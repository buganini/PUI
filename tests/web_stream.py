"""Downstream block-flush boundaries, history, limits and cross-language cases."""
import base64
import json
import unittest

import msgpack
import zstandard

from PUI.web.protocol import Codec, Limits, ProtocolError, StreamCodec
from web_protocol import message


def flush_raw(raw):
    compressor = zstandard.ZstdCompressor(write_content_size=False).compressobj()
    return compressor.compress(raw) + compressor.flush(zstandard.COMPRESSOBJ_FLUSH_BLOCK)


def malformed_batches():
    pack = msgpack.Packer(use_bin_type=True)
    valid = StreamCodec().encode(message())
    # Header followed by non-final raw/RLE blocks; no complete zstd frame needed.
    header = valid[:6]
    return {
        'empty': b'',
        'header only': header,
        'truncated header': valid[:4],
        'truncated block': valid[:-1],
        'extra bytes': valid + b'x',
        'restarted frame': valid + valid,
        'ended frame': Codec().encode(message()),
        'dictionary': header[:4] + b'\x01' + header[5:] + valid[6:],
        'checksum flag': header[:4] + b'\x04' + header[5:] + valid[6:],
        'excess window': header[:5] + b'\x80' + valid[6:],
        'reserved block': header + b'\x06\x00\x00',
        'last block': header + b'\x01\x00\x00',
        'excess block': header + ((128 * 1024 + 1) << 3).to_bytes(3, 'little'),
        'trailing MessagePack': flush_raw(pack.pack(message()) + b'\xc0'),
        'truncated MessagePack': flush_raw(pack.pack(message())[:-1]),
        'duplicate keys': flush_raw(b'\x82\xa1a\x01\xa1a\x02'),
        'invalid UTF-8': flush_raw(b'\xa1\xff'),
        'extension': flush_raw(pack.pack(msgpack.ExtType(1, b'x'))),
        'invalid envelope': flush_raw(pack.pack({})),
        'nonfinite': flush_raw(pack.pack(message({'value': float('nan')}))),
        'unsafe integer': flush_raw(pack.pack(message({'value': 2 ** 60}))),
        'excess decoded bytes': flush_raw(pack.pack(message({'value': b'x' * Limits().max_decoded_bytes}))),
        'excess items': flush_raw(pack.pack(message({'items': [0] * (Limits().max_items - 12)}))),
        'excess depth': flush_raw(b'\x91' * 66 + b'\xc0'),
    }


class StreamTests(unittest.TestCase):
    def test_every_batch_decodes_immediately_and_reuses_history(self):
        encoder, decoder = StreamCodec(), StreamCodec()
        # Many diverse commands prevent a trivially tiny independent frame.
        commands = [['line', i, i * .3, str(i)] for i in range(4000)]
        sizes = []
        for i in range(6):
            value = message({'commands': commands}, type='render', seq=i + 1)
            packet = encoder.encode(value)
            sizes.append(len(packet))
            self.assertEqual(decoder.decode(packet), value)
            if i:
                self.assertFalse(packet.startswith(b'\x28\xb5\x2f\xfd'))
            else:
                self.assertEqual(zstandard.get_frame_parameters(packet).window_size, 4 * 1024 * 1024)
        self.assertLess(sizes[-1], sizes[0] // 10)

    def test_flush_once_after_complete_dom_and_canvas(self):
        encoder, decoder = StreamCodec(), StreamCodec()
        raw_decoder = zstandard.ZstdDecompressor().decompressobj()
        for i in range(3):
            value = message({'roots': ['dom' * 50000], 'canvases': [list(range(10000))]}, seq=i + 1)
            packet = encoder.encode(value)
            self.assertEqual(msgpack.unpackb(raw_decoder.decompress(packet)), value)
            self.assertFalse(raw_decoder.eof)
            self.assertEqual(decoder.decode(packet), value)

    def test_connections_have_independent_histories(self):
        encoders, decoders = [StreamCodec(), StreamCodec()], [StreamCodec(), StreamCodec()]
        for i in range(5):
            for client in range(2):
                value = message({'data': str(client) * 10000}, session=str(client), seq=i + 1)
                self.assertEqual(decoders[client].decode(encoders[client].encode(value)), value)
        value = message({'data': 'reconnected'})
        self.assertEqual(StreamCodec().decode(StreamCodec().encode(value)), value)

    def test_discarded_compressed_chunk_cannot_be_retried(self):
        sender = StreamCodec()
        value = message({'data': 'history' * 10000})
        sender.encode(value)
        with self.assertRaises(ProtocolError):
            StreamCodec().decode(sender.encode(value))

    def test_shared_malformed_batches_close_stream(self):
        valid = StreamCodec().encode(message())
        for name, packet in malformed_batches().items():
            with self.subTest(name=name):
                decoder = StreamCodec()
                with self.assertRaises(ProtocolError):
                    decoder.decode(packet)
                with self.assertRaisesRegex(ProtocolError, 'closed'):
                    decoder.decode(valid)

    def test_limits_apply_per_batch_not_whole_connection(self):
        limits = Limits(max_decoded_bytes=1024)
        sender, receiver = StreamCodec(), StreamCodec(limits=limits)
        for i in range(30):
            value = message({'value': 'x' * 900}, seq=i + 1)
            self.assertEqual(receiver.decode(sender.encode(value)), value)
        with self.assertRaisesRegex(ProtocolError, 'Decoded batch'):
            receiver.decode(sender.encode(message({'value': 'x' * 1024})))

    def test_wire_and_decoded_limits(self):
        value = message({'value': 'x' * 1000})
        packet = StreamCodec().encode(value)
        with self.assertRaisesRegex(ProtocolError, 'Compressed batch'):
            StreamCodec(limits=Limits(max_wire_bytes=8)).decode(packet)
        with self.assertRaisesRegex(ProtocolError, 'Decoded batch'):
            StreamCodec(limits=Limits(max_decoded_bytes=100)).decode(packet)
        with self.assertRaisesRegex(ProtocolError, 'window'):
            StreamCodec(limits=Limits(max_window_bytes=1024)).decode(packet)
        with self.assertRaises(ProtocolError):
            StreamCodec(limits=Limits(max_wire_bytes=8)).encode(value)

    def test_explicit_close_releases_state(self):
        codec = StreamCodec()
        codec.decode(codec.encode(message()))
        codec.close()
        self.assertIsNone(codec._encoder)
        self.assertIsNone(codec._decoder)
        with self.assertRaisesRegex(ProtocolError, 'closed'):
            codec.encode(message())


if __name__ == '__main__':
    import sys
    if '--fixtures' in sys.argv:
        print(json.dumps({name: base64.b64encode(packet).decode('ascii')
                          for name, packet in malformed_batches().items()}))
    else:
        unittest.main()
