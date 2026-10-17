"""Native application supervisor and its independent AI window."""
import asyncio
import importlib
import json
import os
import secrets
import subprocess
import sys
import threading
from . import enabled_providers
from .ipc import MAX_MESSAGE, connect, options_text
from .session import Session


def entry_command():
    # orig_argv preserves interpreter flags and -m on Python 3.10+.
    if hasattr(sys, 'orig_argv'):
        return [sys.executable, *sys.orig_argv[1:]]
    main = sys.modules['__main__']
    spec = getattr(main, '__spec__', None)
    if spec is not None:
        return [sys.executable, '-m', spec.name, *sys.argv[1:]]
    if not sys.argv or sys.argv[0] in ('', '-c', '-'):
        raise ValueError('AI supervision requires a Python script or module entry point')
    return [sys.executable, *sys.argv]


def poster(app, backend):
    if backend == 'PySide6':
        from ..PySide6.base import _WindowCommands
        app._ai_commands = _WindowCommands(app.ui)
        return app._ai_commands.requested.emit
    if backend == 'wx':
        import wx
        return wx.CallAfter
    if backend == 'tkinter':
        from ..tkinter.base import _WindowCommands
        if app._window_commands is None:
            app._window_commands = _WindowCommands(app.ui)
        return app._window_commands.submit
    return lambda callback: app.loop.call_soon_threadsafe(callback, context=app.context.copy())


def bring_to_front(app, backend, done=None):
    """Request activation on the owning UI thread, then run done."""
    if not app.children:
        if done:
            done()
        return
    window = app.children[0].ui
    if backend == 'PySide6':
        if window.isMinimized():
            window.showNormal()
        window.raise_()
        window.activateWindow()
    elif backend == 'wx':
        if window.IsIconized():
            window.Iconize(False)
        window.Raise()
        window.SetFocus()
    elif backend == 'tkinter':
        window.deiconify()
        window.lift()
        window.focus_set()
    elif backend == 'flet':
        async def activate():
            window.window.minimized = False
            window.update()
            await window.window.to_front()
            if done:
                done()
        app.loop.create_task(activate())
        return
    if done:
        done()


def ready(app, backend):
    child = connect()
    if child is not None:
        child.ready(poster(app, backend), app.quit,
                    before_notify=lambda done: bring_to_front(app, backend, done))
    callback = getattr(app, '_ai_ready', None)
    if callback:
        callback(poster(app, backend))


def start(app, backend, run, *, codex=None, claude=None, landlock=None):
    if not os.environ.get('PUI_IPC'):
        credentials = enabled_providers(codex, claude)
        if credentials:
            run_supervisor(backend, app.title, credentials)
            return
    connect()  # Fail startup if the supervisor channel is unavailable.
    from .._landlock import apply
    if backend != 'flet':
        if app.ui is None:
            app.sync()
        ready(app, backend)
    apply(landlock)
    run()


class Supervisor:
    def __init__(self, credentials, *, command=None, cwd=None):
        from pathlib import Path
        self.cwd = str(Path(cwd or Path.cwd()).resolve())
        self.command = command or entry_command()
        self.credentials = credentials
        self.process = self.server = self.writer = None
        self.connections = {}
        self.output_tasks = set()
        self.options = {}
        from ..options import Options
        self.options.update(Options)
        self.token = None
        self.session = Session(credentials, asyncio.Lock(), self.restart, cwd=self.cwd)
        self.child_lock = asyncio.Lock()
        self.closed = False
        self.child_ready = False
        self.on_child_ready = None

    async def _accept(self, reader, writer):
        # Each child gets a new endpoint/token; old publishers cannot modify new state.
        task = asyncio.current_task()
        self.connections[task] = writer
        token = self.token
        try:
            while True:
                line = await reader.readline()
                if not line:
                    break
                message = json.loads(line)
                if message.get('token') != token:
                    break
                self.writer = writer
                if message.get('type') == 'ready' and not self.child_ready:
                    self.child_ready = True
                    if self.on_child_ready:
                        self.on_child_ready()
                if message.get('type') == 'state' and isinstance(message.get('name'), str) and isinstance(message.get('value'), str):
                    self.options[message['name']] = message['value']
        except (OSError, ValueError):
            pass
        finally:
            writer.close()
            await writer.wait_closed()
            self.connections.pop(task, None)
            if self.writer is writer:
                self.writer = None

    async def _stop_child(self):
        server, self.server = self.server, None
        if server:
            server.close()
        process = self.process
        if process and process.returncode is None:
            if self.writer:
                self.writer.write((json.dumps(dict(token=self.token, type='stop')) + '\n').encode())
                try:
                    await self.writer.drain()
                except ConnectionError:
                    pass
            else:
                for writer in list(self.connections.values()):
                    writer.close()
            try:
                await asyncio.wait_for(process.wait(), 5)
            except asyncio.TimeoutError:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), 2)
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
        # EOF drains the child's final State ref messages before PUI_OPTIONS is built.
        for writer in list(self.connections.values()):
            writer.close()
        if self.connections:
            await asyncio.gather(*list(self.connections), return_exceptions=True)
        if server:
            await server.wait_closed()
        self.process = None

    async def restart(self):
        async with self.child_lock:
            if self.closed:
                return
            await self._stop_child()
            self.child_ready = False
            self.token = secrets.token_urlsafe(32)
            self.server = await asyncio.start_server(self._accept, '127.0.0.1', 0, limit=MAX_MESSAGE)
            env = os.environ.copy()
            env['PUI_IPC'] = json.dumps(dict(port=self.server.sockets[0].getsockname()[1], token=self.token))
            env['PUI_OPTIONS'] = options_text(self.options)
            # Do not add keys to the child environment; remove inherited provider secrets.
            for name in ('OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN', 'CLAUDE_CODE_OAUTH_TOKEN'):
                env.pop(name, None)
            try:
                self.process = await asyncio.create_subprocess_exec(*self.command, cwd=self.cwd, env=env,
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
                    limit=MAX_MESSAGE)
            except Exception:
                self.server.close()
                await self.server.wait_closed()
                self.server = None
                raise
            output = asyncio.create_task(self._output(self.process))
            self.output_tasks.add(output)
            output.add_done_callback(self.output_tasks.discard)
            self.session.message('status', 'Application started')

    async def _output(self, process):
        while True:
            data = await process.stdout.read(4096)
            if not data:
                break
            text = data.decode(errors='replace')
            self.session.message('application', text, append=True)
        code = await process.wait()
        if not self.closed:
            self.session.message('status', 'Application exited (%s). The AI window remains open.' % code)

    async def close(self):
        self.closed = True
        await self.session.close()
        async with self.child_lock:
            await self._stop_child()
        for task in list(self.output_tasks):
            task.cancel()
        await asyncio.gather(*list(self.output_tasks), return_exceptions=True)


