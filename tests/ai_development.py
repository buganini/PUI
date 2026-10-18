"""Credential-free agent, workspace and real supervisor regression coverage."""
import asyncio
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock, AsyncMock, call
from PUI.ai.session import Session
from PUI.ai.workspace import snapshot
from PUI.ai.native import Supervisor, bring_to_front
from PUI.__main__ import create_application, valid_name, main


class FakeAgent:
    def __init__(self, name, key, session):
        self.session = session
        self.release = asyncio.Event()

    async def run(self, prompt):
        if prompt == 'approval':
            answer = await self.session.ask('Run command', {'command': 'example'})
            self.session.message('assistant', str(answer['allow']), 'codex')
        else:
            Path(self.session.cwd, 'example.txt').write_text(prompt)
        if prompt == 'fail':
            raise RuntimeError('failed secret-key')
        if prompt == 'cancel':
            await self.release.wait()

    async def interrupt(self):
        self.release.set()

    async def close(self):
        pass


class SessionTests(unittest.IsolatedAsyncioTestCase):
    async def test_settings_are_session_local_and_applied_per_turn(self):
        credentials = {'codex': {'key': 'secret', 'model': 'configured'}}
        observed = []
        class Agent(FakeAgent):
            async def run(self, prompt):
                observed.append(dict(self.options))
        with tempfile.TemporaryDirectory() as folder:
            session = Session(credentials, asyncio.Lock(), lambda: None, cwd=folder, provider_factory=Agent)
            try:
                session.catalog = {'codex': [{'model':'chosen', 'efforts':['high']}]}
                for invalid in ({'key':'leak'}, {'model': 42}, {'model':'chosen','effort':'low'}):
                    with self.assertRaises(ValueError):
                        session.submit('codex', 'test', invalid)
                session.submit('codex', 'first', {'model':'chosen', 'effort':'high'})
                with self.assertRaises(ValueError):
                    session.submit('codex', 'busy', {})
                await session.task
                session.submit('codex', 'default', {'model':'', 'effort':''})
                await session.task
                self.assertEqual(observed, [{'key':'secret','model':'chosen','effort':'high'}, {'key':'secret'}])
                self.assertEqual(credentials['codex']['model'], 'configured')
                self.assertNotIn('secret', str(session.state()))
            finally:
                await session.close()

    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.changes = []
        self.session = Session({'codex': {'key': 'secret-key'}}, asyncio.Lock(),
            lambda: self.changes.append(True), cwd=self.tmp.name, provider_factory=FakeAgent)

    async def asyncTearDown(self):
        await self.session.close()
        self.tmp.cleanup()

    async def test_changes_failure_cancellation_and_no_change(self):
        for prompt in ('first', 'first', 'fail', 'cancel'):
            before = len(self.changes)
            self.session.submit('codex', prompt)
            task = self.session.task
            if prompt == 'cancel':
                while not Path(self.tmp.name, 'example.txt').exists() or Path(self.tmp.name, 'example.txt').read_text() != 'cancel':
                    await asyncio.sleep(.01)
                await self.session.cancel()
            else:
                await task
            # Rewriting identical bytes still changes mtime and must renew.
            self.assertEqual(len(self.changes), before + 1)
        self.assertNotIn('secret-key', json.dumps(self.session.state()))
        self.session.submit('codex', 'approval')
        while not self.session.pending:
            await asyncio.sleep(.01)
        token = next(iter(self.session.pending))
        self.session.answer(token, False)
        await self.session.task
        self.assertEqual(len(self.changes), 4)
        self.assertEqual(self.session.messages[-1]['text'], 'False')
        with self.assertRaises(ValueError):
            self.session.answer(token, True)

    async def test_workspace_lock_serializes_sessions(self):
        self.session.submit('codex', 'approval')
        while not self.session.pending:
            await asyncio.sleep(.01)
        other = Session({'codex': {}}, self.session.lock, lambda: None,
                        cwd=self.tmp.name, provider_factory=FakeAgent)
        try:
            other.submit('codex', 'second')
            other_task = other.task
            await asyncio.sleep(.03)
            self.assertFalse(Path(self.tmp.name, 'example.txt').exists())
            await self.session.cancel()
            await other_task
            self.assertEqual(Path(self.tmp.name, 'example.txt').read_text(), 'second')
        finally:
            await other.close()

    async def test_supervisor_roundtrip_restart_and_parent_close(self):
        supervisor = Supervisor({'codex': {}}, command=[sys.executable,
            str(Path(__file__).with_name('ai_child_fixture.py'))], cwd=Path(__file__).resolve().parents[1])
        activations = []
        supervisor.on_child_ready = lambda: activations.append(True)
        # A subprocess launched as a script needs the checkout import path.
        with patch.dict(os.environ, {'PYTHONPATH': str(Path(__file__).resolve().parents[1])}):
            try:
                await supervisor.restart()
                async def wait_count(count):
                    for _ in range(200):
                        if supervisor.options.get('example.count') == str(count):
                            return
                        await asyncio.sleep(.01)
                    self.fail(str(supervisor.session.messages))
                await wait_count(1)
                self.assertEqual(len(activations), 1)
                old = supervisor.process
                await supervisor.restart()
                await wait_count(2)
                self.assertEqual(len(activations), 2)
                self.assertEqual(old.returncode, 0)
                self.assertEqual(supervisor.options['example.special'], '#hello=世界')
                process = supervisor.process
                await supervisor.close()
                self.assertEqual(process.returncode, 0)
            finally:
                await supervisor.close()


