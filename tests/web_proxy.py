"""Run Chrome cookbook checks through an isolated prefix-stripping nginx.

Requires existing nginx, Node and Playwright/Chrome installations. Run with the
Web Python environment; PUI_NODE and PUI_BROWSER_MODULES may select local tools.
No system nginx configuration is changed.
"""
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen


def free_port():
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        return listener.getsockname()[1]


def main():
    nginx = shutil.which('nginx')
    node = os.environ.get('PUI_NODE') or shutil.which('node')
    if not nginx or not node:
        raise SystemExit('Install/configure nginx and Node before running this optional deployment check')
    root = Path(__file__).resolve().parents[1]
    upstream, public = free_port(), free_port()
    while public == upstream:
        public = free_port()
    url = 'http://127.0.0.1:%s/pui/' % public
    processes = []
    with tempfile.TemporaryDirectory(prefix='pui-web-proxy-') as directory:
        directory = Path(directory)
        config = directory / 'nginx.conf'
        config.write_text('''
worker_processes 1;
pid nginx.pid;
error_log stderr warn;
events { worker_connections 64; }
http {
    access_log off;
    client_body_temp_path body;
    proxy_temp_path proxy;
    map $http_upgrade $connection_upgrade { default upgrade; '' close; }
    server {
        listen 127.0.0.1:%s;
        location /pui/ {
            proxy_pass http://127.0.0.1:%s/;
            proxy_http_version 1.1;
            proxy_set_header Host $http_host;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection $connection_upgrade;
        }
    }
}
''' % (public, upstream))
        with (directory / 'services.log').open('w+') as log:
            try:
                processes.append(subprocess.Popen([sys.executable, '-m', 'cookbook', 'web',
                    '--host', '127.0.0.1', '--port', str(upstream), '--base-url', url,
                    '--mount-path', '/', '--allow-host', '127.0.0.1'], cwd=root,
                    stdout=log, stderr=log, start_new_session=True))
                processes.append(subprocess.Popen([nginx, '-p', str(directory) + '/',
                    '-c', str(config), '-g', 'daemon off;'], stdout=log, stderr=log,
                    start_new_session=True))
                deadline = time.monotonic() + 10
                while True:
                    if any(process.poll() is not None for process in processes):
                        raise RuntimeError('Proxy or gateway exited during startup')
                    try:
                        with urlopen(url, timeout=.2) as response:
                            if response.status == 200:
                                break
                    except OSError:
                        pass
                    if time.monotonic() >= deadline:
                        raise RuntimeError('Proxy/gateway startup timed out')
                    time.sleep(.05)
                subprocess.run([node, 'tests/web_browser.cjs'], cwd=root,
                    env=dict(os.environ, PUI_WEB_URL=url, PUI_PYTHON=sys.executable),
                    check=True, timeout=90)
                print('Prefix-stripping nginx deployment checks passed.')
            except BaseException:
                log.flush()
                log.seek(0)
                print(log.read()[-8000:], file=sys.stderr)
                raise
            finally:
                for process in reversed(processes):
                    if process.poll() is None:
                        os.killpg(process.pid, signal.SIGINT)
                        try:
                            process.wait(timeout=8)
                        except subprocess.TimeoutExpired:
                            os.killpg(process.pid, signal.SIGKILL)
                            process.wait()


if __name__ == '__main__':
    main()
