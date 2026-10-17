"""AI WebSocket authentication, ownership, approvals and retained conversations."""
import asyncio
import re
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from aiohttp import ClientSession, CookieJar, WSServerHandshakeError, WSMsgType
from aiohttp.test_utils import TestServer
from PUI.web.server import Gateway, COOKIE
from PUI.ai.session import Session
from ai_development import FakeAgent


class WebAITests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.gateway = Gateway('web_fixture:App', codex=True, auth=lambda u, p: True)
        def create(credentials, lock, changed):
            return Session(credentials, lock, changed, cwd=self.tmp.name, provider_factory=FakeAgent)
        self.patch = patch('PUI.web.ai.Session', side_effect=create)
        self.patch.start()
        self.server = TestServer(self.gateway.application())
        await self.server.start_server()
        self.origin = str(self.server.make_url('/')).rstrip('/')
        self.client = ClientSession(cookie_jar=CookieJar(unsafe=True))
        self.owner = self.gateway._new_owner(authenticated=True)
        self.client.cookie_jar.update_cookies({COOKIE: self.owner + '.' + self.gateway._sign(self.owner)})
        self.sockets = []

    async def asyncTearDown(self):
        for ws in self.sockets:
            await ws.close()
        await self.client.close()
        await self.server.close()
        self.patch.stop()
        self.tmp.cleanup()

    async def connect(self, conversation=None, client=None):
        ws = await (client or self.client).ws_connect(self.server.make_url('/pui/ai'), headers={'Origin': self.origin})
        self.sockets.append(ws)
        await ws.send_json(dict(type='attach', conversation=conversation))
        return ws

    async def until(self, ws, check):
        async def receive():
            while True:
                message = await ws.receive_json()
                if check(message):
                    return message
        return await asyncio.wait_for(receive(), 5)

    async def test_auth_and_origin_gates(self):
        async with ClientSession() as anonymous:
            with self.assertRaises(WSServerHandshakeError) as error:
                await self.connect(client=anonymous)
            self.assertEqual(error.exception.status, 403)
        with self.assertRaises(WSServerHandshakeError):
            await self.client.ws_connect(self.server.make_url('/pui/ai'), headers={'Origin': 'https://other.example'})
        async with self.client.get(self.server.make_url('/')) as response:
            self.assertIn('data-ai="/pui/ai"', await response.text())

    async def test_renew_keeps_history_and_owner_isolation(self):
        ws = await self.connect()
        first = await ws.receive_json()
        await ws.send_json(dict(type='prompt', provider='codex', text='change', resume_id='retired-worker'))
        changed = await self.until(ws, lambda m: m.get('renew') == 1 and not m.get('busy'))
        self.assertEqual(changed['resume_id'], 'retired-worker')
        self.assertEqual(changed['messages'][0]['text'], 'change')
        await ws.close()
        ws = await self.connect(first['conversation'])
        self.assertEqual((await ws.receive_json())['renew'], 1)
        async with ClientSession(cookie_jar=CookieJar(unsafe=True)) as other:
            owner = self.gateway._new_owner(authenticated=True)
            other.cookie_jar.update_cookies({COOKIE: owner + '.' + self.gateway._sign(owner)})
            foreign = await self.connect(first['conversation'], other)
            self.assertEqual((await foreign.receive()).type, WSMsgType.CLOSE)
        await self.gateway.ai.drop_owner(self.owner)
        self.assertEqual(self.gateway.ai.entries, {})

    async def test_worker_owner_and_pending_approval(self):
        ws = await self.connect()
        await ws.receive_json()
        self.gateway.workers['foreign'] = SimpleNamespace(owner='someone-else')
        try:
            await ws.send_json(dict(type='prompt', provider='codex', text='change', resume_id='foreign'))
            result = await ws.receive_json()
            self.assertEqual(result['type'], 'error')
        finally:
            self.gateway.workers.pop('foreign')
        await ws.send_json(dict(type='prompt', provider='codex', text='approval'))
        state = await self.until(ws, lambda m: m.get('approvals'))
        await ws.send_json(dict(type='answer', id=state['approvals'][0]['id'], allow=False))
        state = await self.until(ws, lambda m: m.get('type') == 'state' and not m['busy'])
        self.assertEqual(state['messages'][-1]['text'], 'False')
        self.assertEqual(state['renew'], 0)

    async def test_logout_cancels_turn_and_revokes_pending_attach(self):
        ws = await self.connect()
        first = await ws.receive_json()
        session = self.gateway.ai.entries[first['conversation']]['session']
        await ws.send_json(dict(type='prompt', provider='codex', text='approval'))
        await self.until(ws, lambda m: m.get('approvals'))
        pending = await self.client.ws_connect(self.server.make_url('/pui/ai'),
            headers={'Origin': self.origin})
        self.sockets.append(pending)
        async with self.client.post(self.server.make_url('/pui/logout'),
                data={'csrf': self.gateway._sign(self.owner, 'logout')},
                headers={'Origin': self.origin}, allow_redirects=False) as response:
            self.assertEqual(response.status, 303)
        self.assertEqual(self.gateway.ai.entries, {})
        self.assertIsNone(session.task)
        self.assertEqual(session.pending, {})
        closed = await ws.receive()
        self.assertEqual((closed.type, closed.data), (WSMsgType.CLOSE, 4001))
        await pending.send_json(dict(type='attach'))
        closed = await pending.receive()
        self.assertEqual((closed.type, closed.data), (WSMsgType.CLOSE, 4001))
        self.assertEqual(self.gateway.ai.entries, {})
        # Logging in with AI enabled creates a fresh owner and conversation.
        async with self.client.get(self.server.make_url('/')) as response:
            html = await response.text()
            csrf = re.search(r'name="csrf" value="([^"]+)"', html).group(1)
        async with self.client.post(self.server.make_url('/pui/login'),
                data={'username': 'test', 'password': 'test123', 'csrf': csrf},
                headers={'Origin': self.origin}, allow_redirects=False) as response:
            self.assertEqual(response.status, 303)
        again = await self.connect()
        self.assertNotEqual((await again.receive_json())['conversation'], first['conversation'])


if __name__ == '__main__':
    unittest.main()