def run_supervisor(backend, title, credentials):
    UI = importlib.import_module('PUI.' + backend)
    supervisor = Supervisor(credentials)
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, name='PUI AI supervisor')
    view_state = {'messages': [], 'providers': list(credentials), 'busy': False, 'approvals': []}

    class AIApplication(UI.Application):
        def setup(self):
            self.fields = UI.State()
            self.fields.prompt = ''
            self.fields.provider = next(iter(credentials))
            self.fields.answer = ''

        def send(self, event):
            prompt, provider = self.fields.prompt, self.fields.provider
            self.fields.prompt = ''
            def submit():
                try:
                    supervisor.session.submit(provider, prompt)
                except ValueError as error:
                    supervisor.session.message('error', str(error))
            loop.call_soon_threadsafe(submit)

        def cancel(self, event):
            asyncio.run_coroutine_threadsafe(supervisor.session.cancel(), loop)

        def restart(self, event):
            async def restart():
                try:
                    await supervisor.restart()
                except Exception as error:
                    supervisor.session.message('error', str(error))
            asyncio.run_coroutine_threadsafe(restart(), loop)

        def answer(self, token, allow):
            text = self.fields.answer
            def answer():
                try:
                    supervisor.session.answer(token, allow, text)
                except ValueError as error:
                    supervisor.session.message('error', str(error))
            loop.call_soon_threadsafe(answer)

        def content(self):
            with UI.Window(title=(title or 'PUI') + ' — AI', size=(640, 700)):
                with UI.VBox().layout(weight=1):
                    UI.Label('Workspace: ' + supervisor.cwd)
                    with UI.HBox():
                        with UI.ComboBox(text_model=self.fields('provider'), editable=False):
                            for provider in credentials:
                                UI.ComboBoxItem(provider)
                        UI.Button('Restart application', disabled=view_state['busy']).click(self.restart)
                    with UI.Scroll().layout(weight=1):
                        UI.Text('\n\n'.join((m['provider'] or m['role']) + ': ' + m['text']
                            for m in view_state['messages']), selectable=True)
                    for approval in view_state['approvals']:
                        UI.Text(approval['title'] + '\n' + approval['details'])
                        if approval['input']:
                            UI.TextField(self.fields('answer'), placeholder='Answer')
                        with UI.HBox():
                            UI.Button('Allow / Send').click(lambda event, token=approval['id']: self.answer(token, True))
                            UI.Button('Deny').click(lambda event, token=approval['id']: self.answer(token, False))
                    UI.TextField(self.fields('prompt'), edit_model=self.fields('prompt'), placeholder='Describe a change…')
                    with UI.HBox():
                        UI.Button('Send', disabled=view_state['busy']).click(self.send)
                        UI.Button('Cancel', disabled=not view_state['busy']).click(self.cancel)

    app = AIApplication(title=title)
    async def watch(post):
        event = asyncio.Event()
        supervisor.session.listeners.add(event)
        try:
            while True:
                state = supervisor.session.state()
                def update(state=state):
                    view_state.update(state)
                    app.redraw()
                post(update)
                await event.wait()
                event.clear()
        finally:
            supervisor.session.listeners.discard(event)

    watcher = None
    def attached(post):
        nonlocal watcher
        def attach():
            def schedule_activation():
                token = supervisor.token
                def activate():
                    if not supervisor.closed and supervisor.token == token:
                        bring_to_front(app, backend)
                loop.call_later(0.5, post, activate)
            supervisor.on_child_ready = schedule_activation
            if supervisor.child_ready:
                supervisor.on_child_ready()
        loop.call_soon_threadsafe(attach)
        watcher = asyncio.run_coroutine_threadsafe(watch(post), loop)
    app._ai_ready = attached
    async def boot():
        try:
            await supervisor.restart()
        except Exception as error:
            supervisor.session.message('error', str(error))
    thread.start()
    asyncio.run_coroutine_threadsafe(boot(), loop)
    try:
        app.start()
    finally:
        if watcher:
            watcher.cancel()
        try:
            asyncio.run_coroutine_threadsafe(supervisor.close(), loop).result(timeout=20)
        finally:
            loop.call_soon_threadsafe(loop.stop)
            thread.join()
            loop.close()
