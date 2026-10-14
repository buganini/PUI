"""Original-file HTTP resources; browser-side image transformation descriptors."""
from dataclasses import dataclass
import mimetypes
from pathlib import Path
import secrets

MAX_IMAGES = 128
MAX_IMAGE_BYTES = 64 * 1024 * 1024


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


def image_file(path):
    path = Path(path).resolve(strict=True)
    stat = path.stat()
    mime = mimetypes.guess_type(str(path))[0]
    if not path.is_file() or not mime or not mime.startswith('image/'):
        raise ValueError('Web images require a file with an image MIME type')
    if stat.st_size > MAX_IMAGE_BYTES:
        raise ValueError('Web image exceeds 64 MiB')
    return path, stat, mime


@dataclass(frozen=True)
class ImageResource:
    path: str
    operations: tuple = ()

    @staticmethod
    def load(path):
        path, _, _ = image_file(path)
        return ImageResource(str(path))

    def _with(self, operation):
        if len(self.operations) >= 32:
            raise ValueError('Web image supports at most 32 transformations')
        return ImageResource(self.path, self.operations + (operation,))

    def crop(self, x, y, width, height):
        if any(type(v) is not int or abs(v) > 16384 for v in (x, y, width, height)) or min(width, height) < 1:
            raise ValueError('Web crop requires bounded integer coordinates and positive dimensions')
        return self._with(('crop', x, y, width, height))

    def scale(self, width, height, keepAspectRatio=True, quality=0):
        if any(type(v) is not int or not 1 <= v <= 16384 for v in (width, height)):
            raise ValueError('Web scale requires positive integer dimensions up to 16384')
        return self._with(('scale', width, height, bool(keepAspectRatio), quality != 0))


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
