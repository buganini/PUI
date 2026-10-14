"""Session ownership, disconnect TTL, and stale-connection race checks."""
import unittest

from PUI.web.protocol import ProtocolError
from PUI.web.sessions import DEFAULT_SESSION_TTL, SessionRegistry


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.now = 100.0
        self.registry = SessionRegistry(clock=lambda: self.now)

    def test_default_900_seconds_starts_at_disconnect(self):
        self.assertEqual(DEFAULT_SESSION_TTL, 900)
        session = self.registry.create('owner')
        self.now += 2000
        self.assertEqual(self.registry.expire(), [])
        self.registry.detach(session.resume_id, session.epoch)
        self.assertEqual(session.expires_at, 3000)
        self.now = 2999.999
        self.assertEqual(self.registry.expire(), [])
        self.now = 3000
        self.assertEqual(self.registry.expire(), [session])
        self.assertEqual(len(self.registry), 0)

    def test_resume_keeps_worker_id_and_changes_connection_epoch(self):
        session = self.registry.create('owner')
        old_epoch = session.epoch
        self.registry.detach(session.resume_id, old_epoch)
        self.now += 899
        resumed = self.registry.resume('owner', session.resume_id)
        self.assertIs(resumed, session)
        self.assertNotEqual(session.epoch, old_epoch)
        self.assertIsNone(session.expires_at)
        self.assertFalse(self.registry.detach(session.resume_id, old_epoch))
        self.assertIsNone(self.registry.remove(session.resume_id, epoch=old_epoch))
        self.now += 1000
        self.assertEqual(self.registry.expire(), [])

    def test_duplicate_disconnect_does_not_extend_deadline(self):
        session = self.registry.create('owner')
        epoch = session.epoch
        self.registry.detach(session.resume_id, epoch)
        self.now += 50
        self.assertFalse(self.registry.detach(session.resume_id, epoch))
        self.assertFalse(self.registry.detach(session.resume_id, None))
        self.assertEqual(session.expires_at, 1000)

    def test_other_owners_and_second_active_connections_are_rejected(self):
        first = self.registry.create('owner')
        second = self.registry.create('owner')
        self.assertNotEqual(first.resume_id, second.resume_id)
        for owner, code in [('other', 'BAD_SESSION'), ('owner', 'SESSION_BUSY')]:
            with self.assertRaises(ProtocolError) as caught:
                self.registry.resume(owner, first.resume_id)
            self.assertEqual(caught.exception.code, code)
        self.assertIsNone(self.registry.resume('owner', 'unknown'))

    def test_zero_ttl_and_expiry_boundary_cannot_resume(self):
        for ttl in (0, 12.5):
            registry = SessionRegistry(session_ttl=ttl, clock=lambda: self.now)
            session = registry.create('owner')
            registry.detach(session.resume_id, session.epoch)
            self.now += ttl
            self.assertIsNone(registry.resume('owner', session.resume_id))
            self.assertEqual(registry.expire(), [session])

    def test_capacity_counts_retained_workers_until_collected(self):
        registry = SessionRegistry(session_ttl=0, max_sessions=1)
        session = registry.create('owner')
        registry.detach(session.resume_id, session.epoch)
        with self.assertRaises(ProtocolError) as caught:
            registry.create('second-owner')
        self.assertEqual(caught.exception.code, 'OVERLOADED')
        self.assertEqual(registry.expire(), [session])
        second = registry.create('second-owner')
        self.assertEqual(registry.clear(), [second])
        self.assertEqual(registry.clear(), [])

    def test_invalid_configuration(self):
        for ttl in (-1, True, None, float('inf'), float('nan')):
            with self.assertRaises(ValueError):
                SessionRegistry(session_ttl=ttl)
        for capacity in (0, -1, True, 1.5):
            with self.assertRaises(ValueError):
                SessionRegistry(max_sessions=capacity)


if __name__ == '__main__':
    unittest.main()
