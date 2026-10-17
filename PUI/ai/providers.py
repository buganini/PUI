"""Public SDK adapters. PUI never reads CLI credential files itself."""
import asyncio
import tempfile
import threading
from pathlib import Path

INSTRUCTIONS = ('You are editing the running PUI application in the working directory. '
    'Keep changes within the requested scope. Do not commit changes. '
    'The application is restarted after a turn if workspace files changed; '
    'do not launch another copy of the application. Application/supervisor startup '
    'configuration is fixed until the developer manually restarts the supervisor.')


def create(name, credential, session):
    return (Codex if name == 'codex' else Claude)(credential, session)


class Codex:
    def __init__(self, credential, session):
        self.credential, self.session = credential, session
        self.loop = asyncio.get_running_loop()
        self.client = None
        self.thread = self.turn = None
        self.home = None
        self.start_lock = threading.Lock()
        self.stopped = False

    def _approval(self, method, params):
        params = params or {}
        ask = self.session.ask
        if method in ('item/commandExecution/requestApproval', 'item/fileChange/requestApproval'):
            answer = asyncio.run_coroutine_threadsafe(ask(method, params), self.loop).result()
            return {'decision': 'accept' if answer['allow'] else 'decline'}
        if method == 'item/permissions/requestApproval':
            answer = asyncio.run_coroutine_threadsafe(ask('Additional permissions', params), self.loop).result()
            return {'permissions': params['permissions'] if answer['allow'] else {}, 'scope': 'turn'}
        if method == 'mcpServer/elicitation/request':
            # Form-mode elicitation expects a JSON object; URL-mode authentication
            # belongs to the provider rather than a server-side browser session.
            answer = asyncio.run_coroutine_threadsafe(ask('MCP input (JSON)', params, input=True), self.loop).result()
            import json
            try:
                content = json.loads(answer['text']) if answer['allow'] else None
            except ValueError:
                content = None
            return {'action': 'accept' if isinstance(content, dict) else 'decline', 'content': content}
        if method == 'item/tool/requestUserInput':
            answers = {}
            for question in params.get('questions', []):
                answer = asyncio.run_coroutine_threadsafe(ask('Agent question', question, input=True), self.loop).result()
                answers[question['id']] = {'answers': [answer['text']] if answer['allow'] else []}
            return {'answers': answers}
        # Unknown requests must never inherit the SDK's auto-accept default.
        raise RuntimeError('Unsupported Codex permission request: ' + method)

    def _run(self, prompt):
        from openai_codex.client import CodexClient, CodexConfig
        if self.stopped:
            return
        if self.client is None:
            env = {}
            if self.credential is not True:
                # API-key login must not replace the user's CLI login.
                self.home = tempfile.TemporaryDirectory(prefix='pui-codex-')
                env['CODEX_HOME'] = self.home.name
            with self.start_lock:
                if self.stopped:
                    return
                self.client = CodexClient(CodexConfig(cwd=self.session.cwd, env=env),
                                          approval_handler=self._approval)
                self.client.start()
            self.client.initialize()
            if self.credential is not True:
                self.client.account_login_start({'type': 'apiKey', 'apiKey': self.credential})
        if self.thread is None:
            started = self.client.thread_start({'cwd': self.session.cwd, 'sandbox': 'workspace-write',
                'approvalPolicy': 'on-request', 'approvalsReviewer': 'user',
                'developerInstructions': INSTRUCTIONS})
            self.thread = started.thread.id
        client = self.client
        turn_id = self.turn = client.turn_start(self.thread, prompt).turn.id
        try:
            while True:
                event = client.next_turn_notification(turn_id)
                data = event.payload.model_dump(mode='json', by_alias=True)
                if event.method == 'item/agentMessage/delta':
                    self.loop.call_soon_threadsafe(self._text, data['delta'])
                elif event.method == 'turn/completed':
                    turn = data['turn']
                    if turn.get('error'):
                        raise RuntimeError(turn['error'].get('message', 'Codex turn failed'))
                    break
        finally:
            client.unregister_turn_notifications(turn_id)
            self.turn = None

    def _text(self, text):
        self.session.message('assistant', text, 'codex', append=True)

    async def run(self, prompt):
        self.stopped = False
        work = asyncio.create_task(asyncio.to_thread(self._run, prompt))
        try:
            await asyncio.shield(work)
        except asyncio.CancelledError:
            # Stop edits before the caller scans files or releases the workspace lock.
            await self.close()
            await asyncio.gather(work, return_exceptions=True)
            raise
        except Exception:
            await self.close()
            raise

    async def interrupt(self):
        if self.client and self.turn:
            await asyncio.to_thread(self.client.turn_interrupt, self.thread, self.turn)

    def _close(self):
        with self.start_lock:
            self.stopped = True
            if self.client:
                self.client.close()
                self.client = None

    async def close(self):
        await asyncio.to_thread(self._close)
        if self.home:
            self.home.cleanup()
            self.home = None
        self.thread = self.turn = None


class Claude:
    def __init__(self, credential, session):
        self.credential, self.session = credential, session
        self.client = None
        self.resume = None

    async def _permission(self, name, arguments, context):
        from claude_agent_sdk import PermissionResultAllow, PermissionResultDeny
        if name == 'AskUserQuestion':
            answers = {}
            for question in arguments.get('questions', []):
                answer = await self.session.ask('Agent question', question, input=True)
                if not answer['allow']:
                    return PermissionResultDeny(message='Question cancelled by the user')
                answers[question['question']] = answer['text']
            return PermissionResultAllow(updated_input={**arguments, 'answers': answers})
        path = arguments.get('file_path')
        if name in ('Edit', 'Write') and isinstance(path, str):
            target = (Path(self.session.cwd) / path).resolve()
            if target.is_relative_to(Path(self.session.cwd)):
                return PermissionResultAllow(updated_input=arguments)
        answer = await self.session.ask(name, arguments)
        if answer['allow']:
            return PermissionResultAllow(updated_input=arguments)
        return PermissionResultDeny(message='Denied by the user')

    async def run(self, prompt):
        from claude_agent_sdk import (ClaudeSDKClient, ClaudeAgentOptions,
                                      AssistantMessage, TextBlock, ResultMessage, SystemMessage)
        env = {} if self.credential is True else {'ANTHROPIC_API_KEY': self.credential}
        options = ClaudeAgentOptions(cwd=self.session.cwd, env=env, resume=self.resume,
            permission_mode='default', can_use_tool=self._permission,
            system_prompt={'type': 'preset', 'preset': 'claude_code', 'append': INSTRUCTIONS})
        # AnyIO's connection scope is opened and closed in this same task.
        async with ClaudeSDKClient(options=options) as client:
            self.client = client
            try:
                await client.query(prompt)
                async for message in client.receive_response():
                    if isinstance(message, SystemMessage) and message.subtype == 'init':
                        self.resume = message.data.get('session_id', self.resume)
                    elif isinstance(message, AssistantMessage):
                        for block in message.content:
                            if isinstance(block, TextBlock):
                                self.session.message('assistant', block.text, 'claude')
                    elif isinstance(message, ResultMessage):
                        self.resume = message.session_id
                        if message.is_error:
                            raise RuntimeError(message.result or message.subtype)
            finally:
                self.client = None

    async def interrupt(self):
        if self.client:
            await self.client.interrupt()

    async def close(self):
        # The session cancels/awaits run() before close(), so its async-with has exited.
        pass
