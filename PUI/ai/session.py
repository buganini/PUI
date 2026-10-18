"""Agent conversations and permissions, owned by the supervisor event loop."""
import asyncio
import inspect
import json
import secrets
from pathlib import Path
from .workspace import snapshot


class Session:
    def __init__(self, credentials, lock, changed, *, cwd=None, provider_factory=None):
        self.credentials = {name: dict(options) for name, options in credentials.items()}
        self.selections = {name: {key: options.get(key, "") for key in ("model", "effort")}
                           for name, options in credentials.items()}
        self.catalog = {}
        self.catalog_task = None
        self.lock = lock
        self.changed = changed
        self.cwd = str(Path(cwd or Path.cwd()).resolve())
        self.provider_factory = provider_factory
        self.agents = {}
        self.messages = []
        self.pending = {}
        self.listeners = set()
        self.task = None
        self.active = None
        self.closed = False
        self.revision = 0

    def redact(self, text):
        text = str(text)
        for settings in self.credentials.values():
            key = settings.get('key')
            if key:
                text = text.replace(key, '[redacted]')
        return text

    def notify(self):
        self.revision += 1
        for event in self.listeners:
            event.set()

    def message(self, role, text, provider=None, *, append=False):
        text = self.redact(text)
        if append and self.messages and self.messages[-1]['role'] == role and self.messages[-1]['provider'] == provider:
            self.messages[-1]['text'] = (self.messages[-1]['text'] + text)[-65536:]
        else:
            self.messages.append(dict(role=role, text=text[-65536:], provider=provider))
        while len(self.messages) > 200 or sum(len(m['text']) for m in self.messages) > 131072:
            self.messages.pop(0)
        self.notify()

    def state(self):
        return dict(providers=list(self.credentials), cwd=self.cwd,
                    selections={name: dict(value) for name, value in self.selections.items()},
                    models=self.catalog,
                    effort_levels={"claude": ["low", "medium", "high", "xhigh", "max"]},
                    busy=self.task is not None, active=self.active,
                    messages=[dict(message) for message in self.messages], revision=self.revision,
                    approvals=[p[0] for p in self.pending.values()])

    async def ask(self, title, details, *, input=False):
        if self.closed:
            return dict(allow=False, text='')
        token = secrets.token_urlsafe(16)
        future = asyncio.get_running_loop().create_future()
        self.pending[token] = (dict(id=token, title=title, input=input,
            details=self.redact(json.dumps(details, ensure_ascii=False, default=str))[:32768]), future)
        self.notify()
        try:
            return await future
        finally:
            self.pending.pop(token, None)
            self.notify()

    def answer(self, token, allow, text=''):
        if type(allow) is not bool or not isinstance(text, str) or len(text) > 8192:
            raise ValueError('Invalid approval response')
        entry = self.pending.get(token)
        if entry is None or entry[1].done():
            raise ValueError('Approval is no longer pending')
        entry[1].set_result(dict(allow=allow, text=text))

    def load_models(self):
        if self.catalog_task is None and 'codex' in self.credentials and not self.closed:
            self.catalog_task = asyncio.create_task(self._load_models())

    def _agent(self, provider):
        if provider not in self.agents:
            from .providers import create
            factory = self.provider_factory or create
            self.agents[provider] = factory(provider, self.credentials[provider], self)
        return self.agents[provider]

    async def _load_models(self):
        try:
            agent = self._agent('codex')
            if hasattr(agent, 'models'):
                self.catalog['codex'] = await agent.models()
                self.notify()
        except Exception as error:
            self.message('error', 'Could not load models: ' + str(error), 'codex')

    def submit(self, provider, prompt, settings=None):
        if self.closed or self.task is not None:
            raise ValueError('An AI turn is already running or this session is closed')
        if provider not in self.credentials or not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 32768:
            raise ValueError('Choose an enabled provider and enter a prompt of at most 32768 characters')
        if settings is not None:
            if (not isinstance(settings, dict) or settings.keys() - {'model', 'effort'} or
                    any(not isinstance(value, str) or len(value) > 200 for value in settings.values())):
                raise ValueError('Invalid model/effort selection')
            selection = {key: settings.get(key, '').strip() for key in ('model', 'effort')}
            model = next((m for m in self.catalog.get(provider, []) if m['model'] == selection['model']), None)
            if model and selection['effort'] and selection['effort'] not in model['efforts']:
                raise ValueError('Unsupported effort for the selected model')
            self.selections[provider] = selection
        self.active = provider
        self.message('user', prompt, provider)
        self.task = asyncio.create_task(self._run(provider, prompt))
        self.notify()

    async def _run(self, provider, prompt):
        try:
            async with self.lock:
                before = await asyncio.to_thread(snapshot, self.cwd)
                try:
                    if self.catalog_task is not None:
                        await asyncio.shield(self.catalog_task)
                    agent = self._agent(provider)
                    agent.options = {key: value for key, value in self.credentials[provider].items()
                                     if key not in ('model', 'effort')}
                    agent.options.update({key: value for key, value in self.selections[provider].items() if value})
                    await self.agents[provider].run(prompt)
                finally:
                    # Even a failed/cancelled turn can have changed files.
                    after = await asyncio.to_thread(snapshot, self.cwd)
                    if before != after and not self.closed:
                        outcome = self.changed()
                        if inspect.isawaitable(outcome):
                            await outcome
        except asyncio.CancelledError:
            self.message('status', 'Cancelled', provider)
        except Exception as error:
            self.message('error', str(error), provider)
        finally:
            self.task = None
            self.active = None
            self.notify()

    async def cancel(self):
        task = self.task
        if task is None:
            return
        for _, future in list(self.pending.values()):
            if not future.done():
                future.set_result(dict(allow=False, text=''))
        agent = self.agents.get(self.active)
        if agent is not None:
            try:
                await asyncio.wait_for(agent.interrupt(), 3)
                await asyncio.wait_for(asyncio.shield(task), 3)
                return
            except (Exception, asyncio.CancelledError):
                pass
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        if self.task is task:
            self.task = self.active = None
            self.notify()

    async def close(self):
        self.closed = True
        await self.cancel()
        if self.catalog_task is not None:
            self.catalog_task.cancel()
            await asyncio.gather(self.catalog_task, return_exceptions=True)
        await asyncio.gather(*(agent.close() for agent in self.agents.values()), return_exceptions=True)
        self.listeners.clear()
