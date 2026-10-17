"""Browser smoke fixture with a local fake agent; no model requests."""
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import patch
from aiohttp import web
from PUI.web.server import Gateway
from PUI.ai.session import Session
import PUI.web as UI
from PUI import Options


class App(UI.Application):
    def setup(self):
        self.state = UI.State({'value': Options.get('example.value', 'initial')})

    def content(self):
        with UI.Window(title='AI browser smoke'):
            with UI.VBox():
                UI.Label('Application worker is running')
                UI.TextField(self.state('value').ref('example.value'))


class Agent:
    def __init__(self, provider, key, session):
        self.session = session

    async def run(self, prompt):
        answer = await self.session.ask('Edit workspace file?', {'file': 'example.txt'})
        if answer['allow']:
            Path(self.session.cwd, 'example.txt').write_text(prompt)
        self.session.message('assistant', 'Edit saved' if answer['allow'] else 'Edit denied', 'codex')

    async def interrupt(self):
        pass

    async def close(self):
        pass


async def main():
    with tempfile.TemporaryDirectory() as directory:
        def create(credentials, lock, changed):
            return Session(credentials, lock, changed, cwd=directory, provider_factory=Agent)
        with patch('PUI.web.ai.Session', side_effect=create):
            gateway = Gateway('ai_web_fixture:App', codex=True)
            runner = web.AppRunner(gateway.application())
            await runner.setup()
            site = web.TCPSite(runner, '127.0.0.1', 0)
            await site.start()
            print('BROWSER_SMOKE_URL=http://127.0.0.1:' + str(site._server.sockets[0].getsockname()[1]), flush=True)
            try:
                await asyncio.Event().wait()
            finally:
                await runner.cleanup()


if __name__ == '__main__':
    asyncio.run(main())
