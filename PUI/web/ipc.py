"""Bounded private stream framing; application payloads retain the Web codec."""
import struct

MAX_PACKET = 8 * 1024 * 1024 + 4096


async def read_packet(reader):
    length = struct.unpack('!I', await reader.readexactly(4))[0]
    if not 0 < length <= MAX_PACKET:
        raise ValueError('IPC packet size exceeds limit')
    return await reader.readexactly(length)


def queue_packet(writer, payload):
    """Append one packet atomically; the caller must subsequently await drain."""
    if not 0 < len(payload) <= MAX_PACKET:
        raise ValueError('IPC packet size exceeds limit')
    writer.write(struct.pack('!I', len(payload)) + payload)


async def write_packet(writer, payload):
    queue_packet(writer, payload)
    await writer.drain()
