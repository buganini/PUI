"""Original-file image descriptors shared by browser backends."""
from dataclasses import dataclass
import mimetypes
from pathlib import Path

MAX_IMAGES = 128
MAX_IMAGE_BYTES = 64 * 1024 * 1024


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
