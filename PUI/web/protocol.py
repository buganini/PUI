"""Bounded binary framing shared by Web workers and gateway handshake checks."""
from dataclasses import dataclass
from .._browser.schema import ProtocolError, RenderLimits, SAFE_INTEGER, validate_data


VERSION = 1
SUBPROTOCOL = 'pui.v1.msgpack.zstd-stream'
MESSAGE_TYPES = frozenset((
    'hello', 'ready', 'render', 'event', 'binding_write', 'result', 'measure',
    'ack', 'canvas_ack', 'resync', 'resource', 'release', 'error', 'close',
))


@dataclass(frozen=True)
class Limits:
    max_wire_bytes: int = 8 * 1024 * 1024
    max_decoded_bytes: int = RenderLimits.max_decoded_bytes
    max_window_bytes: int = 16 * 1024 * 1024
    max_items: int = RenderLimits.max_items
    max_depth: int = RenderLimits.max_depth

    def __post_init__(self):
        for value in self.__dict__.values():
            if type(value) is not int or value <= 0:
                raise ValueError('Protocol limits must be positive integers')


def validate_envelope(message, *, limits=None, check_values=True, check_numbers=True):
    if check_values:
        validate_data(message, limits=limits, check_numbers=check_numbers)
    if type(message) is not dict or set(message) != {'v', 'type', 'session', 'seq', 'body'}:
        raise ProtocolError('BAD_FRAME', 'Invalid envelope fields')
    if type(message['v']) is not int or message['v'] != VERSION:
        raise ProtocolError('VERSION_MISMATCH', 'Unsupported protocol version')
    if type(message['type']) is not str or message['type'] not in MESSAGE_TYPES:
        raise ProtocolError('BAD_FRAME', 'Unknown message type')
    if type(message['seq']) is not int or not 0 < message['seq'] <= SAFE_INTEGER:
        raise ProtocolError('BAD_SEQUENCE', 'Invalid message sequence')
    session = message['session']
    if message['type'] == 'hello':
        valid_session = session is None
    else:
        valid_session = type(session) is str and bool(session)
    if not valid_session:
        raise ProtocolError('BAD_SESSION', 'Invalid session epoch')
    if type(message['body']) is not dict:
        raise ProtocolError('BAD_FRAME', 'Message body must be a map')


def _pairs(items):
    result = {}
    for key, value in items:
        if type(key) is not str or key in result:
            raise ProtocolError('BAD_FRAME', 'Duplicate or non-string map key')
        result[key] = value
    return result


def _extension(code, data):
    raise ProtocolError('BAD_FRAME', 'MessagePack extensions are unsupported')


class Codec:
    """One content-sized Zstandard frame containing one MessagePack envelope."""

    render_output = False

    def __init__(self, *, limits=None):
        # Dependencies are loaded only when Web transport is used.
        import msgpack
        import zstandard
        self._msgpack = msgpack
        self._zstd = zstandard
        self.limits = limits or Limits()

    def encode(self, message):
        data = self.pack(message)
        frame = self._zstd.ZstdCompressor(
            level=3, write_content_size=True, write_checksum=True,
        ).compress(data)
        if len(frame) > self.limits.max_wire_bytes:
            raise ProtocolError('LIMIT_EXCEEDED', 'Compressed frame exceeds limit')
        return frame

    def pack(self, message):
        # Our render records go directly to MessagePack. The receiver enforces
        # item/depth budgets; do not walk a complete display list before packing.
        render = self.render_output and type(message) is dict and message.get('type') == 'render'
        validate_envelope(message, limits=self.limits, check_values=not render)
        # Native tuple encoding produces MessagePack arrays without an intermediate list.
        data = self._msgpack.packb(message, use_bin_type=True)
        if len(data) > self.limits.max_decoded_bytes:
            raise ProtocolError('LIMIT_EXCEEDED', 'MessagePack payload exceeds limit')
        return data

    def decode(self, frame):
        if type(frame) is not bytes or not frame.startswith(b'\x28\xb5\x2f\xfd'):
            raise ProtocolError('BAD_FRAME', 'Expected a standard Zstandard binary frame')
        if len(frame) > self.limits.max_wire_bytes:
            raise ProtocolError('LIMIT_EXCEEDED', 'Compressed frame exceeds limit')
        try:
            parameters = self._zstd.get_frame_parameters(frame)
            if parameters.dict_id or parameters.content_size in (
                self._zstd.CONTENTSIZE_UNKNOWN, self._zstd.CONTENTSIZE_ERROR,
            ):
                raise ProtocolError('BAD_FRAME', 'Frame requires a size and no dictionary')
            if (parameters.content_size > self.limits.max_decoded_bytes or
                    parameters.window_size > self.limits.max_window_bytes):
                raise ProtocolError('LIMIT_EXCEEDED', 'Decoded size or window exceeds limit')
            data = self._zstd.ZstdDecompressor().decompress(
                frame, max_output_size=self.limits.max_decoded_bytes, allow_extra_data=False,
            )
        except ProtocolError:
            raise
        except (ValueError, TypeError, OverflowError, self._zstd.ZstdError) as error:
            raise ProtocolError('BAD_FRAME', 'Invalid compressed MessagePack frame') from error
        return self.unpack(data)

    def unpack(self, data):
        if len(data) > self.limits.max_decoded_bytes:
            raise ProtocolError('LIMIT_EXCEEDED', 'MessagePack payload exceeds limit')
        try:
            message = self._msgpack.unpackb(
                data, raw=False, strict_map_key=True, unicode_errors='strict',
                object_pairs_hook=_pairs, ext_hook=_extension,
                max_str_len=self.limits.max_decoded_bytes,
                max_bin_len=self.limits.max_decoded_bytes,
                max_array_len=self.limits.max_items,
                max_map_len=self.limits.max_items, max_ext_len=0,
            )
        except ProtocolError:
            raise
        except (ValueError, TypeError, OverflowError, self._zstd.ZstdError) as error:
            raise ProtocolError('BAD_FRAME', 'Invalid compressed MessagePack frame') from error
        render = self.render_output and type(message) is dict and message.get('type') == 'render'
        validate_envelope(message, limits=self.limits, check_numbers=not render)
        return message


