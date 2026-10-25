"""One upstream mount served through different public prefixes, without base_url."""
import asyncio
import re
import unittest
from contextlib import AsyncExitStack
from urllib.parse import urljoin

from aiohttp import ClientSession, CookieJar, DummyCookieJar, WSMsgType, web
from aiohttp.test_utils import TestServer
from multidict import CIMultiDict
from PUI.web.protocol import SUBPROTOCOL
from PUI.web.server import COOKIE, LOGIN_COOKIE, Gateway


class RelativeProxyTests(unittest.IsolatedAsyncioTestCase):
    async def test_relative_links_login_retry_websocket_and_cookie_isolation(self):
        gateway = Gateway('unused:App', mount_path='/internal/',
                          auth=lambda u, p: {'auth': u == 'user' and p == 'password'})
        async with AsyncExitStack() as stack:
            upstream = await stack.enter_async_context(TestServer(gateway.application()))
            forwarding = await stack.enter_async_context(ClientSession(cookie_jar=DummyCookieJar(), auto_decompress=False))

            async def proxy(request):
                prefix = '/' + request.match_info['app'] + '/'
                target = upstream.make_url('/internal/' + request.match_info['tail'])
                headers = CIMultiDict(request.headers)
                if request.headers.get('Upgrade', '').lower() == 'websocket':
                    async with forwarding.ws_connect(target, protocols=[SUBPROTOCOL],
                            headers={'Host': request.host, 'Origin': request.headers['Origin'],
                                     'Cookie': request.headers.get('Cookie', '')}) as remote:
                        browser = web.WebSocketResponse(protocols=[SUBPROTOCOL])
                        await browser.prepare(request)
                        async def pump(source, destination):
                            async for message in source:
                                if message.type == WSMsgType.BINARY:
                                    await destination.send_bytes(message.data)
                                elif message.type == WSMsgType.TEXT:
                                    await destination.send_str(message.data)
                        tasks = [asyncio.create_task(pump(browser, remote)),
                                 asyncio.create_task(pump(remote, browser))]
                        try:
                            await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                        finally:
                            for task in tasks:
                                task.cancel()
                            await asyncio.gather(*tasks, return_exceptions=True)
                        return browser
                async with forwarding.request(request.method, target, headers=headers,
                        data=await request.read(), allow_redirects=False) as response:
                    outgoing = CIMultiDict()
                    for name, value in response.headers.items():
                        if name.lower() in ('content-length', 'transfer-encoding', 'connection'):
                            continue
                        if name.lower() == 'set-cookie':
                            value = value.replace('Path=/internal/', 'Path=' + prefix)
                        outgoing.add(name, value)
                    return web.Response(status=response.status, headers=outgoing, body=await response.read())

            app = web.Application()
            app.router.add_route('*', '/{app}/{tail:.*}', proxy)
            public = await stack.enter_async_context(TestServer(app))
            client = await stack.enter_async_context(ClientSession(cookie_jar=CookieJar(unsafe=True)))
            origin = str(public.make_url('/')).rstrip('/')
            owners = []
            for name in ('first', 'second'):
                entry = str(public.make_url('/' + name + '/'))
                async with client.get(entry) as response:
                    html = await response.text()
                    self.assertEqual(response.cookies[LOGIN_COOKIE]['path'], '/' + name + '/')
                csrf = re.search(r'name="csrf" value="([^"]+)"', html)[1]
                action = urljoin(entry, re.search(r'action="([^"]+)"', html)[1])
                self.assertEqual(action, entry + 'pui/login')
                fields = {'username': 'user', 'password': 'wrong', 'csrf': csrf}
                async with client.post(action, data=fields, headers={'Origin': origin}) as response:
                    failed = await response.text()
                    self.assertIn('Invalid username', failed)
                    stylesheet = urljoin(str(response.url), re.search(r'rel="stylesheet" href="([^"]+)"', failed)[1])
                    retry = urljoin(str(response.url), re.search(r'action="([^"]+)"', failed)[1])
                    self.assertEqual(retry, action)
                    self.assertTrue(stylesheet.startswith(entry + 'assets/'))
                async with client.get(stylesheet) as response:
                    self.assertEqual(response.status, 200)
                gateway.login_attempts.clear()
                fields['password'] = 'password'
                async with client.post(retry, data=fields, headers={'Origin': origin}, allow_redirects=False) as response:
                    self.assertEqual(response.status, 303)
                    self.assertEqual(urljoin(retry, response.headers['Location']), entry)
                    self.assertEqual(response.cookies[COOKIE]['path'], '/' + name + '/')
                    owners.append(response.cookies[COOKIE].value)
                async with client.get(entry) as response:
                    html = await response.text()
                    self.assertIn('data-entry="./"', html)
                    self.assertNotIn('/internal/', html)
                script = urljoin(entry, re.search(r'<script type="module" src="([^"]+)"', html)[1])
                async with client.get(script) as response:
                    self.assertEqual(response.status, 200)
                endpoint = urljoin(entry, re.search(r'data-ws="([^"]+)"', html)[1])
                async with client.ws_connect(endpoint, protocols=[SUBPROTOCOL], headers={'Origin': origin}) as ws:
                    self.assertEqual(ws.protocol, SUBPROTOCOL)
                if name == 'second':
                    action = urljoin(entry, re.search(r'data-logout="([^"]+)"', html)[1])
                    csrf = re.search(r'data-logout-token="([^"]+)"', html)[1]
                    async with client.post(action, data={'csrf': csrf}, headers={'Origin': origin},
                                           allow_redirects=False) as response:
                        self.assertEqual(urljoin(action, response.headers['Location']), entry)
                        self.assertEqual(response.cookies[COOKIE]['max-age'], '0')
                        self.assertEqual(response.cookies[COOKIE]['path'], '/second/')
            self.assertNotEqual(*owners)
            async with client.get(public.make_url('/first/')) as response:
                self.assertIn('id="pui-root"', await response.text())
            async with client.get(public.make_url('/second/')) as response:
                self.assertIn('Sign in', await response.text())
