"""Session entry point for a forkserver child or a fresh spawned interpreter."""
import asyncio
import importlib
import logging
import json
import os
import signal
import traceback
import threading

from .transport import Transport
from .messages import validate_client_body
from .protocol import Codec, StreamCodec, Limits, ProtocolError
from ..options import Options
from .render import RenderStream
from .runtime import Runtime
from .images import pack_registry

CAPABILITIES = ['render.snapshot', 'render.patch', 'binding.object_id']
CANVAS_CAPABILITIES = ['canvas.geometry', 'canvas.text', 'canvas.input', 'canvas.path', 'canvas.image', 'canvas.patch']
RENDER_ACK_TIMEOUT = 30
MAX_RENDER_RETRIES = 2
OPTIONS_TIMEOUT = 10
STATE_REFS_CAPABILITY = 'state.refs'


def run(sock, factory, build, image_base='/pui/images', title='', landlock=None, upload_root=None, upload_limits=None, download_root=None, webroot=None, file_start=None):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    os.environ['PUI_BACKEND'] = 'web'
    asyncio.run(_run(sock, factory, build, image_base, title, landlock, upload_root, upload_limits, download_root, webroot, file_start))


async def _run(sock, factory, build, image_base='/pui/images', title='', landlock=None, upload_root=None, upload_limits=None, download_root=None, webroot=None, file_start=None, *, passthru=False):
    transport = None
    runtime = Runtime(asyncio.get_running_loop(), image_base=image_base)
    from .._browser.uploads import UploadStore
    runtime.uploads = UploadStore(upload_root, upload_limits)
    from .files import DownloadStore, FilePicker
    runtime.downloads = DownloadStore(download_root)
    runtime.file_picker = FilePicker(webroot, file_start, runtime.downloads)
    codec = Codec()
    downstream = None
    incoming = changed = None
    epoch = None
    outgoing = received = 0
    stream = RenderStream()
    deadline, retries = None, 0
    loop = asyncio.get_running_loop()
    registered_images = []
    registered_drops = None
    options_deadline = None
    awaiting_options = False
    state_refs_enabled = False
    published_state_refs = None

    async def send(kind, body):
        nonlocal outgoing
        outgoing += 1
        frame = downstream.encode({'v': 1, 'type': kind, 'session': epoch,
                              'seq': outgoing, 'body': body})
        await transport.send(epoch.encode('ascii') + b'\0' + frame)

    application_started = False
    application_thread = threading.get_ident()

    def dialog(kind, message, title, default, options=None):
        nonlocal outgoing
        if threading.get_ident() != application_thread:
            raise RuntimeError("Web dialogs must run on the application thread; use get_poster()")
        if not application_started:
            raise RuntimeError('Call Web dialogs from application callbacks after startup')
        if epoch is None or downstream is None:
            raise ConnectionError('Browser is not connected')
        outgoing += 1
        request_id = str(outgoing)
        body = {'request_id': request_id, 'kind': kind, 'message': message, 'title': title, 'default': default}
        if options is not None:
            body['options'] = options
        frame = downstream.encode({'v': 1, 'type': 'dialog', 'session': epoch,
            'seq': outgoing, 'body': body})
        return transport.dialog(epoch.encode('ascii') + b'\0' + frame,
                                epoch, request_id, kind)

    def file_upload_access(record):
        if threading.get_ident() != application_thread or not application_started:
            raise RuntimeError('Call Web file dialogs from application callbacks after startup')
        if record is not None:
            record = dict(record, epoch=epoch)
        try:
            transport.control(b'F\0' + json.dumps(record).encode('utf-8'))
        except ConnectionError:
            if record is not None:
                raise

    runtime.file_upload_access = file_upload_access
    runtime.dialog = dialog

    async def create_application():
        nonlocal application_started
        create = factory
        if isinstance(factory, str):
            module, name = factory.split(':', 1)
            create = importlib.import_module(module)
            for part in name.split('.'):
                create = getattr(create, part)
        app = create()
        if passthru and app.destroyed:
            raise RuntimeError('This Application instance has ended; restart passthru with a new instance or a factory')
        runtime.app = app
        runtime.app.runtime = runtime
        if title:
            runtime.app.title = title
        runtime.app.sync()
        # Ready precedes construction for URL Options. Keep the gateway's
        # startup watchdog active until application initialization finishes.
        await transport.send(b'S\0')
        application_started = True

    try:
        from .._landlock import apply
        if not passthru:
            apply(landlock)
        transport = Transport(sock, loop)
        incoming = asyncio.create_task(transport.receive())
        changed = asyncio.create_task(runtime.changed.wait())
        while not runtime.quit_requested:
            deadlines = [value for value in (deadline, options_deadline) if value is not None]
            timeout = max(0, min(deadlines) - loop.time()) if deadlines else None
            done, _ = await asyncio.wait((incoming, changed), timeout=timeout,
                                        return_when=asyncio.FIRST_COMPLETED)
            if options_deadline is not None and loop.time() >= options_deadline:
                raise ProtocolError('BAD_FRAME', 'Options were not received before startup timeout')
            refresh = False
            if incoming in done:
                packet = incoming.result()
                incoming = asyncio.create_task(transport.receive())
                operation, payload = packet[:1], packet[1:]
                if operation == b'A':
                    hello = codec.decode(payload)
                    context = hello['body']
                    epoch, outgoing, received = context['epoch'], 0, 1
                    if downstream is not None:
                        downstream.close()
                    downstream = StreamCodec()
                    stream = RenderStream()
                    deadline, retries = None, 0
                    state_refs_enabled = STATE_REFS_CAPABILITY in context['hello']['capabilities']
                    awaiting_options = state_refs_enabled
                    options_deadline = loop.time() + OPTIONS_TIMEOUT if awaiting_options else None
                    published_state_refs = None
                    # Browser drafts/edit sequences restart with each connection,
                    # while the retained worker keeps its nodes and bindings.
                    runtime.reset_connection()
                    if context['hello']['client_build'] != build:
                        raise ProtocolError('VERSION_MISMATCH', 'Reload the client page')
                    if not set(CAPABILITIES) <= set(context['hello']['capabilities']):
                        raise ProtocolError('UNSUPPORTED_CAPABILITY', 'Missing required capabilities')
                    if not awaiting_options and runtime.app is None:
                        Options.clear()
                        await create_application()
                    await send('ready', {'server_build': build, 'capabilities': CAPABILITIES + CANVAS_CAPABILITIES + [STATE_REFS_CAPABILITY],
                        'limits': dict(Limits().__dict__, max_pending_actions=64),
                        'resume_id': context['resume_id'], 'resumed': context['resumed'],
                        'session_ttl': context['session_ttl'], 'upload_limits': runtime.uploads.limits})
                    # Clients advertising state.refs send Options after ready.
                    # Existing protocol clients start with empty host input.
                    if not awaiting_options:
                        refresh = True
                elif operation == b'D':
                    runtime.uploads.discard_pending()
                    epoch = None
                    if downstream is not None:
                        downstream.close()
                    downstream = None
                    stream = RenderStream()
                    deadline = options_deadline = None
                    awaiting_options = False
                elif operation == b'M' and epoch is not None:
                    message = codec.decode(payload)
                    # Transport checks consecutive sequences, consuming dialog
                    # replies itself while application events stay queued.
                    if message['session'] != epoch or message['seq'] <= received:
                        raise ProtocolError('BAD_SEQUENCE', 'Invalid session or sequence')
                    received = message['seq']
                    body, kind = message['body'], message['type']
                    if awaiting_options:
                        if kind != 'options':
                            raise ProtocolError('BAD_FRAME', 'Expected Options before application messages')
                        validate_client_body(kind, body)
                        Options.clear()
                        Options.update(body['values'])
                        awaiting_options = False
                        options_deadline = None
                        if runtime.app is None:
                            await create_application()
                        refresh = True
                    elif kind in ('event', 'binding_write'):
                        try:
                            status, code = runtime.action(kind, body, render_rev=stream.issued_rev)
                        except Exception:
                            traceback.print_exc()
                            status, code = 'error', 'APP_ERROR'
                        if status == 'processed':
                            await transport.send(b'U\0' + epoch.encode('ascii'))
                        await send('result', {'reply_to': received, 'status': status, 'code': code})
                        refresh = True
                    elif kind == 'ack':
                        validate_client_body(kind, body)
                        if stream.acknowledge(**body):
                            deadline = None
                    elif kind == 'resync':
                        validate_client_body(kind, body)
                        stream.resync(**body)
                        refresh = True
                    elif kind == 'container_size':
                        refresh = runtime.size_control(body) or refresh
                    elif kind in ('measure', 'canvas_ack'):
                        refresh = runtime.canvas_control(kind, body)
                    elif kind == 'close':
                        validate_client_body(kind, body)
                        runtime.quit_requested = True
                    else:
                        raise ProtocolError('BAD_FRAME', 'Unsupported client message')
                elif operation != b'M':
                    raise ProtocolError('BAD_FRAME', 'Invalid worker control packet')
            if changed in done:
                runtime.changed.clear()
                changed = asyncio.create_task(runtime.changed.wait())
                refresh = True
            if refresh and runtime.app is not None and not awaiting_options:
                runtime.flush()
                if epoch is not None:
                    # Runtime publishes new records; the serial worker only
                    # reads retained versions for diffing, encoding and retries.
                    stream.offer(runtime.snapshot(copy=False), processed_seq=received, copy=False, trusted=True)
            if epoch is not None and runtime.app is not None and not awaiting_options:
                import json
                targets = runtime.drop_targets()
                if targets != registered_drops:
                    await transport.send(b'T\0' + json.dumps(targets).encode())
                    registered_drops = targets
                for url in runtime.take_open_urls():
                    await send('open_url', {'url': url})
                for result in runtime.drop_results:
                    await send('drop_result', result)
                runtime.drop_results.clear()
                if state_refs_enabled:
                    values = runtime.state_refs.snapshot()
                    if values != published_state_refs:
                        await send('state_ref', {'values': list(values.items())})
                        published_state_refs = values
                images = runtime.images.retain(stream.retained_states())
                if images != registered_images:
                    # Private worker-to-gateway metadata; never forwarded to the browser.
                    await transport.send(b'I\0' + pack_registry(images))
                    registered_images = images
                render = stream.next_render(copy=False)
                if render is not None:
                    await send('render', render)
                    deadline, retries = loop.time() + RENDER_ACK_TIMEOUT, 0
                elif deadline is not None and loop.time() >= deadline:
                    if retries < MAX_RENDER_RETRIES:
                        await send('render', stream.retry(copy=False))
                        retries += 1
                        deadline = loop.time() + RENDER_ACK_TIMEOUT
                    else:
                        # Empty outbound payload asks the gateway to disconnect
                        # this epoch, retaining the worker under its normal TTL.
                        await transport.send(epoch.encode('ascii') + b'\0')
                        epoch, deadline = None, None
                        stream = RenderStream()
        if epoch is not None:
            await send('close', {'reason': 'Application quit'})
    except (asyncio.IncompleteReadError, ConnectionError):
        pass
    except asyncio.TimeoutError:
        # The gateway normally drains output after disconnecting a slow browser.
        # A broken IPC peer must not leave this worker blocked or retry errors
        # through the same stalled stream.
        logging.getLogger(__name__).warning('Worker output IPC did not drain; ending session')
    except Exception as error:
        traceback.print_exc()
        if epoch is not None:
            try:
                await send('error', {'code': getattr(error, 'code', 'APP_ERROR'),
                    'reply_to': None, 'fatal': True, 'message': 'Session failed; see server log'})
            except Exception:
                pass
    finally:
        if downstream is not None:
            downstream.close()
        pending = [task for task in (incoming, changed) if task is not None]
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        try:
            runtime.close()
            Options.clear()
        finally:
            if transport is not None:
                await transport.close()
