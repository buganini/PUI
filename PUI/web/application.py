"""Server entry point over the shared browser application model."""
from .._browser.widgets import Application as BrowserApplication


class Application(BrowserApplication):
    def start(self, *, factory=None, auth=None, auth_prompt='', socket_mode=None, **kwargs):
        """Start the Web server; forward keyword options to the server runtime.

        Omit factory to use this instance's importable Application class. CLI
        launchers may supply module:Class/factory to defer imports to workers.
        The application title is forwarded to the gateway and each worker.
        Optional auth(username, password) must return True to allow login.
        Optional auth_prompt is plain text displayed on the login page.
        Optional socket_mode sets Unix socket permissions; None leaves them unchanged.
        """
        from .server import serve
        import sys
        if factory is None:
            module = type(self).__module__
            if module == '__main__':
                spec = sys.modules[module].__spec__
                if spec is None:
                    raise ValueError('Use an importable Application class or python -m PUI.web module:Class')
                module = spec.name
            factory = module + ':' + type(self).__qualname__
        return serve(factory, title=self.title, auth=auth, auth_prompt=auth_prompt,
                     socket_mode=socket_mode, **kwargs)
