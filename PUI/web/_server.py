"""Internal ownership of a Web server's event loop and shutdown."""
from __future__ import annotations
import asyncio
from concurrent.futures import Future
from contextlib import contextmanager
from dataclasses import dataclass, field
import threading


@dataclass
class _Run:
    ready: Future = field(default_factory=Future)
    done: Future = field(default_factory=Future)
    requested: bool = False
    thread: int | None = None
    loop: asyncio.AbstractEventLoop | None = None
    stop: asyncio.Event | None = None


class Server:
    def __init__(self):
        self._lock = threading.Lock()
        # Allocate before start(), so another thread can wait for startup or
        # request shutdown even before the serving thread has been scheduled.
        self._current = _Run()

    @contextmanager
    def running(self):
        with self._lock:
            run = self._current
            if run.thread is not None:
                raise RuntimeError('Web server is already starting or running')
            if run.done.done():
                run = self._current = _Run()
            run.thread = threading.get_ident()
        error = None
        try:
            yield
        except BaseException as exc:
            error = exc
            raise
        finally:
            with self._lock:
                run.loop = run.stop = run.thread = None
                if not run.ready.done():
                    run.ready.set_exception(error or RuntimeError('Web server stopped before startup'))
                if error is None:
                    run.done.set_result(None)
                else:
                    run.done.set_exception(error)

    def stop(self):
        with self._lock:
            run = self._current
            if run.thread == threading.get_ident():
                raise RuntimeError('Blocking stop() cannot run on the Web server thread; call it from another thread')
            run.requested = True
            if run.loop is not None:
                run.loop.call_soon_threadsafe(run.stop.set)
            active = run.thread is not None
        if active:
            run.done.result()

    def wait_started(self, timeout=None):
        with self._lock:
            run = self._current
            if run.thread == threading.get_ident() and not run.ready.done():
                raise RuntimeError('Cannot wait for startup on the Web server thread')
        return run.ready.result(timeout)

    def run(self, app, *, mount_path, host=None, port=None, sock=None,
            handle_signals=True, shutdown_timeout=3):
        from aiohttp import web
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            pass
        else:
            raise RuntimeError('start() owns its event loop; run it in a separate thread')
        try:
            asyncio.run(self._serve(app, mount_path=mount_path, host=host, port=port,
                                   sock=sock, handle_signals=handle_signals,
                                   shutdown_timeout=shutdown_timeout))
        except (KeyboardInterrupt, web.GracefulExit):
            pass

    async def _serve(self, app, *, mount_path, host, port, sock, handle_signals, shutdown_timeout):
        from aiohttp import web
        run = self._current
        with self._lock:
            run.loop = asyncio.get_running_loop()
            run.stop = asyncio.Event()
            if run.requested:
                run.stop.set()
        runner = web.AppRunner(app, handle_signals=handle_signals, shutdown_timeout=shutdown_timeout)
        try:
            if run.stop.is_set():
                return
            await runner.setup()
            if run.stop.is_set():
                return
            site = web.SockSite(runner, sock) if sock is not None else web.TCPSite(runner, host, port)
            await site.start()
            if run.stop.is_set():
                return
            address = runner.addresses[0]
            if isinstance(address, str):
                print('PUI Web: %s (Unix socket %s)' % (mount_path, address), flush=True)
                endpoint = address
            else:
                host, port = address[:2]
                endpoint = 'http://%s:%s%s' % ('[' + host + ']' if ':' in host else host, port, mount_path)
                print('PUI Web: ' + endpoint, flush=True)
            run.ready.set_result(endpoint)
            await run.stop.wait()
        finally:
            try:
                await runner.cleanup()
            finally:
                # Do not let a concurrent stop() enqueue work on a closing loop.
                with self._lock:
                    run.loop = run.stop = None


def run_app(app, *, server=None, **kwargs):
    if server is not None:
        return server.run(app, **kwargs)
    server = Server()
    with server.running():
        return server.run(app, **kwargs)
