"""Exercise the macOS/Windows process strategy on Linux as well."""
import multiprocessing
import sys
import unittest

import web_server


@unittest.skipUnless(sys.platform == 'linux', 'Native server tests already use spawn')
class SpawnServerTests(web_server.ServerTests):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.gateway.context = multiprocessing.get_context('spawn')
