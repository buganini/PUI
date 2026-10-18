import asyncio
import threading
import unittest
from unittest.mock import patch
from PUI.poster import make_poster


class PosterTests(unittest.TestCase):
    def test_validation_and_elapsed_queue_time(self):
        queue, timers, calls = [], [], []
        post = make_poster(queue.append, lambda delay, callback: timers.append((delay, callback)))
        for delay in (-1, float('nan'), float('inf'), '1'):
            with self.assertRaises(ValueError):
                post(lambda: None, delay=delay)
        with self.assertRaises(TypeError):
            post(None)
        with patch('PUI.poster.time.monotonic', side_effect=[10, 10.25]):
            post(lambda: calls.append(True), delay=500)
            queue.pop()()
        self.assertEqual(timers[0][0], 0.25)
        self.assertEqual(calls, [])
        timers[0][1]()
        self.assertEqual(calls, [True])

    def test_thread_submission(self):
        async def run():
            loop = asyncio.get_running_loop()
            owner = threading.get_ident()
            done = loop.create_future()
            started = loop.time()
            def later(delay, callback):
                self.assertEqual(threading.get_ident(), owner)
                loop.call_later(delay, callback)
            def callback():
                self.assertEqual(threading.get_ident(), owner)
                done.set_result(loop.time() - started)
            post = make_poster(loop.call_soon_threadsafe, later)
            thread = threading.Thread(target=lambda: post(callback, delay=30))
            thread.start()
            thread.join()
            self.assertGreaterEqual(await asyncio.wait_for(done, 1), 0.03)
        asyncio.run(run())
