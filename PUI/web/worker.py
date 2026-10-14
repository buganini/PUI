"""Runs after the clean standard-library fork supervisor forks a session."""
import asyncio
import importlib
import os
import signal
import traceback

from .ipc import read_packet, write_packet
from .messages import validate_client_body
from .protocol import Codec, Limits, ProtocolError
from .render import RenderStream
from .runtime import Runtime

CAPABILITIES = ['render.snapshot', 'render.patch', 'binding.object_id']


def run(sock, factory, build):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    os.environ['PUI_BACKEND'] = 'web'
    asyncio.run(_run(sock, factory, build))


async def _run(sock, factory, build):
    sock.setblocking(False)
    reader, writer = await asyncio.open_connection(sock=sock)
    runtime = Runtime(asyncio.get_running_loop())
    codec = Codec()
    incoming = changed = None
    epoch = None
    outgoing = received = 0
    stream = RenderStream()

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
            done, _ = await asyncio.wait((incoming, changed), return_when=asyncio.FIRST_COMPLETED)
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
                    if context['hello']['client_build'] != build:
                        raise ProtocolError('VERSION_MISMATCH', 'Reload the client page')
                    if not set(CAPABILITIES) <= set(context['hello']['capabilities']):
                        raise ProtocolError('UNSUPPORTED_CAPABILITY', 'Missing required capabilities')
                    await send('ready', {'server_build': build, 'capabilities': CAPABILITIES,
                        'limits': dict(Limits().__dict__, max_pending_actions=64),
                        'resume_id': context['resume_id'], 'resumed': context['resumed'],
                        'session_ttl': context['session_ttl']})
                    refresh = True
                elif operation == b'D':
                    epoch = None
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
                        stream.acknowledge(**body)
                    elif kind == 'resync':
                        validate_client_body(kind, body)
                        stream.resync(**body)
                        refresh = True
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
                render = stream.next_render()
                if render is not None:
                    await send('render', render)
        if epoch is not None:
            await send('close', {'reason': 'Application quit'})
    except (asyncio.IncompleteReadError, ConnectionError):
        pass
    except Exception as error:
        traceback.print_exc()
        if epoch is not None:
            try:
                await send('error', {'code': getattr(error, 'code', 'APP_ERROR'),
                    'reply_to': None, 'fatal': True, 'message': 'Session failed; see server log'})
            except Exception:
                pass
    finally:
        for task in (incoming, changed):
            if task is not None:
                task.cancel()
        runtime.close()
        writer.close()
        await writer.wait_closed()
