"""Binary protocol boundary tests; requires the approved Web codecs."""
import unittest

import msgpack
import zstandard

from PUI.web.protocol import Codec, Limits, ProtocolError, SAFE_INTEGER


def message(body=None, **changes):
    value = {'v': 1, 'type': 'event', 'session': 's1', 'seq': 1,
             'body': {} if body is None else body}
    value.update(changes)
    return value


class CodecTests(unittest.TestCase):
    def setUp(self):
        self.codec = Codec()

    def test_round_trip_preserves_data_types(self):
        value = message({'values': [None, True, False, 1, 1.25, '中文', b'\x00\xff',
                                   SAFE_INTEGER, -SAFE_INTEGER],
                         'object_id': '18446744073709551615'})
        decoded = self.codec.decode(self.codec.encode(value))
        self.assertEqual(decoded, value)
        self.assertIs(type(decoded['body']['values'][1]), bool)
        self.assertIs(type(decoded['body']['values'][3]), int)
        self.assertIs(type(decoded['body']['values'][4]), float)

    def test_hello_requires_null_epoch_and_other_messages_require_epoch(self):
        hello = message(type='hello', session=None)
        self.assertEqual(self.codec.decode(self.codec.encode(hello)), hello)
        for changes in ({'session': None}, {'type': 'hello'}, {'session': ''}):
            with self.subTest(changes=changes), self.assertRaises(ProtocolError):
                self.codec.encode(message(**changes))

    def test_reject_invalid_values_and_envelopes(self):
        for value in (SAFE_INTEGER + 1, float('nan'), float('inf'), object(),
                      (1, 2), {1: 'value'}, '\ud800'):
            with self.subTest(value=type(value).__name__), self.assertRaises(ProtocolError):
                self.codec.encode(message({'value': value}))
        for changes in ({'seq': True}, {'seq': 0}, {'v': 2}, {'type': 'unknown'},
                        {'extra': 1}, {'body': []}):
            with self.subTest(changes=changes), self.assertRaises(ProtocolError):
                self.codec.encode(message(**changes))

    def test_reject_concatenation_trailing_data_and_truncation(self):
        frame = self.codec.encode(message())
        for bad in (frame + frame, frame + b'extra', frame[:-1], b'{}', b'', frame[:4]):
            with self.subTest(length=len(bad)), self.assertRaises(ProtocolError):
                self.codec.decode(bad)

    def test_reject_duplicate_keys_invalid_utf8_and_extensions(self):
        payloads = [b'\x82\xa1a\x01\xa1a\x02', b'\xa1\xff',
                    msgpack.packb(msgpack.ExtType(1, b'opaque')),
                    msgpack.packb(message()) + msgpack.packb(message())]
        for payload in payloads:
            with self.subTest(payload=payload), self.assertRaises(ProtocolError):
                self.codec.decode(zstandard.ZstdCompressor().compress(payload))

    def test_bounds_and_unknown_content_size(self):
        small = Codec(limits=Limits(max_decoded_bytes=128, max_wire_bytes=128,
                                   max_window_bytes=128, max_items=20, max_depth=4))
        for value in (message({'data': 'x' * 129}), message({'items': list(range(30))}),
                      message({'nested': [[[[[0]]]]]})):
            with self.subTest(value=value), self.assertRaises(ProtocolError):
                small.encode(value)
        oversized = zstandard.ZstdCompressor().compress(b'x' * 129)
        with self.assertRaises(ProtocolError) as caught:
            small.decode(oversized)
        self.assertEqual(caught.exception.code, 'LIMIT_EXCEEDED')
        unknown_size = zstandard.ZstdCompressor(write_content_size=False).compress(
            msgpack.packb(message()))
        with self.assertRaises(ProtocolError):
            self.codec.decode(unknown_size)

    def test_decoder_also_rejects_non_wire_values(self):
        for value in (float('nan'), 2 ** 60, msgpack.Timestamp(1, 0)):
            raw = msgpack.packb(message({'value': value}), use_bin_type=True)
            with self.subTest(value=value), self.assertRaises(ProtocolError):
                self.codec.decode(zstandard.ZstdCompressor().compress(raw))


if __name__ == '__main__':
    unittest.main()