class LauncherTests(unittest.TestCase):
    def test_names_source_and_no_overwrite(self):
        for name in ('class', '123App', 'hello-world', '../Bad', '', 'ｃｌａｓｓ', '__debug__'):
            self.assertFalse(valid_name(name))
        for name in ('Example', '_App', '應用'):
            self.assertTrue(valid_name(name))
        with tempfile.TemporaryDirectory() as directory:
            for backend in ('PySide6', 'wx', 'tkinter', 'flet', 'web'):
                name = backend.title() + 'App'
                command = create_application(name, backend, 'codex', directory)
                text = Path(directory, name + '.py').read_text()
                compile(text, name + '.py', 'exec')
                self.assertIn("title=" + repr(name), text)
                self.assertEqual(command[-2:], ['-m', name])
                with self.assertRaises(FileExistsError):
                    create_application(name, backend, 'codex', directory)

    def test_missing_auth_exits_before_backend_or_write(self):
        with patch('builtins.input', side_effect=['1']), \
             patch('PUI.ai.auth.check_credentials', side_effect=RuntimeError('No credentials')), \
             patch('PUI.__main__.create_application') as create:
            self.assertEqual(main(), 1)
            create.assert_not_called()

    def test_scan_ignores_environments_and_detects_deletion(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'env').mkdir()
            (root / 'env' / 'ignored.py').write_text('a')
            (root / 'x.pyc').write_text('a')
            (root / 'app.py').write_text('a')
            self.assertEqual(set(snapshot(root)), {'app.py'})
            (root / 'app.py').unlink()
            self.assertEqual(snapshot(root), {})



class ForegroundTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        activation = patch('PUI.ai.native._activate_macos_application')
        self.macos_activation = activation.start()
        self.addCleanup(activation.stop)

    async def test_wx_activates_macos_process_before_raising_window(self):
        for platform in ('darwin', 'linux', 'win32'):
            with self.subTest(platform=platform):
                events = []
                window = Mock()
                window.IsIconized.return_value = True
                window.Iconize.side_effect = lambda _: events.append('restore')
                window.Raise.side_effect = lambda: events.append('raise')
                window.SetFocus.side_effect = lambda: events.append('focus')
                self.macos_activation.side_effect = lambda: events.append('application')
                with patch('PUI.ai.native.sys.platform', platform):
                    bring_to_front(Mock(children=[Mock(ui=window)]), 'wx',
                                   lambda: events.append('done'))
                expected = ['restore']
                if platform == 'darwin':
                    expected.append('application')
                self.assertEqual(events, expected + ['raise', 'focus', 'done'])

    async def test_tkinter_activates_macos_process_before_lifting_window(self):
        for platform in ('darwin', 'linux', 'win32'):
            with self.subTest(platform=platform):
                events = []
                window = Mock()
                window.deiconify.side_effect = lambda: events.append('restore')
                window.lift.side_effect = lambda: events.append('lift')
                window.focus_set.side_effect = lambda: events.append('focus')
                self.macos_activation.side_effect = lambda: events.append('application')
                with patch('PUI.ai.native.sys.platform', platform):
                    bring_to_front(Mock(children=[Mock(ui=window)]), 'tkinter',
                                   lambda: events.append('done'))
                expected = ['restore']
                if platform == 'darwin':
                    expected.append('application')
                self.assertEqual(events, expected + ['lift', 'focus', 'done'])

    async def test_native_activation_and_restore(self):
        for backend, methods in (
            ('PySide6', [call.isMinimized(), call.showNormal(), call.raise_(), call.activateWindow()]),
            ('wx', [call.IsIconized(), call.Iconize(False), call.Raise(), call.SetFocus()]),
            ('tkinter', [call.deiconify(), call.lift(), call.focus_set()]),
        ):
            with self.subTest(backend=backend):
                window = Mock()
                app = Mock(children=[Mock(ui=window)])
                bring_to_front(app, backend)
                self.assertEqual(window.mock_calls, methods)

    async def test_flet_activation_runs_on_ui_loop(self):
        page = Mock()
        page.window.to_front = AsyncMock()
        app = Mock(children=[Mock(ui=page)], loop=asyncio.get_running_loop())
        bring_to_front(app, 'flet')
        await asyncio.sleep(0)
        self.assertFalse(page.window.minimized)
        page.update.assert_called_once_with()
        page.window.to_front.assert_awaited_once_with()
        self.macos_activation.assert_not_called()

    async def test_child_activation_precedes_ready_notification(self):
        from PUI.ai.native import ready
        from PUI.ai.ipc import ChildConnection
        import threading
        for backend in ('PySide6', 'wx', 'tkinter', 'flet'):
            with self.subTest(backend=backend):
                events = []
                child = ChildConnection.__new__(ChildConnection)
                child.lock = threading.Lock()
                child.stopping = False
                child._notify_ready = lambda: events.append('ready')
                window = Mock()
                window.activateWindow.side_effect = lambda: events.append('activate')
                window.SetFocus.side_effect = lambda: events.append('activate')
                window.focus_set.side_effect = lambda: events.append('activate')
                release = asyncio.Event()
                async def activate():
                    await release.wait()
                    events.append('activate')
                window.window.to_front = activate
                app = Mock(children=[Mock(ui=window)], loop=asyncio.get_running_loop(), _ai_ready=None)
                posted = []
                with patch('PUI.ai.native.connect', return_value=child), \
                     patch('PUI.ai.native.poster', return_value=posted.append):
                    ready(app, backend)
                self.assertEqual(events, [])
                posted.pop()()
                if backend == 'flet':
                    await asyncio.sleep(0)
                    self.assertEqual(events, [])
                    release.set()
                    await asyncio.sleep(0)
                self.assertEqual(events, ['activate', 'ready'])


if __name__ == '__main__':
    unittest.main()
