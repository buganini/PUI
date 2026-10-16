"""Versioned original-file resources from the worker's filesystem."""
from .._browser.images import ImageResource, image_file, MAX_IMAGES, MAX_IMAGE_BYTES


class ImageRegistry:
    def __init__(self):
        self.files = {}
        self.counter = 0

    def register(self, path):
        path, stat, mime = image_file(path)
        version = (str(path), stat.st_mtime_ns, stat.st_size)
        if version not in self.files:
            if len(self.files) >= MAX_IMAGES:
                raise ValueError('Pyodide application exceeds 128 image revisions')
            # Freeze bytes once per revision so an older retained frame remains valid.
            data = path.read_bytes()
            if len(data) > MAX_IMAGE_BYTES:
                raise ValueError('Image exceeds 64 MiB')
            self.counter += 1
            self.files[version] = {'ref': 'image:%s' % self.counter, 'mime': mime, 'data': data}
        return self.files[version]['ref']

    def retain(self, states):
        used = set()

        def visit(node):
            if node['type'] == 'Image':
                used.add(node['props']['src'])
            for child in node['children']:
                visit(child)

        for state in states:
            for root in state['roots']:
                visit(root)
            for frame in state['canvases']:
                for command in frame['commands']:
                    if command[0] == 'image':
                        used.add(command[1])
        self.files = {key: entry for key, entry in self.files.items() if entry['ref'] in used}
        return list(self.files.values())

    def close(self):
        self.files.clear()