class StreamCodec(Codec):
    """Connection-local downstream stream; one complete envelope per block flush.

    Reconnects need a new instance, even when the application worker survives.
    Upstream events and private control packets continue to use ``Codec``.
    """

    render_output = True

    def __init__(self, *, limits=None):
        super().__init__(limits=limits)
        self._encoder = self._decoder = None
        self._window = None
        self._closed = False

    def close(self):
        self._closed = True
        self._encoder = self._decoder = None

    def _check_open(self):
        if self._closed:
            raise ProtocolError('BAD_FRAME', 'Compression stream is closed')

    def encode(self, message):
        self._check_open()
        try:
            data = self.pack(message)
            if self._encoder is None:
                parameters = self._zstd.ZstdCompressionParameters.from_level(
                    3, window_log=22, write_content_size=False, write_checksum=False,
                )
                self._encoder = self._zstd.ZstdCompressor(
                    compression_params=parameters,
                ).compressobj()
            # render already contains the complete DOM/Canvas batch. Flush once
            # here, preserving history for every subsequent server message.
            packet = self._encoder.compress(data)
            packet += self._encoder.flush(self._zstd.COMPRESSOBJ_FLUSH_BLOCK)
            if len(packet) > self.limits.max_wire_bytes:
                raise ProtocolError('LIMIT_EXCEEDED', 'Compressed batch exceeds limit')
            return packet
        except Exception:
            self.close()
            raise

    def decode(self, packet):
        self._check_open()
        try:
            blocks = self._blocks(packet)
            if self._decoder is None:
                self._decoder = self._zstd.ZstdDecompressor().decompressobj()
                self._decoder.decompress(packet[:6])
            chunks, size = [], 0
            for block in blocks:
                # The format caps each block's decoded output at 128 KiB.
                chunk = self._decoder.decompress(block)
                size += len(chunk)
                if size > self.limits.max_decoded_bytes:
                    raise ProtocolError('LIMIT_EXCEEDED', 'Decoded batch exceeds limit')
                chunks.append(chunk)
            return self.unpack(b''.join(chunks))
        except Exception as error:
            self.close()
            if isinstance(error, ProtocolError):
                raise
            raise ProtocolError('BAD_FRAME', 'Invalid compressed MessagePack stream') from error

    def _blocks(self, packet):
        if type(packet) is not bytes or not packet:
            raise ProtocolError('BAD_FRAME', 'Expected a nonempty binary batch')
        if len(packet) > self.limits.max_wire_bytes:
            raise ProtocolError('LIMIT_EXCEEDED', 'Compressed batch exceeds limit')
        offset = 0
        if self._window is None:
            # An open frame has a window, no content size, dictionary or checksum.
            if len(packet) < 6 or packet[:5] != b'\x28\xb5\x2f\xfd\x00':
                raise ProtocolError('BAD_FRAME', 'Expected an open Zstandard stream')
            descriptor = packet[5]
            base = 2 ** (10 + (descriptor >> 3))
            self._window = base + base // 8 * (descriptor & 7)
            if self._window > self.limits.max_window_bytes:
                raise ProtocolError('LIMIT_EXCEEDED', 'Stream window exceeds limit')
            offset = 6
        blocks = []
        while offset < len(packet):
            start = offset
            if offset + 3 > len(packet):
                raise ProtocolError('BAD_FRAME', 'Truncated stream block header')
            header = int.from_bytes(packet[offset:offset + 3], 'little')
            kind, size = (header >> 1) & 3, header >> 3
            if header & 1 or kind == 3:
                raise ProtocolError('BAD_FRAME', 'Ended stream or reserved block type')
            if size > min(self._window, 128 * 1024):
                raise ProtocolError('LIMIT_EXCEEDED', 'Stream block exceeds limit')
            offset += 3 + (1 if kind == 1 else size)
            if offset > len(packet):
                raise ProtocolError('BAD_FRAME', 'Truncated stream block')
            blocks.append(packet[start:offset])
        if not blocks:
            raise ProtocolError('BAD_FRAME', 'Empty stream batch')
        return blocks
