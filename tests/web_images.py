"""HTTP image cache validators, ownership, version changes and worker registration."""
import asyncio
import os
from pathlib import Path
import tempfile
import unittest
from aiohttp import ClientSession, CookieJar, WSMsgType
from aiohttp.test_utils import TestServer
from PUI.web.server import Gateway, Worker
from PUI.web.images import ImageRegistry, ImageResource, pack_registry, unpack_registry
from PUI.web.protocol import Codec, StreamCodec, SUBPROTOCOL


class ImageTests(unittest.IsolatedAsyncioTestCase):
    async def test_http_cache_versions_and_ownership(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'image.png'
            original = Path(__file__).with_name('web-image.png').read_bytes()
            path.write_bytes(original)
            registry = ImageRegistry('/pui/pui/images')
            url = registry.register(path)
            gateway = Gateway('unused:App', mount_path='/pui')
            async with TestServer(gateway.application()) as server:
                async with ClientSession(cookie_jar=CookieJar(unsafe=True)) as client:
                    async with client.get(server.make_url('/pui/')) as response:
                        owner = response.cookies['pui_owner'].value.split('.')[0]
                    worker = Worker(None, None, owner=owner, images=unpack_registry(pack_registry(list(registry.files.values()))))
                    gateway.workers['test'] = worker
                    try:
                        async with client.get(server.make_url(url)) as response:
                            self.assertEqual(response.status, 200)
                            self.assertEqual(await response.read(), original)
                            self.assertEqual(response.headers['Content-Type'], 'image/png')
                            self.assertEqual(response.headers['Cache-Control'], 'private, no-cache')
                            etag, modified = response.headers['ETag'], response.headers['Last-Modified']
                        for header, value in (('If-None-Match', etag), ('If-Modified-Since', modified)):
                            async with client.get(server.make_url(url), headers={header: value}) as response:
                                self.assertEqual(response.status, 304)
                                self.assertEqual(await response.read(), b'')
                        async with ClientSession() as foreign:
                            async with foreign.get(server.make_url(url)) as response:
                                self.assertEqual(response.status, 404)
                        os.utime(path, ns=(path.stat().st_atime_ns, path.stat().st_mtime_ns + 1000000))
                        async with client.get(server.make_url(url)) as response:
                            self.assertEqual(response.status, 409)
                        fresh = registry.register(path)
                        self.assertNotEqual(url, fresh)
                        self.assertEqual(url.split('?')[0], fresh.split('?')[0])
                        async with client.get(server.make_url(fresh)) as response:
                            self.assertEqual(response.status, 200)
                        path.unlink()
                        async with client.get(server.make_url(fresh)) as response:
                            self.assertEqual(response.status, 404)
                    finally:
                        gateway.workers.clear()

    async def test_real_worker_registration_and_retirement(self):
        gateway = Gateway('web_image_fixture:App', mount_path='/')
        codec = Codec()
        async with TestServer(gateway.application()) as server:
            origin = str(server.make_url('/')).rstrip('/')
            async with ClientSession(cookie_jar=CookieJar(unsafe=True)) as client:
                async with client.get(server.make_url('/')) as response:
                    # Capture the owner used for the session's relative image URLs.
                    cookie = response.cookies['pui_owner'].value
                headers = {'Origin': origin, 'Cookie': 'pui_owner=' + cookie}
                async with client.ws_connect(server.make_url('/pui/ws'), protocols=[SUBPROTOCOL], headers=headers) as ws:
                    downstream = StreamCodec()
                    await ws.send_bytes(codec.encode(dict(v=1, type='hello', session=None, seq=1, body={
                        'client_build': gateway.build, 'capabilities': ['render.snapshot', 'render.patch', 'binding.object_id'],
                        'viewport': dict(width=200, height=200, dpr=1), 'resume_id': None})))
                    async def read():
                        message = await asyncio.wait_for(ws.receive(), 5)
                        self.assertEqual(message.type, WSMsgType.BINARY)
                        return downstream.decode(message.data)
                    ready, snapshot = await read(), await read()
                    def walk(n):
                        yield n
                        for child in n['children']: yield from walk(child)
                    nodes = list(walk(snapshot['body']['roots'][0]))
                    url = next(n['props']['src'] for n in nodes if n['type'] == 'Image')
                    self.assertTrue(url.startswith('pui/images/'))
                    upstream = '/' + url
                    async with client.get(server.make_url(upstream), headers=headers) as response:
                        self.assertEqual(response.status, 200)
                    button = next(n for n in nodes if n['type'] == 'Button')
                    async def send(seq, kind, body):
                        await ws.send_bytes(codec.encode(dict(v=1, type=kind, session=ready['session'], seq=seq, body=body)))
                    await send(2, 'ack', dict(render_rev=1, applied_rev=1, status='applied'))
                    await send(3, 'event', dict(node_id=button['id'], event='click', token=button['events']['click'],
                                               observed_render_rev=1, data={}))
                    self.assertEqual((await read())['type'], 'result')
                    patch = await read()
                    await send(4, 'ack', dict(render_rev=patch['body']['rev'], applied_rev=patch['body']['rev'], status='applied'))
                    for _ in range(100):
                        if not next(iter(gateway.workers.values())).images: break
                        await asyncio.sleep(.01)
                    self.assertFalse(next(iter(gateway.workers.values())).images)
                    async with client.get(server.make_url(upstream), headers=headers) as response:
                        self.assertEqual(response.status, 404)

    def test_resources_record_transforms_without_conversion(self):
        path = Path(__file__).with_name('web-image.png')
        image = ImageResource.load(path)
        transformed = image.crop(0, 0, 2, 2).scale(12, 10, quality=1)
        self.assertEqual(image.operations, ())
        self.assertEqual(transformed.path, image.path)
        self.assertEqual(transformed.operations, (('crop', 0, 0, 2, 2), ('scale', 12, 10, True, True)))
        with self.assertRaises(ValueError): image.scale(0, 10)
