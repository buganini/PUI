"""Connection leases for cookie-owned, per-tab workers.

The gateway serializes access on its event loop. This registry only tracks
ownership and deadlines: callers must stop/reap workers returned by ``expire``
or ``remove``. It never starts a thread, timer, or application callback.
"""
from dataclasses import dataclass
import hmac
import math
import secrets
import time
from typing import Optional

from .protocol import ProtocolError


DEFAULT_SESSION_TTL = 900


@dataclass
class Session:
    resume_id: str
    owner: str
    epoch: Optional[str]
    expires_at: Optional[float] = None  # No deadline while connected, or with TTL 0.


class SessionRegistry:
    def __init__(self, *, session_ttl=DEFAULT_SESSION_TTL, max_sessions=64,
                 clock=time.monotonic):
        if (type(session_ttl) not in (int, float) or
                not math.isfinite(session_ttl) or session_ttl < 0):
            raise ValueError('session_ttl must be a finite, nonnegative number')
        if type(max_sessions) is not int or max_sessions <= 0:
            raise ValueError('max_sessions must be a positive integer')
        self.session_ttl = session_ttl
        self.max_sessions = max_sessions
        self._clock = clock
        self._sessions = {}

    def __len__(self):
        return len(self._sessions)

    def owners(self):
        """Owners with worker reservations, including startup and retained sessions."""
        return {session.owner for session in self._sessions.values()}

    @staticmethod
    def _owner(owner):
        # Owners are opaque ASCII tokens issued/verified by the HTTP gateway.
        if type(owner) is not str or not owner or not owner.isascii():
            raise ProtocolError('BAD_SESSION', 'Invalid browser owner')

    def create(self, owner):
        """Reserve capacity before starting a worker; remove it if startup fails."""
        self._owner(owner)
        if len(self._sessions) >= self.max_sessions:
            raise ProtocolError('OVERLOADED', 'Session capacity reached')
        resume_id = secrets.token_urlsafe(32)
        while resume_id in self._sessions:
            resume_id = secrets.token_urlsafe(32)
        session = Session(resume_id, owner, secrets.token_urlsafe(32))
        self._sessions[resume_id] = session
        return session

    def resume(self, owner, resume_id):
        """Attach a retained worker, or return None for an unknown/expired ID."""
        self._owner(owner)
        session = self._sessions.get(resume_id)
        if session is None:
            return None
        if not hmac.compare_digest(session.owner, owner):
            raise ProtocolError('BAD_SESSION', 'Session belongs to another browser')
        if session.epoch is not None:
            raise ProtocolError('SESSION_BUSY', 'Session already has a connection')
        if session.expires_at is not None and self._clock() >= session.expires_at:
            return None
        session.epoch = secrets.token_urlsafe(32)
        session.expires_at = None
        return session

    def detach(self, resume_id, epoch):
        """Start TTL once; a stale connection cannot detach a newer connection."""
        session = self._sessions.get(resume_id)
        if session is None or epoch is None or session.epoch != epoch:
            return False
        session.epoch = None
        session.expires_at = self._clock() + self.session_ttl if self.session_ttl else None
        return True

    def expire(self):
        """Remove expired reservations and return them for worker teardown."""
        now = self._clock()
        expired = [session for session in self._sessions.values()
                   if session.epoch is None and session.expires_at is not None and now >= session.expires_at]
        for session in expired:
            del self._sessions[session.resume_id]
        return expired

    def remove(self, resume_id, *, epoch=None, owner=None):
        """Remove a worker, optionally checking its owner and connection epoch."""
        session = self._sessions.get(resume_id)
        if session is not None and owner is not None and not hmac.compare_digest(session.owner, owner):
            raise ProtocolError('BAD_SESSION', 'Session belongs to another browser')
        if session is None or (epoch is not None and session.epoch != epoch):
            return None
        return self._sessions.pop(resume_id)

    def clear(self):
        """Remove every reservation and return workers to stop on server shutdown."""
        sessions = list(self._sessions.values())
        self._sessions.clear()
        return sessions
