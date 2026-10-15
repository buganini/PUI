"""Bound anonymous HTTP ownership without evicting logins or worker reservations."""
import unittest
from unittest.mock import patch

from aiohttp import ClientSession, DummyCookieJar, WSServerHandshakeError
from aiohttp.test_utils import TestServer

from PUI.web.protocol import SUBPROTOCOL
from PUI.web.server import COOKIE, Gateway


class OwnerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.limit = patch('PUI.web.server.MAX_ANONYMOUS_OWNERS', 3)
        self.limit.start()
        self.addCleanup(self.limit.stop)
        self.gateway = Gateway('unused:App', base_url='/pui')
        self.server = TestServer(self.gateway.application())
        await self.server.start_server()
        self.client = ClientSession(cookie_jar=DummyCookieJar())

    async def asyncTearDown(self):
        await self.client.close()
        await self.server.close()
        self.assertFalse(self.gateway.owners)

    async def entry(self, cookie=None):
        headers = {} if cookie is None else {'Cookie': COOKIE + '=' + cookie}
        async with self.client.get(self.server.make_url('/pui/'), headers=headers) as response:
            self.assertEqual(response.status, 200)
            await response.read()
            return response.cookies[COOKIE].value

    async def test_anonymous_requests_are_bounded_and_cookie_use_refreshes_lru(self):
        first, second, third = [await self.entry() for _ in range(3)]
        self.assertEqual(await self.entry(first), first)
        fourth = await self.entry()
        self.assertEqual(list(self.gateway.owners), [c.split('.')[0] for c in (third, first, fourth)])
        for _ in range(20):
            await self.entry()
        self.assertEqual(len(self.gateway.owners), 3)
        self.assertFalse(self.gateway.workers)

    async def test_evicted_cookie_cannot_attach_and_entry_issues_a_fresh_owner(self):
        old = await self.entry()
        for _ in range(3):
            await self.entry()
        origin = str(self.server.make_url('/')).rstrip('/')
        with self.assertRaises(WSServerHandshakeError) as caught:
            await self.client.ws_connect(self.server.make_url('/pui/pui/ws'), protocols=[SUBPROTOCOL],
                headers={'Origin': origin, 'Cookie': COOKIE + '=' + old})
        self.assertEqual(caught.exception.status, 403)
        fresh = await self.entry(old)
        self.assertNotEqual(fresh, old)
        self.assertEqual(len(self.gateway.owners), 3)

    async def test_authenticated_owners_are_not_in_the_anonymous_budget(self):
        authenticated = [self.gateway._new_owner(authenticated=True) for _ in range(5)]
        for _ in range(10):
            await self.entry()
        self.assertTrue(all(token in self.gateway.owners for token in authenticated))
        self.assertEqual(len(self.gateway.owners), 8)

    async def test_worker_reservation_protects_owner_before_spawn_completes(self):
        owner = (await self.entry()).split('.')[0]
        session = self.gateway.sessions.create(owner)
        for _ in range(6):
            await self.entry()
        self.assertIn(owner, self.gateway.owners)
        self.assertEqual(len(self.gateway.owners), 4)
        self.gateway.sessions.remove(session.resume_id)
        self.gateway._prune_owners()
        self.assertNotIn(owner, self.gateway.owners)
        self.assertEqual(len(self.gateway.owners), 3)
