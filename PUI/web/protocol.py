"""Bounded binary framing shared by Web workers and gateway handshake checks."""
from dataclasses import dataclass
import math


VERSION = 1
SUBPROTOCOL = 'pui.v1.msgpack.zstd'
SAFE_INTEGER = 2 ** 53 - 1
MESSAGE_TYPES = frozenset((
    'hello', 'ready', 'render', 'event', 'binding_write', 'result', 'measure',
    'ack', 'canvas_ack', 'resync', 'resource', 'release', 'error', 'close',
))


class ProtocolError(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class Limits:
    max_wire_bytes: int = 8 * 1024 * 1024
    max_decoded_bytes: int = 16 * 1024 * 1024
    max_window_bytes: int = 16 * 1024 * 1024
    max_items: int = 1000000
    max_depth: int = 64

    def __post_init__(self):
        for value in self.__dict__.values():
            if type(value) is not int or value <= 0:
                raise ValueError('Protocol limits must be positive integers')


def validate_data(value, *, limits=None):
    """Check the wire value subset without converting opaque Python objects."""
    limits = limits or Limits()
    remaining = limits.max_items
    byte_budget = limits.max_decoded_bytes

    def visit(item, depth):
        nonlocal remaining, byte_budget
        remaining -= 1
        if remaining < 0:
            raise ProtocolError('LIMIT_EXCEEDED',
                'Value count exceeds limit (%s > %s)' % (limits.max_items - remaining, limits.max_items))
        if depth > limits.max_depth:
            raise ProtocolError('LIMIT_EXCEEDED',
                'Nesting depth exceeds limit (%s > %s)' % (depth, limits.max_depth))
        kind = type(item)
        if item is None or kind is bool:
            return
        if kind is int:
            if abs(item) > SAFE_INTEGER:
                raise ProtocolError('INVALID_VALUE', 'Integer exceeds exact JavaScript range')
        elif kind is float:
            if not math.isfinite(item):
                raise ProtocolError('INVALID_VALUE', 'Non-finite number')
        elif kind in (str, bytes):
            try:
                byte_budget -= len(item.encode('utf-8') if kind is str else item)
            except UnicodeError as error:
                raise ProtocolError('INVALID_VALUE', 'Invalid Unicode') from error
            if byte_budget < 0:
                raise ProtocolError('LIMIT_EXCEEDED', 'Value bytes exceed limit')
        elif kind is list:
            for child in item:
                visit(child, depth + 1)
        elif kind is dict:
            for key, child in item.items():
                if type(key) is not str or key == '__proto__':
                    raise ProtocolError('INVALID_VALUE', 'Invalid map key')
                visit(key, depth + 1)
                visit(child, depth + 1)
        else:
            raise ProtocolError('INVALID_VALUE', 'Unsupported wire value type: ' + kind.__name__)

    visit(value, 0)


def validate_envelope(message, *, limits=None):
    validate_data(message, limits=limits)
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

    def __init__(self, *, limits=None):
        # Dependencies are loaded only when Web transport is used.
        import msgpack
        import zstandard
        self._msgpack = msgpack
        self._zstd = zstandard
        self.limits = limits or Limits()

    def encode(self, message):
        validate_envelope(message, limits=self.limits)
        data = self._msgpack.packb(message, use_bin_type=True, strict_types=True)
        if len(data) > self.limits.max_decoded_bytes:
            raise ProtocolError('LIMIT_EXCEEDED', 'MessagePack payload exceeds limit')
        frame = self._zstd.ZstdCompressor(
            level=3, write_content_size=True, write_checksum=True,
        ).compress(data)
        if len(frame) > self.limits.max_wire_bytes:
            raise ProtocolError('LIMIT_EXCEEDED', 'Compressed frame exceeds limit')
        return frame

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
        validate_envelope(message, limits=self.limits)
        return message
