"""Optional login gates, cookie separation and authenticated worker sessions."""
import asyncio
import re
import unittest

from aiohttp import ClientSession, CookieJar, WSServerHandshakeError, WSMsgType
from aiohttp.test_utils import TestServer

from PUI.web.protocol import Codec, StreamCodec, SUBPROTOCOL
from PUI.web.server import COOKIE, LOGIN_COOKIE, Gateway


class AuthTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.calls = []
        def auth(username, password):
            self.calls.append((username, password))
            return {'auth': {'test': 'test123'}.get(username) == password}
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

    async def test_auth_result_requires_boolean_dictionary(self):
        fields = await self.form()
        for value in (True, False, None, {}, {'ai': True}, {'auth': False, 'ai': True},
                      {'auth': 1}, {'auth': True, 'ai': 'yes'}):
            self.gateway.login_attempts.clear()
            self.gateway.auth = lambda u, p, result=value: result
            response = await self.post(fields)
            self.assertEqual(response.status, 200)
            self.assertNotIn(COOKIE, response.cookies)
            self.assertEqual(self.gateway.owners, {})
        self.gateway.login_attempts.clear()
        self.gateway.auth = lambda u, p: {'auth': True, 'ai': True}
        response = await self.post(fields)
        self.assertEqual(response.status, 303)
        self.assertEqual(list(self.gateway.owners.values()), [{'auth': True, 'ai': True}])

    async def test_account_failure_backoff_and_reset(self):
        fields = await self.form()
        for seconds in (1, 2, 4, 8, 16, 30, 30):
            response = await self.post(dict(fields, password='wrong'))
            self.assertEqual(response.headers['Retry-After'], str(seconds))
            count = len(self.calls)
            # A fresh login cookie does not reset the account's cooldown.
            fields = await self.form()
            response = await self.post(fields)
            self.assertEqual(response.status, 429)
            self.assertEqual(len(self.calls), count)
            self.gateway.login_attempts['test']['until'] = 0
        response = await self.post(fields)
        self.assertEqual(response.status, 303)
        self.assertNotIn('test', self.gateway.login_attempts)

    async def test_backoff_account_isolation_and_bounded_records(self):
        from unittest.mock import patch
        fields = await self.form()
        response = await self.post(dict(fields, password='wrong'))
        await response.read()
        with patch('PUI.web.server.MAX_LOGIN_ACCOUNTS', 1):
            response = await self.post(dict(fields, username='another'))
            self.assertEqual(response.status, 503)
            self.assertEqual(len(self.calls), 1)
            self.gateway.login_attempts['test']['updated'] -= 901
            response = await self.post(dict(fields, username='another'))
            self.assertEqual(response.status, 200)
            self.assertEqual(len(self.gateway.login_attempts), 1)
            self.assertNotIn('test', self.gateway.login_attempts)
        # A different account remains able to authenticate.
        response = await self.post(fields)
        self.assertEqual(response.status, 303)

    async def test_parallel_login_does_not_repeat_callback(self):
        fields = await self.form()
        entered, release = asyncio.Event(), asyncio.Event()
        calls = []
        async def auth(username, password):
            calls.append(username)
            entered.set()
            await release.wait()
            return {'auth': False}
        self.gateway.auth = auth
        first = asyncio.create_task(self.post(fields))
        try:
            await entered.wait()
            response = await self.post(fields)
            self.assertEqual(response.status, 429)
            self.assertEqual(calls, ['test'])
        finally:
            release.set()
            response = await first
            await response.read()

    async def test_main_and_login_pages_disallow_framing(self):
        def check(response):
            self.assertEqual(response.headers['Content-Security-Policy'], "frame-ancestors 'none'")
            self.assertEqual(response.headers['X-Frame-Options'], 'DENY')

        async with self.client.get(self.server.make_url('/pui/')) as response:
            check(response)
            self.assertIn('<title>Sign in', await response.text())
        fields = await self.form()
        async with await self.post(dict(fields, password='wrong')) as response:
            check(response)
            self.assertIn('Invalid username or password.', await response.text())
        async with await self.post(fields) as response:
            self.assertEqual(response.status, 429)
            check(response)
        await asyncio.sleep(1.05)
        async with await self.post(fields) as response:
            self.assertEqual(response.status, 303)
        async with self.client.get(self.server.make_url('/pui/')) as response:
            check(response)
            self.assertIn('id="pui-root"', await response.text())

    async def logout_form(self):
        async with await self.post(await self.form()) as response:
            self.assertEqual(response.status, 303)
        async with self.client.get(self.server.make_url('/pui/')) as response:
            html = await response.text()
            return {'csrf': re.search(r'data-logout-token="([^"]+)"', html).group(1)}

    async def logout(self, data, **kwargs):
        return await self.client.post(self.server.make_url('/pui/pui/logout'), data=data,
            headers=kwargs.pop('headers', {'Origin': self.origin}), allow_redirects=False, **kwargs)

    async def resume_owner(self):
        async with self.client.get(self.server.make_url('/pui/')) as response:
            html = await response.text()
            marker = re.search(r'data-resume-owner="([^"]+)"', html).group(1)
            # This visible marker cannot be used as the owner cookie or logout token.
            cookie = response.cookies[COOKIE].value
            self.assertNotIn(cookie.split('.')[0], html)
            self.assertNotEqual(marker, cookie.split('.')[1])
            self.assertNotEqual(marker, re.search(r'data-logout-token="([^"]+)"', html).group(1))
            return marker

    async def test_resume_owner_is_stable_until_new_login(self):
        fields = await self.logout_form()
        marker = await self.resume_owner()
        self.assertEqual(await self.resume_owner(), marker)
        async with await self.logout(fields) as response:
            self.assertEqual(response.status, 303)
        async with await self.post(await self.form()) as response:
            self.assertEqual(response.status, 303)
        self.assertNotEqual(await self.resume_owner(), marker)

    async def test_gateway_restart_requires_login_and_changes_resume_owner(self):
        await self.logout_form()
        marker = await self.resume_owner()
        auth = self.gateway.auth
        port = self.server.port
        await self.server.close()
        self.gateway = Gateway('web_fixture:App', base_url='/pui', auth=auth, session_ttl=0)
        self.server = TestServer(self.gateway.application(), port=port)
        await self.server.start_server()
        self.origin = str(self.server.make_url('/')).rstrip('/')
        # Keep the previous browser cookies, as a real server restart does.
        async with await self.post(await self.form()) as response:
            self.assertEqual(response.status, 303)
        self.assertNotEqual(await self.resume_owner(), marker)

    async def test_logout_rejects_csrf_origin_duplicate_fields_and_oversized_forms(self):
        fields = await self.logout_form()
        for data, headers, status in (
            ({'csrf': 'forged'}, {'Origin': self.origin}, 403),
            (fields, {'Origin': 'https://other.example'}, 403),
            (fields, [('Origin', self.origin), ('Origin', self.origin)], 403),
            (list(fields.items()) * 2, {'Origin': self.origin}, 400),
            ({'csrf': 'x' * 2048}, {'Origin': self.origin}, 413),
        ):
            async with await self.logout(data, headers=headers) as response:
                self.assertEqual(response.status, status)
        async with self.client.get(self.server.make_url('/pui/pui/logout')) as response:
            self.assertEqual(response.status, 405)
        async with self.client.get(self.server.make_url('/pui/')) as response:
            self.assertIn('id="pui-root"', await response.text())

    async def test_logout_revokes_cookie_and_reaps_active_and_retained_workers(self):
        fields = await self.logout_form()
        cookie = self.client.cookie_jar.filter_cookies(self.server.make_url('/pui/'))[COOKIE].value
        codec = Codec()
        hello = codec.encode({'v': 1, 'type': 'hello', 'session': None, 'seq': 1,
            'body': {'client_build': self.gateway.build, 'capabilities': [
                'render.snapshot', 'render.patch', 'binding.object_id'],
                'viewport': {'width': 100, 'height': 100, 'dpr': 1}, 'resume_id': None}})
        async def connect():
            ws = await self.client.ws_connect(self.server.make_url('/pui/pui/ws'),
                protocols=[SUBPROTOCOL], headers={'Origin': self.origin})
            self.addAsyncCleanup(ws.close)
            return ws
        sockets = []
        for _ in range(2):
            ws = await connect()
            sockets.append(ws)
            await ws.send_bytes(hello)
            decoder = StreamCodec()
            try:
                self.assertEqual(decoder.decode((await ws.receive()).data)['type'], 'ready')
                self.assertEqual(decoder.decode((await ws.receive()).data)['type'], 'render')
            finally:
                decoder.close()
        await sockets[1].close()
        pending = await connect()  # Handshake accepted before logout, hello still pending.
        async with await self.logout(fields) as response:
            self.assertEqual(response.status, 303)
            self.assertEqual(response.headers['Location'], '/pui/')
            self.assertEqual(response.cookies[COOKIE]['max-age'], '0')
        self.assertEqual(self.gateway.workers, {})
        self.assertEqual(len(self.gateway.sessions), 0)
        closed = await sockets[0].receive()
        self.assertEqual((closed.type, closed.data), (WSMsgType.CLOSE, 4001))
        await pending.send_bytes(hello)
        closed = await pending.receive()
        self.assertEqual((closed.type, closed.data), (WSMsgType.CLOSE, 4001))
        await self.form()
        async with ClientSession(cookie_jar=CookieJar(unsafe=True)) as replay:
            replay.cookie_jar.update_cookies({COOKIE: cookie}, response_url=self.server.make_url('/pui/'))
            async with replay.get(self.server.make_url('/pui/')) as response:
                self.assertIn('<title>Sign in', await response.text())
            with self.assertRaises(WSServerHandshakeError) as caught:
                await replay.ws_connect(self.server.make_url('/pui/pui/ws'),
                    protocols=[SUBPROTOCOL], headers={'Origin': self.origin})
            self.assertEqual(caught.exception.status, 403)
        async with await self.post(await self.form()) as response:
            self.assertEqual(response.status, 303)
            self.assertNotEqual(response.cookies[COOKIE].value, cookie)

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

    async def test_optional_prompt_is_literal_text_and_survives_failed_login(self):
        for prompt in (None, ''):
            self.gateway.auth_prompt = prompt
            async with self.client.get(self.server.make_url('/pui/')) as response:
                html = await response.text()
                self.assertNotIn('pui-auth-prompt', html)
                self.assertIn('<h1>PUI</h1>', html)
        self.gateway.auth_prompt = '<script>alert("test")</script>\nTest & demo'
        self.gateway.title = 'Example <app> & login'
        expected = ('<p class="pui-auth-prompt">&lt;script&gt;alert(&quot;test&quot;)'
                    '&lt;/script&gt;\nTest &amp; demo</p>')
        async with self.client.get(self.server.make_url('/pui/')) as response:
            html = await response.text()
            self.assertIn(expected, html)
            self.assertNotIn('<script>', html)
            self.assertIn('<title>Sign in · Example &lt;app&gt; &amp; login</title>', html)
            self.assertIn('<h1>Example &lt;app&gt; &amp; login</h1>', html)
        fields = await self.form()
        async with await self.post(dict(fields, password='wrong')) as response:
            html = await response.text()
            self.assertIn(expected, html)
            self.assertIn('<h1>Example &lt;app&gt; &amp; login</h1>', html)
        self.gateway.auth = None
        async with self.client.get(self.server.make_url('/pui/')) as response:
            html = await response.text()
            self.assertNotIn('pui-auth-prompt', html)
            self.assertIn('id="pui-root"', html)

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
                self.assertEqual(response.headers['Content-Security-Policy'], "frame-ancestors 'none'")
                self.assertEqual(response.headers['X-Frame-Options'], 'DENY')
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
            return {'auth': username == 'test' and password == 'test123'}
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

    async def test_login_survives_separate_tabs_resume_and_crash(self):
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
        for prompt in (False, 123, {}):
            with self.subTest(auth_prompt=prompt), self.assertRaises(ValueError):
                Gateway('unused:App', auth_prompt=prompt)


if __name__ == '__main__':
    unittest.main()
