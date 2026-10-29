"""Single-session, in-process execution using the existing browser protocol.

HTTP stays on the caller's loop. A dedicated single-worker executor owns the
application loop; the transport helper uses an I/O thread. No child process is created.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import socket
import tempfile
import threading
from pathlib import Path

from .._browser import widgets
from ..options import Options
from .worker import _run
from .server import Worker, LIFECYCLE_LOG, UploadStore

_active = threading.Lock()


async def lifecycle(app):
    # Runtime/Options are process-global today, so concurrent passthru servers
    # must not silently replace one another's registrations.
    if not _active.acquire(blocking=False):
        raise RuntimeError('Only one passthru server may run in a process')
    previous_runtime = widgets._current_runtime
    previous_options = dict(Options)
    try:
        yield
    finally:
        widgets._current_runtime = previous_runtime
        Options.clear()
        Options.update(previous_options)
        _active.release()


async def run_application(*args, **kwargs):
    # Submit the entire event loop, not individual callbacks: all application
    # operations remain serial and keep their thread affinity.
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='pui-web-application')
    future = asyncio.get_running_loop().run_in_executor(
        executor, lambda: asyncio.run(_run(*args, **kwargs)))
    try:
        return await asyncio.shield(future)
    except asyncio.CancelledError:
        # The gateway closes IPC before cancellation. Let the transport release
        # pending dialogs and the application finish cleanup before restoring globals.
        await asyncio.shield(future)
        raise
    finally:
        executor.shutdown(wait=True)


async def spawn(gateway, session):
    if gateway.upload_root is None:
        gateway.upload_root = tempfile.TemporaryDirectory(prefix='pui-upload-')
    uploads = UploadStore(Path(gateway.upload_root.name) / session.resume_id,
                          gateway.upload_limits)
    uploads.root.mkdir(mode=0o700)
    downloads = gateway._downloads(session)
    parent, child = socket.socketpair()
    task = None
    writer = None
    try:
        parent.setblocking(False)
        reader, writer = await asyncio.open_connection(sock=parent)
        task = asyncio.create_task(run_application(
            child, gateway.factory, gateway.build, gateway.urls.public('pui/images'),
            gateway.title, upload_root=str(uploads.root),
            upload_limits=gateway.upload_limits, download_root=str(downloads.root),
            webroot=gateway.webroot, file_start=gateway.file_start, passthru=True))
        worker = Worker(None, writer, owner=session.owner, uploads=uploads, downloads=downloads,
                        application_task=task)
        gateway.workers[session.resume_id] = worker
        worker.task = asyncio.create_task(gateway._relay(session, worker, reader))
        LIFECYCLE_LOG.info('Passthru application scheduled pid=%s', worker.pid)
        return worker
    except BaseException:
        if writer is not None:
            writer.close()
        if task is not None:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        parent.close()
        child.close()
        uploads.close()
        downloads.close()
        gateway.sessions.remove(session.resume_id)
        gateway._prune_owners()
        raise
