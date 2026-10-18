"""Owner-scoped AI sidebar sessions, independent of application workers."""
import asyncio
import json
import secrets
from collections import OrderedDict
from aiohttp import web, WSMsgType
from ..ai.session import Session


class Conversations:
    def __init__(self, gateway, credentials):
        self.gateway, self.credentials = gateway, credentials
        self.entries = OrderedDict()
        self.lock = asyncio.Lock()

    async def drop_owner(self, owner):
        for token, entry in list(self.entries.items()):
            if entry['owner'] == owner:
                self.entries.pop(token)
                for ws in list(entry['sockets']):
                    await ws.close(code=4001, message=b'Logged out')
                await entry['session'].close()

    async def close(self):
        for owner in {entry['owner'] for entry in self.entries.values()}:
            await self.drop_owner(owner)

    async def websocket(self, request):
        gateway = self.gateway
        owner = gateway.owner(request)
        if not gateway.ai_allowed(owner) or request.headers.getall('Origin', []) != [gateway._origin(request)]:
            raise web.HTTPForbidden()
        ws = web.WebSocketResponse(compress=False, heartbeat=20, max_msg_size=65536)
        await ws.prepare(request)
        entry = None
        sender = None
        try:
            hello = await asyncio.wait_for(ws.receive_json(), 10)
            if not isinstance(hello, dict) or hello.get('type') != 'attach':
                raise ValueError('Expected attach')
            if gateway.owner(request) != owner or not gateway.ai_allowed(owner):
                await ws.close(code=4001, message=b'Logged out')
                return ws
            token = hello.get('conversation')
            if token:
                entry = self.entries.get(token)
                if entry is None:
                    token = None  # A gateway restart/eviction starts a new conversation.
                elif entry['owner'] != owner:
                    raise ValueError('Conversation belongs to another browser')
            if not token:
                if len(self.entries) >= gateway.sessions.max_sessions:
                    idle = next((key for key, value in self.entries.items()
                                 if not value['sockets'] and value['session'].task is None), None)
                    if idle is None:
                        raise ValueError('AI conversation capacity reached')
                    await self.entries.pop(idle)['session'].close()
                    if gateway.owner(request) != owner or not gateway.ai_allowed(owner):
                        await ws.close(code=4001, message=b'Logged out')
                        return ws
                token = secrets.token_urlsafe(32)
                entry = dict(owner=owner, sockets=set(), renew=0, resume_id=None)
                def changed():
                    entry['renew'] += 1
                    entry['session'].notify()
                entry['session'] = Session(self.credentials, self.lock, changed)
                self.entries[token] = entry
            self.entries.move_to_end(token)
            entry['sockets'].add(ws)
            session = entry['session']
            session.load_models()
            event = asyncio.Event()
            session.listeners.add(event)

            async def send():
                try:
                    while True:
                        event.clear()
                        await asyncio.wait_for(ws.send_json(dict(type='state', conversation=token,
                            renew=entry['renew'], resume_id=entry['resume_id'], **session.state())), 5)
                        await event.wait()
                except (ConnectionError, asyncio.TimeoutError):
                    await ws.close(code=1011, message=b'AI output stalled')
                finally:
                    session.listeners.discard(event)
            sender = asyncio.create_task(send())
            async for message in ws:
                if gateway.owner(request) != owner or not gateway.ai_allowed(owner):
                    break
                if message.type != WSMsgType.TEXT:
                    break
                try:
                    data = json.loads(message.data)
                    if not isinstance(data, dict):
                        raise ValueError('Expected an object')
                    kind = data.get('type')
                    if kind in ('prompt', 'answer', 'cancel'):
                        gateway.touch_owner(owner)
                    if kind == 'prompt':
                        resume_id = data.get('resume_id')
                        if resume_id is not None and (not isinstance(resume_id, str) or len(resume_id) > 128):
                            raise ValueError('Invalid application session')
                        worker = gateway.workers.get(resume_id)
                        if worker is not None and worker.owner != owner:
                            raise ValueError('Application session belongs to another browser')
                        session.submit(data.get('provider'), data.get('text'), data.get('settings'))
                        entry['resume_id'] = resume_id
                    elif kind == 'answer':
                        session.answer(data.get('id'), data.get('allow'), data.get('text', ''))
                    elif kind == 'cancel':
                        await session.cancel()
                    else:
                        raise ValueError('Unknown AI action')
                except (ValueError, TypeError) as error:
                    await ws.send_json(dict(type='error', text=str(error)))
        except (ValueError, TypeError, asyncio.TimeoutError) as error:
            await ws.close(code=1008, message=str(error).encode()[:120])
        finally:
            if sender:
                sender.cancel()
                await asyncio.gather(sender, return_exceptions=True)
            if entry:
                entry['sockets'].discard(ws)
            await ws.close()
        return ws
