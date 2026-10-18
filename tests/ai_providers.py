"""Exercise SDK adapter contracts without inference or real credentials."""
import asyncio
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
from PUI.ai.providers import Codex, Claude
from PUI.ai.session import Session


class ProviderTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.session = Session({'codex': {}, 'claude': {}}, asyncio.Lock(), lambda: None, cwd=self.tmp.name)

    async def asyncTearDown(self):
        await self.session.close()
        self.tmp.cleanup()

    async def test_codex_thread_sandbox_permissions_and_existing_login(self):
        starts = []
        with patch('openai_codex.client.CodexClient') as Client:
            client = Client.return_value
            client.thread_start.return_value.thread.id = 'thread'
            client.turn_start.return_value.turn.id = 'turn'
            payload = SimpleNamespace(model_dump=lambda **kwargs: {'turn': {'status': 'completed'}})
            client.next_turn_notification.return_value = SimpleNamespace(method='turn/completed', payload=payload)
            agent = Codex({}, self.session)
            try:
                await agent.run('first')
                await agent.run('second')
                client.account_login_start.assert_not_called()
                self.assertEqual(client.turn_start.call_args.args[2], {})
                client.thread_start.assert_called_once()
                params = client.thread_start.call_args.args[0]
                self.assertEqual(params['sandbox'], 'workspace-write')
                self.assertEqual(params['approvalsReviewer'], 'user')
                self.assertEqual(params['cwd'], self.tmp.name)
                response = asyncio.create_task(asyncio.to_thread(agent._approval,
                    'item/permissions/requestApproval', {'permissions': {'network': {'enabled': True}}}))
                while not self.session.pending:
                    await asyncio.sleep(.01)
                self.session.answer(next(iter(self.session.pending)), False)
                self.assertEqual(await response, {'permissions': {}, 'scope': 'turn'})
            finally:
                await agent.close()
            client.close.assert_called_once()

    async def test_api_key_uses_temporary_home(self):
        with patch('openai_codex.client.CodexClient') as Client:
            client = Client.return_value
            client.thread_start.return_value.thread.id = 'thread'
            client.turn_start.return_value.turn.id = 'turn'
            payload = SimpleNamespace(model_dump=lambda **kwargs: {'turn': {'status': 'completed'}})
            client.next_turn_notification.return_value = SimpleNamespace(method='turn/completed', payload=payload)
            agent = Codex({'key': 'sample-key', 'model': 'test-model', 'effort': 'high'}, self.session)
            try:
                await agent.run('test')
                client.turn_start.assert_called_once_with('thread', 'test', {'model': 'test-model', 'effort': 'high'})
                home = Path(Client.call_args.args[0].env['CODEX_HOME'])
                self.assertTrue(home.is_dir())
                client.account_login_start.assert_called_once_with({'type':'apiKey','apiKey':'sample-key'})
            finally:
                await agent.close()
            self.assertFalse(home.exists())

    async def test_claude_permission_boundary_and_question(self):
        from claude_agent_sdk import PermissionResultAllow, PermissionResultDeny
        agent = Claude({}, self.session)
        inside = await agent._permission('Write', {'file_path': str(Path(self.tmp.name, 'app.py'))}, None)
        self.assertIsInstance(inside, PermissionResultAllow)
        outside = asyncio.create_task(agent._permission('Write', {'file_path': '/outside/app.py'}, None))
        while not self.session.pending:
            await asyncio.sleep(.01)
        self.session.answer(next(iter(self.session.pending)), False)
        self.assertIsInstance(await outside, PermissionResultDeny)
        question = asyncio.create_task(agent._permission('AskUserQuestion', {'questions':[{'question':'Which color?'}]}, None))
        while not self.session.pending:
            await asyncio.sleep(.01)
        self.session.answer(next(iter(self.session.pending)), True, 'blue')
        self.assertEqual((await question).updated_input['answers'], {'Which color?':'blue'})

    async def test_claude_resumes_and_exits_in_same_task(self):
        from claude_agent_sdk import AssistantMessage, TextBlock, ResultMessage
        options = []
        tasks = []
        class Client:
            def __init__(self, **kwargs):
                options.append(kwargs['options'])
            async def __aenter__(self):
                tasks.append(asyncio.current_task())
                return self
            async def __aexit__(self, *args):
                self_task = asyncio.current_task()
                assert self_task is tasks[-1]
            async def query(self, prompt):
                pass
            async def receive_response(self):
                yield AssistantMessage(content=[TextBlock(text='Hello')], model='test')
                yield ResultMessage(subtype='success', duration_ms=1, duration_api_ms=1,
                    is_error=False, num_turns=1, session_id='previous')
        with patch('claude_agent_sdk.ClaudeSDKClient', Client):
            agent = Claude({'model': 'test-model', 'effort': 'high'}, self.session)
            await agent.run('first')
            await agent.run('second')
        self.assertEqual(options[0].permission_mode, 'default')
        self.assertEqual(options[0].env, {})
        self.assertEqual(options[0].model, 'test-model')
        self.assertEqual(options[0].effort, 'high')
        self.assertEqual(options[1].resume, 'previous')
        self.assertEqual(self.session.messages[-1]['text'], 'Hello')


class ConfigurationTests(unittest.TestCase):
    def test_empty_settings_enable_and_legacy_forms_are_rejected(self):
        from PUI.ai import enabled_providers
        with patch('PUI.ai.importlib.util.find_spec', return_value=object()):
            self.assertEqual(enabled_providers({}, {}), {'codex': {}, 'claude': {}})
            self.assertEqual(enabled_providers(None, False), {})
            for value in (True, 'api-key', {'mode': 'typo'}, {'key': True}, {'model': ''}):
                for provider in ('codex', 'claude'):
                    with self.subTest(provider=provider, value=value), self.assertRaises(ValueError):
                        enabled_providers(**{provider: value})

    def test_empty_settings_warn_on_unsupported_backend(self):
        from PUI.ai import unsupported
        with self.assertLogs('PUI', level='WARNING'):
            unsupported('textual', {}, None)


if __name__ == '__main__':
    unittest.main()
