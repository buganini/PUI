"""Original-file HTTP resources; browser-side image transformation descriptors."""
from pathlib import Path
import secrets

from .._browser.images import MAX_IMAGES, MAX_IMAGE_BYTES, ImageResource, image_file


def pack_registry(resources):
    import msgpack
    return msgpack.packb(resources, use_bin_type=True)


def unpack_registry(payload):
    import msgpack
    if len(payload) > 1024 * 1024:
        raise ValueError('Image registry exceeds limit')
    records = msgpack.unpackb(payload, raw=False, max_array_len=MAX_IMAGES,
                             max_map_len=4, max_str_len=16384)
    if type(records) is not list:
        raise ValueError('Invalid image registry')
    result = {}
    for record in records:
        if (type(record) is not dict or set(record) != {'id', 'path', 'mime', 'mtime'} or
                any(type(v) is not str for v in record.values()) or
                len(record['id']) != 32 or not all(c.isascii() and (c.isalnum() or c in '-_') for c in record['id']) or
                not Path(record['path']).is_absolute() or not record['mime'].startswith('image/') or
                not record['mtime'].lstrip('-').isdigit() or record['id'] in result):
            raise ValueError('Invalid image registration')
        result[record['id']] = record
    return result


class ImageRegistry:
    def __init__(self, base='/pui/images'):
        self.base = base.rstrip('/')
        self.files = {}

    def register(self, path):
        path, stat, mime = image_file(path)
        path = str(path)
        entry = self.files.get(path)
        if entry is None:
            if len(self.files) >= MAX_IMAGES:
                raise ValueError('Web session exceeds 128 registered images')
            entry = self.files[path] = dict(id=secrets.token_urlsafe(24), path=path, mime=mime)
        entry['mtime'] = str(stat.st_mtime_ns)
        return self.base + '/' + entry['id'] + '?mtime=' + entry['mtime']

    def retain(self, states):
        used = set()
        def visit(node):
            if node['type'] == 'Image':
                used.add(node['props']['src'].split('?')[0])
            for child in node['children']:
                visit(child)
        for state in states:
            for root in state['roots']:
                visit(root)
            for frame in state['canvases']:
                for command in frame['commands']:
                    if command['op'] == 'image':
                        used.add(command['resource'].split('?')[0])
        self.files = {path: e for path, e in self.files.items() if self.base + '/' + e['id'] in used}
        return [dict(e) for e in self.files.values()]

    def close(self):
        self.files.clear()
