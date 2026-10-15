"""Identical malformed binary fixtures for the Python and browser decoders."""
import base64
import json

import msgpack
import zstandard

from PUI.web.protocol import Codec, Limits


def malformed_frames():
    pack = msgpack.Packer(use_bin_type=True)
    compress = zstandard.ZstdCompressor(write_checksum=True).compress
    def body(raw):
        return (pack.pack_map_header(5) + b''.join(pack.pack(k) + pack.pack(v) for k, v in
            (('v', 1), ('type', 'event'), ('session', 'test'), ('seq', 1))) + pack.pack('body') + raw)
    def value(raw):
        return body(pack.pack_map_header(1) + pack.pack('value') + raw)
    message = {'v': 1, 'type': 'event', 'session': 'test', 'seq': 1, 'body': {}}
    frame = Codec().encode(message)
    payloads = {
        'nested duplicate keys': body(b'\x82\xa1a\x01\xa1a\x02'),
        'nested invalid UTF-8': value(b'\xa1\xff'),
        'extension': value(pack.pack(msgpack.ExtType(1, b'data'))),
        'timestamp': value(pack.pack(msgpack.Timestamp(1, 0))),
        'nonfinite': value(pack.pack(float('nan'))),
        'unsafe integer': value(pack.pack(2 ** 60)),
        'prototype key': body(pack.pack({'__proto__': {}})),
        'excess nesting': value(b'\x91' * (Limits().max_depth + 1) + b'\xc0'),
        'excess items': value(pack.pack([0] * (Limits().max_items + 1))),
        # The container fits; map keys/envelope values push the total over.
        'excess aggregate items': value(pack.pack([0] * (Limits().max_items - 12))),
        'extra MessagePack': pack.pack(message) + b'\xc0',
        'binary map key': body(pack.pack({b'key': 1})),
    }
    result = {name: compress(payload) for name, payload in payloads.items()}
    result.update({
        'concatenated frames': frame + frame,
        'trailing bytes': frame + b'x',
        'truncated frame': frame[:-1],
        'checksum mismatch': frame[:-1] + bytes([frame[-1] ^ 1]),
        'unknown content size': zstandard.ZstdCompressor(write_content_size=False).compress(pack.pack(message)),
        'excess content size': compress(b'x' * (Limits().max_decoded_bytes + 1)),
        'excess window': b'\x28\xb5\x2f\xfd\x40\x80\x00\x00\x01\x00\x00',
        'dictionary reference': b'\x28\xb5\x2f\xfd\x21\x01\x00\x01\x00\x00',
    })
    return result


if __name__ == '__main__':
    print(json.dumps({name: base64.b64encode(frame).decode('ascii')
                      for name, frame in malformed_frames().items()}))
