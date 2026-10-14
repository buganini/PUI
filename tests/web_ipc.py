"""An unread peer cannot leave a worker output write waiting forever."""
import asyncio
import socket
import unittest
from unittest.mock import patch

from PUI.web.ipc import MAX_PACKET, read_packet, write_packet


class IPCTests(unittest.IsolatedAsyncioTestCase):
    async def test_unread_peer_times_out_with_one_bounded_packet(self):
        sender, receiver = socket.socketpair()
        sender.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4096)
        sender.setblocking(False)
        _, writer = await asyncio.open_connection(sock=sender)
        try:
            with patch('PUI.web.ipc.WRITE_TIMEOUT', .05), self.assertRaises(asyncio.TimeoutError):
                await write_packet(writer, b'x' * (MAX_PACKET - 1))
            self.assertLessEqual(writer.transport.get_write_buffer_size(), MAX_PACKET + 4)
        finally:
            receiver.close()
            writer.transport.abort()
            try:
                await writer.wait_closed()
            except ConnectionError:
                pass

    async def test_draining_peer_receives_exact_packet_and_oversize_is_rejected(self):
        sender, receiver = socket.socketpair()
        sender.setblocking(False)
        receiver.setblocking(False)
        _, writer = await asyncio.open_connection(sock=sender)
        reader, peer = await asyncio.open_connection(sock=receiver)
        try:
            payload = b'payload' * 100000
            _, received = await asyncio.gather(write_packet(writer, payload), read_packet(reader))
            self.assertEqual(received, payload)
            with self.assertRaises(ValueError):
                await write_packet(writer, b'x' * (MAX_PACKET + 1))
        finally:
            writer.close()
            peer.close()
            await asyncio.gather(writer.wait_closed(), peer.wait_closed())
