"""Blocking callbacks over real worker IPC, including queued input and detach."""
import unittest
import web_server


class DialogTests(unittest.IsolatedAsyncioTestCase):
    asyncTearDown = web_server.ServerTests.asyncTearDown
    connect = web_server.ServerTests.connect
    read = web_server.ServerTests.read
    send = web_server.ServerTests.send
    nodes = web_server.ServerTests.nodes
    disconnect = web_server.ServerTests.disconnect

    async def asyncSetUp(self):
        await web_server.ServerTests.asyncSetUp(self)
        self.gateway.factory = 'web_dialog_fixture:App'
        self.gateway.sessions.session_ttl = 0

    async def begin(self):
        ws = await self.connect()
        ready, render = await self.read(ws), await self.read(ws)
        self.epoch = ready['session']
        self.sequence = 1
        await self.transmit(ws, 'ack', {'render_rev': 1, 'applied_rev': 1, 'status': 'applied'})
        buttons = [n for n in self.nodes(render) if n['type'] == 'Button']
        await self.click(ws, buttons[0])
        dialog = await self.read(ws)
        self.assertEqual(dialog['type'], 'dialog')
        self.assertEqual(dialog['body']['kind'], 'confirm')
        return ws, ready, buttons, dialog

    async def transmit(self, ws, kind, body):
        self.sequence += 1
        await self.send(ws, self.epoch, self.sequence, kind, body)

    async def click(self, ws, button):
        await self.transmit(ws, 'event', {'node_id': button['id'], 'event': 'click',
            'token': button['events']['click'], 'observed_render_rev': 1, 'data': {}})

    async def reply(self, ws, dialog, value):
        await self.transmit(ws, 'dialog_result', {'request_id': dialog['body']['request_id'], 'value': value})

    async def finish_dialogs(self, ws, dialog, confirm, text):
        await self.reply(ws, dialog, confirm)
        prompt = await self.read(ws)
        self.assertEqual(prompt['body']['kind'], 'prompt')
        self.assertEqual(prompt['body']['default'], 'initial')
        await self.reply(ws, prompt, text)
        alert = await self.read(ws)
        self.assertEqual(alert['body']['kind'], 'alert')
        await self.reply(ws, alert, None)
        result = await self.read(ws)
        self.assertEqual(result['type'], 'result')
        self.assertEqual(result['body']['reply_to'], 3)
        self.assertEqual(result['body']['status'], 'processed')
        render = await self.read(ws)
        self.assertEqual(render['type'], 'render')
        return render

    async def test_confirm_prompt_and_alert_return_synchronously(self):
        for confirm, text in ((True, '世界'), (False, None), (True, '')):
            ws, _, _, dialog = await self.begin()
            render = await self.finish_dialogs(ws, dialog, confirm, text)
            self.assertIn(repr((confirm, text)), str(render['body']))
            await self.disconnect(ws)

    async def test_input_queued_during_dialog_is_processed_after_callback(self):
        ws, _, buttons, dialog = await self.begin()
        await self.click(ws, buttons[1])
        await self.finish_dialogs(ws, dialog, True, 'hello')
        result = await self.read(ws)
        self.assertEqual(result['type'], 'result')
        self.assertEqual(result['body']['reply_to'], 4)
        self.assertEqual(result['body']['status'], 'processed')

    async def test_disconnect_unblocks_callback_and_resume_keeps_worker(self):
        ws, ready, _, _ = await self.begin()
        await self.disconnect(ws)
        ws = await self.connect(resume_id=ready['body']['resume_id'])
        resumed, render = await self.read(ws), await self.read(ws)
        self.assertTrue(resumed['body']['resumed'])
        self.assertIn('disconnected', str(render['body']))

    async def test_invalid_reply_type_is_rejected(self):
        ws, _, _, dialog = await self.begin()
        await self.reply(ws, dialog, 'not a boolean')
        # A malformed reply ends the connection; it cannot complete the dialog.
        message = await ws.receive(timeout=10)
        from aiohttp import WSMsgType
        self.assertIn(message.type, (WSMsgType.CLOSE, WSMsgType.CLOSED, WSMsgType.BINARY))
        if message.type == WSMsgType.BINARY:
            decoded = self.decoders[ws].decode(message.data)
            self.assertEqual(decoded['type'], 'error')


class SpawnDialogTests(DialogTests):
    async def asyncSetUp(self):
        import multiprocessing
        await super().asyncSetUp()
        self.gateway.context = multiprocessing.get_context('spawn')
