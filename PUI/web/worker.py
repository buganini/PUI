"""Runs after the clean standard-library fork supervisor forks a session."""
import asyncio
import importlib
import logging
import os
import signal
import traceback

from .ipc import read_packet, write_packet
from .messages import validate_client_body
from .protocol import Codec, Limits, ProtocolError
from .render import RenderStream
from .runtime import Runtime
from .images import pack_registry

CAPABILITIES = ['render.snapshot', 'render.patch', 'binding.object_id']
CANVAS_CAPABILITIES = ['canvas.geometry', 'canvas.text', 'canvas.input', 'canvas.path', 'canvas.image']
RENDER_ACK_TIMEOUT = 30
MAX_RENDER_RETRIES = 2


def run(sock, factory, build, image_base='/pui/images'):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    os.environ['PUI_BACKEND'] = 'web'
    asyncio.run(_run(sock, factory, build, image_base))


async def _run(sock, factory, build, image_base='/pui/images'):
    sock.setblocking(False)
    reader, writer = await asyncio.open_connection(sock=sock)
    runtime = Runtime(asyncio.get_running_loop(), image_base=image_base)
    codec = Codec()
    incoming = changed = None
    epoch = None
    outgoing = received = 0
    stream = RenderStream()
    deadline, retries = None, 0
    loop = asyncio.get_running_loop()
    registered_images = []

    async def send(kind, body):
        nonlocal outgoing
        outgoing += 1
        frame = codec.encode({'v': 1, 'type': kind, 'session': epoch,
                              'seq': outgoing, 'body': body})
        await write_packet(writer, epoch.encode('ascii') + b'\0' + frame)

    try:
        module, name = factory.split(':', 1)
        create = importlib.import_module(module)
        for part in name.split('.'):
            create = getattr(create, part)
        runtime.app = create()
        runtime.app.sync()
        incoming = asyncio.create_task(read_packet(reader))
        changed = asyncio.create_task(runtime.changed.wait())
        while not runtime.quit_requested:
            timeout = None if deadline is None else max(0, deadline - loop.time())
            done, _ = await asyncio.wait((incoming, changed), timeout=timeout,
                                        return_when=asyncio.FIRST_COMPLETED)
            refresh = False
            if incoming in done:
                packet = incoming.result()
                incoming = asyncio.create_task(read_packet(reader))
                operation, payload = packet[:1], packet[1:]
                if operation == b'A':
                    hello = codec.decode(payload)
                    context = hello['body']
                    epoch, outgoing, received = context['epoch'], 0, 1
                    stream = RenderStream()
                    deadline, retries = None, 0
                    # Browser drafts/edit sequences restart with each connection,
                    # while the retained worker keeps its nodes and bindings.
                    runtime.reset_connection()
                    if context['hello']['client_build'] != build:
                        raise ProtocolError('VERSION_MISMATCH', 'Reload the client page')
                    if not set(CAPABILITIES) <= set(context['hello']['capabilities']):
                        raise ProtocolError('UNSUPPORTED_CAPABILITY', 'Missing required capabilities')
                    await send('ready', {'server_build': build, 'capabilities': CAPABILITIES + CANVAS_CAPABILITIES,
                        'limits': dict(Limits().__dict__, max_pending_actions=64),
                        'resume_id': context['resume_id'], 'resumed': context['resumed'],
                        'session_ttl': context['session_ttl']})
                    refresh = True
                elif operation == b'D':
                    epoch = None
                    stream = RenderStream()
                    deadline = None
                elif operation == b'M' and epoch is not None:
                    message = codec.decode(payload)
                    if message['session'] != epoch or message['seq'] != received + 1:
                        raise ProtocolError('BAD_SEQUENCE', 'Invalid session or sequence')
                    received = message['seq']
                    body, kind = message['body'], message['type']
                    if kind in ('event', 'binding_write'):
                        try:
                            status, code = runtime.action(kind, body, render_rev=stream.issued_rev)
                        except Exception:
                            traceback.print_exc()
                            status, code = 'error', 'APP_ERROR'
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
            if refresh:
                runtime.flush()
                if epoch is not None:
                    stream.offer(runtime.snapshot(), processed_seq=received)
            if epoch is not None:
                images = runtime.images.retain(stream.retained_states())
                if images != registered_images:
                    # Private worker-to-gateway metadata; never forwarded to the browser.
                    await write_packet(writer, b'I\0' + pack_registry(images))
                    registered_images = images
                render = stream.next_render()
                if render is not None:
                    await send('render', render)
                    deadline, retries = loop.time() + RENDER_ACK_TIMEOUT, 0
                elif deadline is not None and loop.time() >= deadline:
                    if retries < MAX_RENDER_RETRIES:
                        await send('render', stream.retry())
                        retries += 1
                        deadline = loop.time() + RENDER_ACK_TIMEOUT
                    else:
                        # Empty outbound payload asks the gateway to disconnect
                        # this epoch, retaining the worker under its normal TTL.
                        await write_packet(writer, epoch.encode('ascii') + b'\0')
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
        pending = [task for task in (incoming, changed) if task is not None]
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        try:
            runtime.close()
        finally:
            writer.close()
            try:
                await asyncio.wait_for(writer.wait_closed(), 1)
            except (ConnectionError, asyncio.TimeoutError):
                writer.transport.abort()
