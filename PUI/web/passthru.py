"""Single-session, in-process execution using the existing browser protocol.

HTTP and application callbacks share the caller's event loop. The worker's
transport helper still uses an I/O thread; no child process is created.
"""
import asyncio
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


async def spawn(gateway, session):
    if gateway.upload_root is None:
        gateway.upload_root = tempfile.TemporaryDirectory(prefix='pui-upload-')
    uploads = UploadStore(Path(gateway.upload_root.name) / session.resume_id,
                          gateway.upload_limits)
    uploads.root.mkdir(mode=0o700)
    parent, child = socket.socketpair()
    task = None
    writer = None
    try:
        parent.setblocking(False)
        reader, writer = await asyncio.open_connection(sock=parent)
        task = asyncio.create_task(_run(
            child, gateway.factory, gateway.build, gateway.urls.public('pui/images'),
            gateway.title, upload_root=str(uploads.root),
            upload_limits=gateway.upload_limits, passthru=True))
        worker = Worker(None, writer, owner=session.owner, uploads=uploads,
                        application_task=task)
        gateway.workers[session.resume_id] = worker
        worker.task = asyncio.create_task(gateway._relay(session, worker, reader))
        LIFECYCLE_LOG.info('Passthru application scheduled pid=%s', worker.pid)
        return worker
    except BaseException:
        if task is not None:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        if writer is not None:
            writer.close()
        parent.close()
        child.close()
        uploads.close()
        gateway.sessions.remove(session.resume_id)
        gateway._prune_owners()
        raise
