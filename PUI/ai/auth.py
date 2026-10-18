"""Credential preflight through CLI/SDK status APIs; never read token files."""
import importlib.metadata
import json
import os
import shutil
import subprocess


def check_credentials(provider):
    from . import enabled_providers
    enabled_providers(**{provider: {}})
    if provider == 'codex':
        from openai_codex.client import CodexClient, CodexConfig
        client = CodexClient(CodexConfig(), approval_handler=lambda method, params: {'decision': 'decline'})
        try:
            client.start()
            client.initialize()
            result = client.account_read({'refreshToken': True})
            if result.account is None and result.requires_openai_auth:
                raise RuntimeError('Codex credentials not found. Run codex login first.')
        finally:
            client.close()
    else:
        # The SDK bundles the CLI but has no public auth-status method. Resolve
        # the installed distribution's executable, using its public CLI command.
        distribution = importlib.metadata.distribution('claude-agent-sdk')
        filename = 'claude.exe' if os.name == 'nt' else 'claude'
        cli = next((str(distribution.locate_file(file)) for file in distribution.files or []
                    if file.name == filename and '_bundled' in file.parts), None)
        cli = cli or shutil.which('claude')
        if cli is None:
            raise RuntimeError('Claude CLI not found. Install qpuiq[claude].')
        result = subprocess.run([cli, 'auth', 'status', '--json'], capture_output=True,
                                text=True, timeout=30)
        try:
            status = json.loads(result.stdout)
        except ValueError:
            status = {}
        if result.returncode or status.get('loggedIn') is not True:
            raise RuntimeError('Claude credentials not found. Run claude auth login first.')
