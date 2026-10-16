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

    def test_positive_ttl_expiry_boundary_cannot_resume(self):
        for ttl in (.5, 12.5):
            registry = SessionRegistry(session_ttl=ttl, clock=lambda: self.now)
            session = registry.create('owner')
            registry.detach(session.resume_id, session.epoch)
            self.now += ttl
            self.assertIsNone(registry.resume('owner', session.resume_id))
            self.assertEqual(registry.expire(), [session])

    def test_remove_checks_owner_without_releasing_foreign_reservations(self):
        session = self.registry.create('owner')
        with self.assertRaises(ProtocolError) as caught:
            self.registry.remove(session.resume_id, owner='other')
        self.assertEqual(caught.exception.code, 'BAD_SESSION')
        self.assertEqual(len(self.registry), 1)
        self.assertIsNone(self.registry.remove(session.resume_id, owner='owner', epoch='old'))
        self.assertIs(self.registry.remove(session.resume_id, owner='owner'), session)
        self.assertIsNone(self.registry.remove(session.resume_id, owner='owner'))

    def test_capacity_counts_retained_workers_until_collected(self):
        registry = SessionRegistry(session_ttl=1, max_sessions=1, clock=lambda: self.now)
        session = registry.create('owner')
        registry.detach(session.resume_id, session.epoch)
        self.now += 1
        with self.assertRaises(ProtocolError) as caught:
            registry.create('second-owner')
        self.assertEqual(caught.exception.code, 'OVERLOADED')
        self.assertEqual(registry.expire(), [session])
        second = registry.create('second-owner')
        self.assertEqual(registry.clear(), [second])
        self.assertEqual(registry.clear(), [])

    def test_zero_ttl_retains_until_explicitly_removed(self):
        registry = SessionRegistry(session_ttl=0, max_sessions=1, clock=lambda: self.now)
        session = registry.create('owner')
        for _ in range(2):
            epoch = session.epoch
            self.assertTrue(registry.detach(session.resume_id, epoch))
            self.assertIsNone(session.expires_at)
            self.now += 10**12
            self.assertEqual(registry.expire(), [])
            with self.assertRaises(ProtocolError) as caught:
                registry.create('other')
            self.assertEqual(caught.exception.code, 'OVERLOADED')
            with self.assertRaises(ProtocolError) as caught:
                registry.resume('other', session.resume_id)
            self.assertEqual(caught.exception.code, 'BAD_SESSION')
            self.assertIs(registry.resume('owner', session.resume_id), session)
            self.assertNotEqual(session.epoch, epoch)
            self.assertFalse(registry.detach(session.resume_id, epoch))
        registry.detach(session.resume_id, session.epoch)
        self.assertIs(registry.remove(session.resume_id), session)
        second = registry.create('other')
        registry.detach(second.resume_id, second.epoch)
        self.assertEqual(registry.clear(), [second])

    def test_invalid_configuration(self):
        for ttl in (-1, True, None, float('inf'), float('nan')):
            with self.assertRaises(ValueError):
                SessionRegistry(session_ttl=ttl)
        for capacity in (0, -1, True, 1.5):
            with self.assertRaises(ValueError):
                SessionRegistry(max_sessions=capacity)


if __name__ == '__main__':
    unittest.main()
