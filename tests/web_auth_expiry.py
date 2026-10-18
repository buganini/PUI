"""Real worker retention across authentication expiry and cookie rotation."""
import re
import time
import unittest
from aiohttp import WSMsgType
import web_server
from PUI.web.server import COOKIE


class ExpiryTests(unittest.IsolatedAsyncioTestCase):
    asyncTearDown = web_server.ServerTests.asyncTearDown
    connect = web_server.ServerTests.connect
    read = web_server.ServerTests.read
    send = web_server.ServerTests.send
    nodes = web_server.ServerTests.nodes
    wait_until = web_server.ServerTests.wait_until
    click_increment = web_server.ServerTests.click_increment

    async def asyncSetUp(self):
        await web_server.ServerTests.asyncSetUp(self)
        self.gateway.auth = lambda u, p: {'auth': u in ('test', 'other') and p == 'secret'}
        self.gateway.sessions.session_ttl = 900

    async def login(self, username='test'):
        response = await self.client.get(self.origin + '/pui/')
        html = await response.text()
        csrf = re.search(r'name="csrf" value="([^"]+)"', html).group(1)
        response = await self.client.post(self.origin + '/pui/pui/login',
            data=dict(username=username, password='secret', csrf=csrf),
            headers={'Origin': self.origin}, allow_redirects=False)
        self.assertEqual(response.status, 303)
        token = response.cookies[COOKIE].value.split('.')[0]
        await response.read()
        return token

    async def test_idle_expiry_relogin_resumes_same_worker(self):
        owner = await self.login()
        marker = self.gateway.owners[owner]['resume_marker']
        ws = await self.connect()
        ready, tree = await self.read(ws), await self.read(ws)
        key = ready['body']['resume_id']
        worker = self.gateway.workers[key]
        entry = self.gateway.owners[owner]
        entry['active'] -= 100
        before = entry['active']
        await self.click_increment(ws, ready, tree)
        self.assertEqual((await self.read(ws))['body']['status'], 'processed')
        self.assertIn('count=1', str(await self.read(ws)))
        self.assertGreater(entry['active'], before)
        await self.send(ws, ready['session'], 4, 'ack',
                        {'render_rev': 2, 'applied_rev': 2, 'status': 'applied'})
        entry['active'] -= 4201
        await self.gateway._expire()
        self.assertEqual((await ws.receive()).type, WSMsgType.CLOSE)
        self.assertEqual(ws.close_code, 4004)
        self.assertIn(key, self.gateway.workers)
        self.assertIsNone(self.gateway.sessions._sessions[key].epoch)
        new_owner = await self.login()
        self.assertNotEqual(owner, new_owner)
        self.assertNotIn(owner, self.gateway.owners)
        self.assertEqual(self.gateway.owners[new_owner]['resume_marker'], marker)
        self.assertIs(self.gateway.workers[key], worker)
        resumed = await self.connect(resume_id=key)
        self.assertTrue((await self.read(resumed))['body']['resumed'])
        self.assertIn('count=1', str(await self.read(resumed)))

    async def test_max_age_cannot_be_extended_and_other_account_cannot_resume(self):
        owner = await self.login()
        ws = await self.connect()
        ready = await self.read(ws)
        await self.read(ws)
        key = ready['body']['resume_id']
        self.gateway.owners[owner]['created'] -= 86401
        self.gateway.touch_owner(owner)
        self.assertFalse(self.gateway.owner_valid(owner))
        await self.gateway._expire()
        await ws.receive()
        new_owner = await self.login('other')
        self.assertEqual(self.gateway.workers[key].owner, owner)
        self.assertNotEqual(self.gateway.owners[owner]['resume_marker'],
                            self.gateway.owners[new_owner]['resume_marker'])
        denied = await self.connect(resume_id=key)
        self.assertEqual((await denied.receive()).type, WSMsgType.CLOSE)
