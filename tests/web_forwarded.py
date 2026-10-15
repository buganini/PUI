"""Forwarded scheme handling through real HTTP/WebSocket requests."""
import unittest
from contextlib import AsyncExitStack
from pathlib import Path
import socket
import sys
import tempfile
from aiohttp import web, ClientSession, CookieJar, UnixConnector, WSServerHandshakeError
from aiohttp.test_utils import TestServer
from PUI.web.protocol import SUBPROTOCOL
from PUI.web.server import Gateway, _unix_listener


class ForwardedTests(unittest.IsolatedAsyncioTestCase):
    async def check_scheme(self, gateway, headers, scheme, *, listen='127.0.0.1'):
        async with AsyncExitStack() as stack:
            connector = None
            if listen == 'unix':
                directory = stack.enter_context(tempfile.TemporaryDirectory())
                path = str(Path(directory) / 'server.sock')
                listener = stack.enter_context(_unix_listener(path))
                runner = web.AppRunner(gateway.application())
                await runner.setup()
                stack.push_async_callback(runner.cleanup)
                await web.SockSite(runner, listener).start()
                connector = UnixConnector(path=path)
                make_url = lambda path: 'http://public.example:8443' + path
            else:
                server = await stack.enter_async_context(TestServer(gateway.application(), host=listen))
                make_url = server.make_url
            jar = CookieJar(unsafe=True, treat_as_secure_origin=make_url('/'))
            async with ClientSession(cookie_jar=jar, connector=connector) as client:
                headers = dict(headers, Host='public.example:8443')
                async with client.get(make_url('/pui/'), headers=headers) as response:
                    self.assertEqual(response.status, 200)
                    self.assertEqual(bool(response.cookies['pui_owner']['secure']), scheme == 'https')
                    self.assertEqual(response.cookies['pui_owner']['path'], '/pui/')
                    self.assertIn('data-ws="/pui/pui/ws"', await response.text())
                endpoint = make_url('/pui/pui/ws')
                for origin in ('https://other.example',
                               ('http' if scheme == 'https' else 'https') + '://public.example:8443'):
                    with self.assertRaises(WSServerHandshakeError) as raised:
                        await client.ws_connect(endpoint, protocols=[SUBPROTOCOL],
                                                headers=dict(headers, Origin=origin))
                    self.assertEqual(raised.exception.status, 403)
                async with client.ws_connect(endpoint, protocols=[SUBPROTOCOL],
                        headers=dict(headers, Origin=scheme + '://public.example:8443')) as websocket:
                    self.assertEqual(websocket.protocol, SUBPROTOCOL)
            # These are handshake-only probes; no application worker is created.
            self.assertEqual(gateway.workers, {})

    async def test_default_loopback_https_and_direct_http(self):
        for headers, scheme in (({}, 'http'), ({'X-Forwarded-Proto': 'http'}, 'http'),
                                ({'X-Forwarded-Proto': 'https'}, 'https')):
            with self.subTest(headers=headers):
                await self.check_scheme(Gateway('unused:Application', base_url='/pui'), headers, scheme)

    async def test_default_ipv6_loopback(self):
        await self.check_scheme(Gateway('unused:Application', base_url='/pui'),
                                {'X-Forwarded-Proto': 'https'}, 'https', listen='::1')

    @unittest.skipIf(sys.platform == 'win32' or not hasattr(socket, 'AF_UNIX'), 'Unix listener required')
    async def test_unix_default_explicit_and_disabled_trust(self):
        for proxies, scheme in ((None, 'https'), ('unix', 'https'), ([], 'http'),
                                (['127.0.0.1'], 'http')):
            with self.subTest(proxies=proxies):
                await self.check_scheme(Gateway('unused:Application', base_url='/pui', trusted_proxies=proxies),
                                        {'X-Forwarded-Proto': 'https'}, scheme, listen='unix')

    async def test_unix_trust_does_not_trust_tcp_peers(self):
        await self.check_scheme(Gateway('unused:Application', base_url='/pui', trusted_proxies=['unix']),
                                {'X-Forwarded-Proto': 'https'}, 'http')

    async def test_explicit_address_and_cidr_replace_defaults(self):
        for proxies in (['127.0.0.1'], ['127.0.0.0/8'], '127.0.0.1/32'):
            with self.subTest(proxies=proxies):
                await self.check_scheme(Gateway('unused:Application', base_url='/pui', trusted_proxies=proxies),
                                        {'X-Forwarded-Proto': 'https'}, 'https')

    async def test_untrusted_or_disabled_ignores_spoofed_forwarding_headers(self):
        for proxies in ([], ['192.0.2.0/24']):
            for proto in ('https', 'https,http'):
                with self.subTest(proxies=proxies, proto=proto):
                    await self.check_scheme(Gateway('unused:Application', base_url='/pui', trusted_proxies=proxies),
                        {'X-Forwarded-Proto': proto, 'X-Forwarded-For': '127.0.0.1',
                         'X-Real-IP': '127.0.0.1', 'Forwarded': 'for=127.0.0.1;proto=https'}, 'http')

    async def test_forwarded_host_and_standard_forwarded_header_do_not_override_host_or_scheme(self):
        await self.check_scheme(Gateway('unused:Application', base_url='/pui'),
            {'X-Forwarded-Host': 'other.example', 'Forwarded': 'host=other.example;proto=https'}, 'http')

    async def test_host_policy_still_applies_with_trusted_protocol(self):
        gateway = Gateway('unused:Application', base_url='/pui', allow_hosts=['public.example'])
        async with TestServer(gateway.application()) as server:
            async with ClientSession() as client:
                for path in ('/pui/', '/pui/pui/ws', '/pui/assets/' + gateway.build + '/client.js'):
                    async with client.get(server.make_url(path), headers={
                            'Host': 'other.example', 'X-Forwarded-Host': 'public.example',
                            'X-Forwarded-Proto': 'https'}) as response:
                        self.assertEqual(response.status, 403)
            self.assertEqual(gateway.workers, {})

    async def test_trusted_proxy_must_send_one_valid_protocol(self):
        gateway = Gateway('unused:Application', base_url='/pui')
        async with TestServer(gateway.application()) as server:
            async with ClientSession() as client:
                cases = [[('X-Forwarded-Proto', value)] for value in ('', 'ftp', 'HTTPS', 'https, http')]
                cases.append([('X-Forwarded-Proto', 'https'), ('X-Forwarded-Proto', 'http')])
                for headers in cases:
                    for path in ('/pui/', '/pui/pui/ws'):
                        with self.subTest(headers=headers, path=path):
                            async with client.get(server.make_url(path), headers=headers) as response:
                                self.assertEqual(response.status, 400)
            self.assertEqual(gateway.workers, {})

    def test_invalid_trust_configuration(self):
        for value in (True, ['*'], ['localhost'], ['https://127.0.0.1'],
                      ['127.0.0.1/33'], ['::1/129'], [123], [None]):
            with self.subTest(value=value), self.assertRaises(ValueError):
                Gateway('unused:Application', trusted_proxies=value)
