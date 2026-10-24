"""QT_QPA_PLATFORM=offscreen PYTHONPATH=tests python -m unittest dual_backend_example"""
import asyncio
import json
import threading
import unittest
from unittest.mock import patch

from aiohttp import ClientSession, CookieJar
from PySide6 import QtCore, QtGui, QtWidgets
from PUI.examples.dual_backend import CURVE, DesktopApp, SharedContent, State, web_server
from PUI.web.protocol import Codec, StreamCodec, SUBPROTOCOL


class DualBackendExampleTests(unittest.IsolatedAsyncioTestCase):
    async def test_shared_state_in_both_directions_and_shutdown(self):
        state = State()
        state.text, state.count = 'initial', 0
        state.cursor_index = None
        calls = []
        original_content = SharedContent.content

        def content(app):
            calls.append((app.backend_name, threading.get_ident(), app.state is state))
            original_content(app)

        with patch.object(SharedContent, 'content', content):
            desktop = DesktopApp(state)
            desktop.ui = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
            desktop.sync()
            self.addCleanup(desktop.ui.closeAllWindows)

            def qt_node(name):
                return next(node for node in desktop.children[0].children[0].children if node._id == name)

            with web_server(state) as url:
                async with ClientSession(cookie_jar=CookieJar(unsafe=True)) as client:
                    async with client.get(url) as response:
                        html = await response.text()
                    import re
                    build = re.search(r'data-build="([^"]+)"', html)[1]
                    async with client.ws_connect(url + 'pui/ws', protocols=[SUBPROTOCOL],
                            headers={'Origin': url.rstrip('/')}) as ws:
                        seq = 0
                        epoch = None
                        render_rev = 0
                        decoder = StreamCodec()
                        self.addCleanup(decoder.close)

                        async def send(kind, body):
                            nonlocal seq
                            seq += 1
                            await ws.send_bytes(Codec().encode(dict(v=1, type=kind, session=epoch, seq=seq, body=body)))

                        async def receive():
                            nonlocal render_rev
                            message = decoder.decode((await asyncio.wait_for(ws.receive(), 5)).data)
                            if message['type'] == 'render':
                                rev = render_rev = message['body']['rev']
                                await send('ack', dict(render_rev=rev, applied_rev=rev, status='applied'))
                                frames = message['body'].get('canvases', []) + [
                                    op['frame'] for op in message['body'].get('ops', []) if op['op'] in ('put_canvas', 'patch_canvas')]
                                for frame in frames:
                                    await send('canvas_ack', {key: frame[key] for key in
                                        ('node_id', 'frame_rev', 'measure_rev')} | {'status': 'drawn'})
                            return message

                        await send('hello', dict(client_build=build,
                            capabilities=['render.snapshot', 'render.patch', 'binding.object_id',
                                          'canvas.geometry', 'canvas.text', 'canvas.input', 'canvas.patch'],
                            viewport=dict(width=480, height=240, dpr=1), resume_id=None))
                        ready = await receive()
                        epoch = ready['session']
                        snapshot = await receive()
                        children = snapshot['body']['roots'][0]['children'][0]['children']
                        button = next(node for node in children if node['type'] == 'Button')
                        await send('event', dict(node_id=button['id'], event='click',
                            token=button['events']['click'], observed_render_rev=1, data={}))
                        while state.count != 1:
                            await receive()
                        desktop.ui.processEvents()
                        self.assertEqual(qt_node('count').ui.text(), 'Count: 1')

                        qt_node('increment').ui.click()
                        self.assertEqual(state.count, 2)
                        while 'Count: 2' not in json.dumps(await receive()):
                            pass

                        editor = qt_node('text').ui
                        editor.setText('from Qt')
                        editor.editingFinished.emit()
                        self.assertEqual(state.text, 'from Qt')
                        while 'Text: from Qt' not in json.dumps(await receive()):
                            pass

                        canvas = next(node for node in children if node['type'] == 'Canvas')
                        # A browser width different from Qt must still select the same sample.
                        await send('measure', dict(node_id=canvas['id'], measure_rev=1,
                            width=900, height=300, dpr=2, visible=True))
                        while 'put_canvas' not in json.dumps(await receive()):
                            pass
                        await send('event', dict(node_id=canvas['id'], event='mousemove',
                            token=canvas['events']['mousemove'], observed_render_rev=render_rev,
                            data=dict(x=42 + (900 - 18 - 42) / 4, y=100, button=0, buttons=0,
                                      modifiers=0, pointer_id=1, cancelled=False)))
                        while state.cursor_index != 50:
                            await receive()
                        desktop.ui.processEvents()
                        curve = qt_node('curve')
                        with patch.object(curve, 'drawText', wraps=curve.drawText) as draw_text:
                            curve.ui.repaint()
                            texts = [call.args[2] for call in draw_text.call_args_list]
                            self.assertIn('Index: 50', texts)
                            self.assertIn(f'Value: {CURVE[50]:.3f}', texts)

                        desktop.ui.processEvents()
                        qt_canvas = qt_node('curve').ui
                        left, right = desktop._plot_bounds
                        position = QtCore.QPointF(left + (right - left) * .75, 100)
                        mouse = QtGui.QMouseEvent(QtCore.QEvent.Type.MouseMove, position, position,
                            QtCore.Qt.MouseButton.NoButton, QtCore.Qt.MouseButton.NoButton,
                            QtCore.Qt.KeyboardModifier.NoModifier)
                        desktop.ui.sendEvent(qt_canvas, mouse)
                        self.assertEqual(state.cursor_index, 150)
                        while 'Index: 150' not in json.dumps(await receive()):
                            pass
                        # Clamp outside the plot, and ignore Y when choosing a curve index.
                        for x, expected in ((-100, 0), (10000, len(CURVE) - 1)):
                            desktop.hover_curve(type('Pointer', (), {'x': x, 'y': -999})())
                            self.assertEqual(state.cursor_index, expected)

        self.assertTrue(all(shared for _, _, shared in calls))
        self.assertEqual({tid for name, tid, _ in calls if name.startswith('PySide6')}, {threading.get_ident()})
        web_threads = {tid for name, tid, _ in calls if name.startswith('Web')}
        self.assertEqual(len(web_threads), 1)
        self.assertNotIn(threading.get_ident(), web_threads)
        self.assertFalse(any(thread.name.startswith('pui-web') for thread in threading.enumerate()))


if __name__ == '__main__':
    unittest.main()
