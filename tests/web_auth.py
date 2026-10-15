"""Optional login gates, cookie separation and authenticated worker sessions."""
import asyncio
import re
import unittest

from aiohttp import ClientSession, CookieJar, WSServerHandshakeError
from aiohttp.test_utils import TestServer

from PUI.web.protocol import Codec, StreamCodec, SUBPROTOCOL
from PUI.web.server import COOKIE, LOGIN_COOKIE, Gateway


class AuthTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.calls = []
        def auth(username, password):
            self.calls.append((username, password))
            return {'test': 'test123'}.get(username) == password
        self.gateway = Gateway('web_fixture:App', base_url='/pui', auth=auth, session_ttl=0)
        self.server = TestServer(self.gateway.application())
        await self.server.start_server()
        self.origin = str(self.server.make_url('/')).rstrip('/')
        self.client = ClientSession(cookie_jar=CookieJar(unsafe=True))

    async def asyncTearDown(self):
        await self.client.close()
        await self.server.close()
        self.assertEqual(self.gateway.workers, {})

    async def form(self, client=None):
        async with (client or self.client).get(self.server.make_url('/pui/')) as response:
            self.assertEqual(response.status, 200)
            html = await response.text()
            self.assertIn('<title>Sign in', html)
            self.assertNotIn('id="pui-root"', html)
            self.assertEqual(response.headers['Cache-Control'], 'no-store')
            self.assertNotIn(COOKIE, response.cookies)
            return {'username': 'test', 'password': 'test123',
                    'csrf': re.search(r'name="csrf" value="([^"]+)"', html).group(1)}

    async def post(self, data, **kwargs):
        return await self.client.post(self.server.make_url('/pui/pui/login'), data=data,
            headers=kwargs.pop('headers', {'Origin': self.origin}), allow_redirects=False, **kwargs)

    async def test_login_page_does_not_allocate_worker_or_authorize_resources(self):
        await self.form()
        async with self.client.get(self.server.make_url('/pui/assets/' + self.gateway.build + '/client.css')) as response:
            self.assertEqual(response.status, 200)
        with self.assertRaises(WSServerHandshakeError) as caught:
            await self.client.ws_connect(self.server.make_url('/pui/pui/ws'),
                protocols=[SUBPROTOCOL], headers={'Origin': self.origin})
        self.assertEqual(caught.exception.status, 403)
        async with self.client.get(self.server.make_url('/pui/pui/images/unknown')) as response:
            self.assertEqual(response.status, 404)
        self.assertEqual(self.gateway.workers, {})
        self.assertEqual(self.calls, [])

    async def test_wrong_password_and_missing_or_duplicate_fields_do_not_authenticate(self):
        fields = await self.form()
        async with await self.post(dict(fields, password='wrong')) as response:
            self.assertEqual(response.status, 200)
            self.assertIn('Invalid username or password.', await response.text())
            self.assertNotIn(COOKIE, response.cookies)
        for data in ({'username': 'unknown', 'csrf': fields['csrf']},
                     list(fields.items()) + [('password', 'second')]):
            async with await self.post(data) as response:
                self.assertEqual(response.status, 400)
        self.assertEqual(self.calls, [('test', 'wrong')])
        await self.form()

    async def test_csrf_origin_cookie_tampering_and_size_are_rejected(self):
        fields = await self.form()
        for data, headers in ((dict(fields, csrf='forged'), {'Origin': self.origin}),
                              (fields, {'Origin': 'https://other.example'}),
                              (fields, [('Origin', self.origin), ('Origin', self.origin)])):
            async with await self.post(data, headers=headers) as response:
                self.assertEqual(response.status, 403)
        cookie = self.client.cookie_jar.filter_cookies(self.server.make_url('/pui/'))[LOGIN_COOKIE].value
        async with self.client.get(self.server.make_url('/pui/'), headers={'Cookie': COOKIE + '=' + cookie}) as response:
            self.assertIn('<title>Sign in', await response.text())
        self.client.cookie_jar.clear()
        async with await self.post(fields) as response:
            self.assertEqual(response.status, 403)
        fields = await self.form()
        async with await self.post(dict(fields, password='x' * 9000)) as response:
            self.assertEqual(response.status, 413)
        self.assertEqual(self.calls, [])

    async def test_callback_exception_or_non_boolean_result_fails_closed(self):
        fields = await self.form()
        def broken(username, password):
            raise RuntimeError('do not expose ' + password)
        self.gateway.auth = broken
        with self.assertLogs('PUI.web.server', level='WARNING') as logs:
            async with await self.post(fields) as response:
                self.assertEqual(response.status, 503)
                self.assertNotIn('test123', await response.text())
                self.assertNotIn(COOKIE, response.cookies)
        self.assertNotIn('test123', str(logs.output))
        self.gateway.auth = lambda username, password: 'truthy'
        async with await self.post(fields) as response:
            self.assertIn('Invalid username or password.', await response.text())
            self.assertNotIn(COOKIE, response.cookies)

    async def test_async_callback_and_forwarded_https_cookie(self):
        async def auth(username, password):
            await asyncio.sleep(0)
            return username == 'test' and password == 'test123'
        self.gateway.auth = auth
        fields = await self.form()
        async with await self.post(fields, headers={'Origin': 'https://public.example',
                'Host': 'public.example', 'X-Forwarded-Proto': 'https'}) as response:
            self.assertEqual(response.status, 303)
            cookie = response.cookies[COOKIE]
            self.assertTrue(cookie['secure'])
            self.assertTrue(cookie['httponly'])
            self.assertEqual(cookie['samesite'], 'Lax')
            self.assertEqual(cookie['path'], '/pui/')
            self.assertEqual(cookie['max-age'], '')
            self.assertEqual(cookie['expires'], '')
            self.assertRegex(cookie.value, r'^[A-Za-z0-9_-]{43}\.[0-9a-f]{64}$')

    async def test_login_survives_new_worker_resume_and_crash(self):
        fields = await self.form()
        async with await self.post(fields) as response:
            self.assertEqual(response.status, 303)
            self.assertEqual(response.headers['Location'], '/pui/')
            owner_cookie = response.cookies[COOKIE].value
        codec = Codec()
        async def open_worker(resume_id=None):
            ws = await self.client.ws_connect(self.server.make_url('/pui/pui/ws'),
                protocols=[SUBPROTOCOL], headers={'Origin': self.origin})
            await ws.send_bytes(codec.encode({'v': 1, 'type': 'hello', 'session': None, 'seq': 1,
                'body': {'client_build': self.gateway.build, 'capabilities': [
                    'render.snapshot', 'render.patch', 'binding.object_id'],
                    'viewport': {'width': 100, 'height': 100, 'dpr': 1}, 'resume_id': resume_id}}))
            decoder = StreamCodec()
            try:
                ready = decoder.decode((await asyncio.wait_for(ws.receive(), 5)).data)
                decoder.decode((await asyncio.wait_for(ws.receive(), 5)).data)
            finally:
                decoder.close()
            await ws.close()
            session_id = ready['body']['resume_id']
            async def detached():
                while self.gateway.workers[session_id].websocket is not None:
                    await asyncio.sleep(.01)
            await asyncio.wait_for(detached(), 5)
            return ready
        first = await open_worker()
        second = await open_worker()
        first_id = first['body']['resume_id']
        self.assertNotEqual(first_id, second['body']['resume_id'])
        self.assertTrue((await open_worker(first_id))['body']['resumed'])
        self.gateway.workers[first_id].process.kill()
        async def reaped():
            while first_id in self.gateway.workers:
                await asyncio.sleep(.01)
        await asyncio.wait_for(reaped(), 5)
        replacement = await open_worker(first_id)
        self.assertFalse(replacement['body']['resumed'])
        async with self.client.get(self.server.make_url('/pui/')) as response:
            self.assertIn('id="pui-root"', await response.text())
            self.assertEqual(response.cookies[COOKIE].value, owner_cookie)
        self.assertEqual(self.calls, [('test', 'test123')])

    def test_invalid_auth_configuration(self):
        for auth in (False, True, 'password', {}):
            with self.subTest(auth=auth), self.assertRaises(ValueError):
                Gateway('unused:App', auth=auth)


if __name__ == '__main__':
    unittest.main()
