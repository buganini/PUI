"""Adapt UI dispatchers to a common delayed-callback interface."""
import math
import time


def make_poster(submit, call_later):
    """Expose delay in milliseconds; call_later receives seconds on the UI loop."""
    def post(callback, *, delay=0):
        if not callable(callback):
            raise TypeError('callback must be callable')
        if not isinstance(delay, (int, float)) or not math.isfinite(delay) or delay < 0:
            raise ValueError('delay must be a finite non-negative number of milliseconds')
        if delay == 0:
            submit(callback)
            return
        deadline = time.monotonic() + delay / 1000

        def schedule():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                callback()
            else:
                call_later(remaining, callback)

        submit(schedule)
    return post
