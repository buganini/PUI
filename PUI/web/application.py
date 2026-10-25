"""Server entry point over the shared browser application model."""
from .. import _typing as _t
from .._browser.widgets import Application as BrowserApplication


class Application(BrowserApplication):
    def start(self, *, factory=None, passthru=False, wstunnel=None, auth=None, auth_prompt='', socket_mode=None, landlock=None, codex: _t.AIProvider = None, claude: _t.AIProvider = None, upload_limits=None, **kwargs):
        """Start the Web server; forward keyword options to the server runtime.

        Omit factory to use this instance's importable Application class. CLI
        launchers may supply module:Class/factory to defer imports to workers.
        passthru=True runs this instance (or the supplied factory) in-process,
        retaining one session without worker processes. State thread safety is unchanged.
        The application title is forwarded to the gateway and each worker.
        Optional auth(username, password) returns {"auth": bool, "ai": bool}.
        Optional auth_prompt is plain text displayed on the login page.
        auth_idle_timeout (4200) and auth_max_age (86400) are seconds, forwarded via kwargs.
        Optional landlock configures Linux worker filesystem allowlists.
        Optional socket_mode sets Unix socket permissions; None leaves them unchanged.
        Optional wstunnel={"url": "wss://relay/_puitunnel", "token": "..."} tunnels this
        TCP listener through a reverse client in a managed background process.
        """
        from .server import serve
        import sys
        if passthru and factory is None:
            factory = lambda: self
        elif factory is None:
            module = type(self).__module__
            if module == '__main__':
                spec = sys.modules[module].__spec__
                if spec is None:
                    raise ValueError('Use an importable Application class or python -m PUI.web module:Class')
                module = spec.name
            factory = module + ':' + type(self).__qualname__
        return serve(factory, passthru=passthru, wstunnel=wstunnel, title=self.title, auth=auth, auth_prompt=auth_prompt,
                     socket_mode=socket_mode, landlock=landlock, codex=codex, claude=claude, upload_limits=upload_limits, **kwargs)
