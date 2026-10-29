"""Worker IPC on a dedicated loop; application callbacks remain serial."""
import asyncio
from concurrent.futures import Future
import queue
import threading

from .ipc import read_packet, write_packet
from .messages import validate_client_body
from .protocol import Codec, ProtocolError


class Transport:
    def __init__(self, sock, application_loop):
        self.application_loop = application_loop
        self.available = asyncio.Event()
        self.packets = queue.Queue(maxsize=256)
        self.queued_bytes = 0
        self.budget_lock = threading.Lock()
        self.ready = Future()
        self.failure = None
        self.thread = threading.Thread(target=self._run, args=(sock,), name='pui-web-transport')
        self.thread.start()
        self.ready.result()

    def _run(self, sock):
        try:
            asyncio.run(self._serve(sock))
        except BaseException as error:
            self.failure = error
            if not self.ready.done():
                self.ready.set_exception(error)
        finally:
            self.application_loop.call_soon_threadsafe(self.available.set)

    async def _serve(self, sock):
        self.loop = asyncio.get_running_loop()
        sock.setblocking(False)
        reader, self.writer = await asyncio.open_connection(sock=sock)
        self.epoch = None
        self.sequence = 0
        self.pending = None
        self.stopped = asyncio.Event()
        self.ready.set_result(None)
        codec = Codec()
        try:
            while True:
                packet = await read_packet(reader)
                operation, payload = packet[:1], packet[1:]
                if operation in (b'A', b'D'):
                    self._cancel_dialog('Browser disconnected or connection replaced')
                    self.epoch = codec.decode(payload)['body']['epoch'] if operation == b'A' else None
                    self.sequence = 1 if operation == b'A' else 0
                elif operation == b'M' and self.epoch is not None:
                    message = codec.decode(payload)
                    if message['session'] != self.epoch or message['seq'] != self.sequence + 1:
                        raise ProtocolError('BAD_SEQUENCE', 'Invalid session or sequence')
                    self.sequence = message['seq']
                    if message['type'] == 'dialog_result':
                        body = message['body']
                        validate_client_body('dialog_result', body)
                        if self.pending is None or body['request_id'] != self.pending[0]:
                            raise ProtocolError('BAD_FRAME', 'Unexpected dialog reply')
                        _, kind, future = self.pending
                        value = body['value']
                        if kind == 'savefile':
                            valid = value is None or type(value) is dict
                        elif kind == 'confirm':
                            valid = type(value) is bool
                        elif kind == 'prompt':
                            valid = value is None or type(value) is str
                        else:
                            valid = value is None
                        if not valid:
                            raise ProtocolError('INVALID_VALUE', 'Invalid dialog result')
                        self.pending = None
                        future.set_result(value)
                        continue
                # UI events are queued, never executed by the transport thread.
                with self.budget_lock:
                    if self.queued_bytes + len(packet) > 32 * 1024 * 1024:
                        raise ProtocolError('LIMIT_EXCEEDED', 'Worker input queue is full')
                    self.packets.put_nowait(packet)
                    self.queued_bytes += len(packet)
                self.application_loop.call_soon_threadsafe(self.available.set)
        except Exception as error:
            self.failure = error
        finally:
            self._cancel_dialog('Worker transport closed')
            self.writer.close()
            try:
                await self.writer.wait_closed()
            except ConnectionError:
                pass
            self.application_loop.call_soon_threadsafe(self.available.set)
            # Keep accepting scheduled sends long enough to report closure rather
            # than abandoning their futures while the application unwinds.
            await self.stopped.wait()

    def _cancel_dialog(self, reason):
        if self.pending is not None:
            future = self.pending[2]
            self.pending = None
            future.set_exception(ConnectionError(reason))

    async def receive(self):
        while True:
            try:
                with self.budget_lock:
                    packet = self.packets.get_nowait()
                    self.queued_bytes -= len(packet)
                return packet
            except queue.Empty:
                if self.failure is not None:
                    raise self.failure
                self.available.clear()
                await self.available.wait()

    async def send(self, packet):
        await asyncio.wrap_future(asyncio.run_coroutine_threadsafe(write_packet(self.writer, packet), self.loop))

    def dialog(self, packet, epoch, request_id, kind):
        """Block only the application thread until this connection answers."""
        async def exchange():
            if self.epoch != epoch or self.writer.is_closing():
                raise ConnectionError('Browser is not connected')
            if self.pending is not None:
                raise RuntimeError('A dialog is already pending')
            future = self.loop.create_future()
            self.pending = (request_id, kind, future)
            try:
                await write_packet(self.writer, packet)
                return await future
            finally:
                if self.pending is not None and self.pending[2] is future:
                    self.pending = None
        return asyncio.run_coroutine_threadsafe(exchange(), self.loop).result()

    async def close(self):
        if self.thread.is_alive():
            def stop():
                self.stopped.set()
                self.writer.close()
            self.loop.call_soon_threadsafe(stop)
            await asyncio.to_thread(self.thread.join)
