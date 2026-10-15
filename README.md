# What is PUI
PUI is a reactive/declarative UI framework with two-way data binding.
PUI doesn't do UI itself, it turns imperative UI libraries into reactive/declarative flavor with virtual DOM and aims to maintain interoperability.

[Slides for SciWork 2023](https://speakerdeck.com/buganini/pui-declarative-ui-framework-for-python)

[CPPUI: Experimental C++ Version](https://github.com/buganini/CPPUI)

# Features
* [Declarative UI](REFERENCE.md#declarative-components)
* [Reactive state with two-way binding](#state--data-binding)
* [Hot Reloading](#hot-reload)
* [Multiple Backends](#backends)

# Installation

PUI requires Python 3.9 or newer. Backend packages have their own Python and
platform requirements; the versions available for your interpreter may differ.
The shared framework and PySide6 backend retain Python 3.9 support. Shared changes
must preserve that baseline even when an optional backend requires newer Python.

Choose a backend extra:

```shell
pip install 'QPUIQ[pyside6]'
pip install 'QPUIQ[wx]'
pip install 'QPUIQ[flet]'
pip install 'QPUIQ[textual]'
pip install 'QPUIQ[web]'
```

The `web` extra installs aiohttp, msgpack and zstandard with their dependencies.
Browser JavaScript, CSS and zstd WASM are bundled in the package; no separate npm
install is needed to run the backend.

Install the development/cookbook dependencies with:

```shell
pip install 'QPUIQ[dev]'      # Pygments, Matplotlib and Shapely
pip install 'QPUIQ[web,dev]'  # Web backend plus cookbook dependencies
```

The `dev` extra can be combined with any backend extra. Pip selects dependency
versions compatible with the current Python interpreter, including Python 3.9.

The flet extra installs the current Flet 1.x desktop/web runtime (minimum tested
version: 1.0.4, requiring Python 3.10 or newer). Table support uses its built-in
DataTable, including Dropdown choices and dialog editing; no table extension
is required.

For tkinter, install `QPUIQ` and use a Python build with Tk support:

```shell
pip install QPUIQ
python -c "import tkinter"
```

The optional `QPUIQ[tkinter]` spelling installs the same packages; its extra is
empty because Tk is supplied by Python or the operating system.
Some Linux distributions provide Tk support separately as
`python3-tk`; an existing virtual environment uses its base Python's native
support. wxPython can also require platform-native GTK/build dependencies.

For the framework alone, install `QPUIQ`. Optional development tools:

```shell
pip install 'QPUIQ[reload]'  # Hot reload via jurigged
pip install textual-dev # Textual development tools
```

When working from this checkout, use the project environment:

```shell
python3 -m venv env
env/bin/python -m pip install -e '.[pyside6,flet,textual,dev]'
# Add .[wx] when wxPython is available for the platform.
# Add reload to enable hot reload, e.g. -e '.[web,dev,reload]'.
```

Backend alignment and checked runtime versions are tracked in
[wx progress](doc/wx-progress.md), [flet progress](doc/flet-progress.md),
[tkinter progress](doc/tkinter-progress.md), and
[Textual plan](doc/textual-progress.md).

## Experimental Web backend

On Linux or macOS, install the Web extra and cookbook dependencies, then run:

```shell
env/bin/python -m pip install -e '.[web,dev]'
make web
```

On Windows, from the source checkout:

```powershell
py -3 -m venv env
env\Scripts\python -m pip install -e ".[web,dev]"
env\Scripts\python -m cookbook web --bind localhost:8866 --base-url /pui
```

With an activated environment, `python -m cookbook web --bind localhost:8866 --base-url /pui`
works without Make on all three platforms.

Open **http://localhost:8866/pui/** and sign in with **test / test123**.
The cookbook demonstrates optional Web authentication with these example credentials.
`make web` uses `env/bin/python`; override
`WEB_PYTHON` to select another environment. Browser JS, CSS and zstd WASM are
packaged with PUI; running the server requires no Node installation or CDN.

The cookbook currently enables VBox, HBox, Stack, Grid, Label, Button, TextField,
ProgressBar, TimelineView, Scroll, Views, Tab, Checkbox, RadioButton, Combobox,
Canvas, HeavyCanvas, DrawShapely, Image, Table, Table(Adapter) and State Binding.
Text/Spacer/Divider support the shell. Other examples show
”Not Supported for this backend”; remaining widgets and validation gaps
are tracked in [Web progress](doc/web-progress.md).
Image and Canvas images use original-file HTTP URLs with `?mtime=...`, normal
ETag/Last-Modified revalidation and browser decoding; no Pillow is required.

For an importable Application class/factory, use:

```shell
python -m PUI.web myapp:MyApplication --bind 127.0.0.1:8000 --base-url /tools/pui
```

From a Python launcher, server options belong on `Application.start()`:

```python
from myapp import MyApplication

if __name__ == "__main__":
    MyApplication().start(bind="localhost:8866", base_url="/pui", session_ttl=900)
```

`MyApplication().run(**kwargs)` also forwards to `start(**kwargs)`. Supported Web
options are `bind`, `base_url`, `mount_path`, `allow_hosts`, `trusted_proxies`,
`session_ttl`, `max_sessions`, `auth` and `auth_prompt`; their defaults are documented in the reference. The class
must be importable and constructible without arguments in each worker. Keep
launch calls under `if __name__ == "__main__":` in importable application modules.
To defer application imports to workers, launch with
`Application().start(factory="myapp:MyApplication", **options)` using
`Application` from `PUI.web`, as the generic CLI does. The cookbook calls
`Cookbook().start(**options)` and lets `start()` infer its class. Applications
do not need to import `PUI.web.server.serve`.

`auth=None` keeps access open. To require a login, pass a callable that accepts
`username, password` and returns `True` on success. The cookbook example is:

```python
Cookbook().start(
    bind="localhost:8866", base_url="/pui",
    auth=lambda username, password: {"test": "test123"}.get(username) == password,
    auth_prompt="test/test123",
)
```

`auth_prompt` optionally displays plain text below the login title, preserving
line breaks. HTML is escaped; `None` (default) or an empty string shows no prompt.
It has no effect when `auth=None`.

Login is checked in the gateway before any application worker is created.
Synchronous callbacks run in a gateway thread; async callbacks are also supported.
Exceptions or any result other than `True` deny login. A signed, HttpOnly,
SameSite cookie stores login authorization without usernames or passwords;
HTTPS makes it Secure. It is a browser-session cookie scoped to `base_url`,
independent of worker TTLs and per-tab resume IDs. **New session**, resume and
worker crashes do not require another login. Restarting the server changes the
cookie signing key and requires login again. The login form uses a separate
signed CSRF cookie; assets stay public, while unauthenticated WebSockets and
application images are denied. Custom authentication is configured in the Python
launcher; the generic CLI remains open without a callback.

`bind` replaces the former `host`/`port` arguments and `--host`/`--port` flags.
It accepts `hostname:port`, `IPv4:port`, `[IPv6]:port`, or a Unix socket path.
The server default is `127.0.0.1:8000`; the cookbook default is `localhost:8866`.
Use `WEB_BIND` with Make:

```shell
make web WEB_BIND='127.0.0.1:8866'
make web WEB_BIND='[::1]:8866'
make web WEB_BIND='./pui.sock'
```

On Linux/macOS, `MyApplication().start(bind="/run/pui/pui.sock", base_url="/pui")`
listens only on that Unix socket. Relative paths and `pathlib.Path` are also
accepted. Create the parent directory first; its permissions and the server's
umask determine who can access the socket. The proxy user needs permission to
connect. Existing files/sockets are never overwritten, and normal shutdown
removes only the socket created by this process. After an ungraceful shutdown,
remove a stale socket only after confirming its server has stopped. Windows
uses TCP binds; Unix sockets and named pipes are not enabled there.

For nginx with a prefix-preserving Unix socket upstream:

```nginx
location /pui/ {
    proxy_pass http://unix:/run/pui/pui.sock;
    proxy_http_version 1.1;
    proxy_set_header Host $http_host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

`base_url` still defines the public URL prefix; it is independent of `bind`.

Python computes VDOM diffs and owns callbacks/State in a dedicated worker
process per tab. Linux uses a clean standard-library `forkserver` supervisor;
macOS and Windows use `spawn` to start fresh Python interpreters. Workers
import and construct their own application. Keep module-level code safe to import
again and guard server launch calls with `if __name__ == "__main__":`.
The gateway may import the application and construct a launcher instance,
but it does not build the UI or transfer the launcher's State to workers.
The browser applies patches over a binary MessagePack + Zstandard WebSocket.
A signed HttpOnly cookie owns sessions; per-tab IDs identify workers. Disconnects
retain the worker for **900 seconds** by default (`--session-ttl`); reconnects use
a full snapshot and never replay uncertain actions. Connected sessions do not
expire through this TTL. Stopping the server reaps its workers.
Use `Application.start(session_ttl=0)` or CLI `--session-ttl 0` to retain
disconnected sessions indefinitely instead of expiring them. This replaces the
former immediate-expiry meaning of zero. Retained workers still count toward
`max_sessions`; explicit application quit, worker failure and server shutdown
still end sessions. Choosing New session leaves the previous worker retained
indefinitely when TTL is zero.
On reload or recoverable connection loss, a tab with a saved session ID offers **Resume session**
and **New session** before opening another WebSocket. First visits connect directly.
Resume keeps the worker's Python state if it is still available; an expired session
creates a new one. New session starts a fresh worker and leaves the old worker to
expire under its existing TTL. The application is inactive until the chosen
session's snapshot arrives; unsent edits and pending actions are not replayed.
A session still connected (including an old connection still closing) cannot be
taken over; the banner allows another resume attempt or New session. Failed
connection attempts retry the chosen option without asking again; a subsequent
established-connection loss asks again.

Both process strategies pass the server/transport tests on Linux with Python
3.9 and 3.14; the Chrome cookbook suite also passes with spawned workers.
Native macOS/Windows execution, including Windows Proactor I/O and console
shutdown, still needs validation.
Run `python -m unittest discover -s tests -p "web_*.py"` from the checkout to
exercise the native worker strategy. The extra spawn suite runs on Linux too;
descriptor/RSS soak and nginx proxy harnesses remain Linux-specific.

`--base-url` accepts a public path prefix or absolute HTTP(S) URL.
`--mount-path /` supports proxies that strip the public prefix; otherwise the
upstream preserves it. When nginx terminates HTTPS and forwards HTTP, preserve
the public Host and set the original scheme:

```nginx
proxy_set_header Host $http_host;
proxy_set_header X-Forwarded-Proto $scheme;
```

PUI trusts `X-Forwarded-Proto` from loopback peers (`127.0.0.0/8`, `::1/128`) and Unix sockets
by default, so plain `make web` with `/pui` works through a local HTTPS proxy
and directly over HTTP. HTTPS uses WSS and a Secure cookie. The proxy must
overwrite the header with a single `http` or `https` value.

For a proxy on another machine or container network, set
`trusted_proxies=["192.0.2.10", "2001:db8::/64"]` on `start()`, repeat CLI
`--trusted-proxy IP_OR_CIDR`, or use
`make web WEB_TRUSTED_PROXIES="192.0.2.10 2001:db8::/64"`. These replace the
defaults. Include `"unix"` in an explicit list to trust Unix socket peers, or
use `--trusted-proxy unix`. Use `trusted_proxies=[]`, `--no-trusted-proxy`, or
`make web WEB_TRUSTED_PROXIES=` to ignore forwarded protocol headers.
Trust uses the immediate socket peer, never a forwarded client address;
`X-Forwarded-Host`, `X-Forwarded-For` and `Forwarded` do not change request identity.
An absolute `base_url`, such as `WEB_BASE_URL=https://example.com/pui`, remains
available to fix the public origin explicitly. The transport/session contract
and remaining limitations are in [Web API](doc/web-api.md).

Host access is configured separately with `allow_hosts`, which defaults to
`["*"]`. To restrict it, use `--allow-host example.com` (repeat for multiple
hosts), or `make web WEB_ALLOW_HOSTS="example.com localhost"`. Entries are exact
host names without schemes, paths or ports; request ports are ignored and IPv6
entries use brackets. The proxy must preserve the public Host when restricting
it this way. This HTTP Host policy applies to every route; WebSocket Origin
validation remains independent, including when `allow_hosts=["*"]`.

Python 3.9 and 3.14 transport/lifecycle tests and real Chrome cookbook/codec tests
pass. Tested Python dependency versions are pinned in [tests/requirements-web.txt](tests/requirements-web.txt).
With nginx, Node and Playwright/Chrome already installed, run
`env/bin/python tests/web_proxy.py` for an isolated prefix-stripping proxy check.
Add `--unix` to test a Unix socket upstream, including socket cleanup on shutdown.
Set `PUI_NODE` and `PUI_BROWSER_MODULES` if these test tools are outside normal
search paths. The check starts local services on temporary ports and cleans them
up without changing the system proxy.

To rebuild browser assets (Node and pnpm are development tools only):

```shell
mkdir -p env/web-client
cp web-client/package.json web-client/pnpm-lock.yaml env/web-client/
pnpm --dir env/web-client install --ignore-scripts --frozen-lockfile
make web-build
```

Restart the server after rebuilding. This uses the pinned @msgpack/msgpack,
@bokuweb/zstd-wasm, fzstd and esbuild packages; upstream modules are bundled without edits.
Python uses a 4 MiB history window for the downstream zstd stream and flushes
after each complete message (one whole DOM/Canvas batch per render); fzstd
retains browser decompression history until disconnect. Upstream events retain
independent zstd frames.

## Python 3.9 compatibility

The shared and Qt regression suites pass on Python 3.9.24 with PySide6 6.7.2 on
Linux. This covers state/bindings, lifecycle, signatures and legacy decorators,
plus Qt windows, controls, tables, trees, scrolling, Tabs, and Views. It does not
validate integration with an application's embedded interpreter or other platforms.
[PySide6 6.7.2 supports Python 3.9–3.12](https://pypi.org/project/PySide6/6.7.2/).
To use this tested combination on Python 3.9:

```shell
python3.9 -m pip install 'QPUIQ[pyside6]' 'PySide6==6.7.2'
```

To reproduce the compatibility check from a checkout, create a separate runtime
under `env/` and install only the packages needed for this baseline:

```shell
python3.9 -m venv env/python39
env/python39/bin/python -m pip install -e . -r tests/requirements-python39.txt
make check-python39
# Or use an existing environment: make check-python39 PYTHON39=/path/to/python3.9
```

The test runtime is pinned to `PySide6==6.7.2` in
[tests/requirements-python39.txt](tests/requirements-python39.txt), and
`make check-python39` rejects a different PySide6 version. The check runs the
shared and Qt regression suites; the Flet-specific signature test is skipped in
this environment.
The normal backend extra continues to allow newer versions. Run this check when changing
shared code or the Qt backend. Keep Python 3.10-only syntax and APIs, including
standard-library `ParamSpec`, out of code used by the Python 3.9 baseline.

# Get Started

Define applications by subclassing the backend's `Application`, and reusable
views by subclassing its `PUIView`. Put UI declarations in `content()`, initialize
local state in `setup()`, and use member functions as event handlers. Classes
are the recommended API; `@PUI` and `@PUIApp` are deprecated and retained for
compatibility. See the [migration reference](REFERENCE.md#deprecated-decorators).

## Hello World
```python
# example/hello_world.py
from PUI.PySide6 import *

class Example(Application):
    def content(self):
        with Window(title="test", size=(320,240)):
            Label("Hello world")

root = Example()
root.run()
```
![Hello World](screenshots/hello_world.png)

## State & Data Binding
```python
# example/generic_textfield.py
from PUI.PySide6 import *

data = State()
class Example(Application):
    def __init__(self):
        super().__init__()
        data.var = 0

    def content(self):
        with Window(title="blah"):
            with VBox():
                with HBox():
                    Button("-").click(self.on_minus)
                    Label(f"{data.var}")
                    Button("+").click(self.on_plus)

                TextField(data("var")) # binding

    def on_minus(self, event):
        data.var -= 1

    def on_plus(self, event):
        data.var += 1

root = Example()
root.run()
```
![State & Data Binding](screenshots/pyside6_textfield.png)

## View Component
```python
# example/bleak_list.py

....

class DeviceView(PUIView):
    def __init__(self, device, advertising_data):
        super().__init__()
        self.device = device
        self.advertising_data = advertising_data

    def content(self):
        Label(f"{self.device.address} {self.device.name} {self.advertising_data.rssi}")

class GUI(Application):
    def __init__(self, state):
        super().__init__()
        self.state = state

    def content(self):
        with Window(title="BLE List"):
            with VBox():
                Label(f"Found {len(self.state.scanned_devices)} devices")
                for device, advertising_data in self.state.scanned_devices:
                    DeviceView(device, advertising_data)

....
```
![View Component](screenshots/bleak_list.png)

## Layout & Styling

PUI handles normal widget sizing automatically. Each component supplies a
preferred size and expansion policy appropriate to the widget and its position
in an `HBox` or `VBox`; for example, a `TextField` uses the available horizontal
space while retaining its native height, and a `Spacer` consumes flexible space.
Application code normally does not need to assign control dimensions just to
make a layout fit.

Use `.layout(width=..., height=..., weight=..., padding=..., margin=...)` when a
design needs an explicit size, a particular share of flexible space, or custom
spacing. PUI translates these semantic rules to each backend's native layout
system, so exact pixel sizes can still vary with the toolkit, platform, font,
and theme.

Web resolves flexible space on the parent container's main axis: width in HBox,
height in VBox. Positive weights take priority over automatic expansion;
`weight=0` preserves the widget's preferred size. Setting only Canvas width or
height leaves its other axis flexible. See the [layout reference](REFERENCE.md#common-modifiers)
for the priority rules and the [Web plan](doc/web-progress.md) for specification
differences still needing clarification.

```python
# example/pyside6_feedparser.py

...
with VBox():
    Label(title).qt(StyleSheet={"font-weight":"bold"}) # QT-specific

    with HBox():
        with Scroll():
            with VBox():
                for i,e in enumerate(entries):
                    Label(e.title).click(self.entry_selected, i)
                Spacer()

        with Scroll().layout(weight=1): # Generic Layout Parameter
            if 0 <= selected and selected < len(entries):
                (Text(entries[selected].description)
                    .layout(padding=10) # Generic Layout Parameter
                    .qt(StyleSheet={"background-color":"white", "color":"black"})) # QT-specific
...
```
![Layout & Styling](screenshots/feed_parser_padding.png)


## Canvas
```python
# example/generic_canvas.py

from PUI.PySide6 import *

data = State()
class Example(Application):
    def __init__(self):
        super().__init__()
        data.var = 50

    def content(self):
        with Window(title="blah", size=(640,480)):
            with VBox():
                Canvas(self.painter, data.var)
                with HBox():
                    Button("-").click(self.on_minus)
                    Label(f"{data.var}").layout(weight=1)
                    Button("+").click(self.on_plus)

    @staticmethod
    def painter(canvas, var):
        # Canvas coordinates are logical pixels. Use pixel_density when
        # preparing raster images for HiDPI displays.
        raster_scale = canvas.pixel_density
        canvas.drawText(var, var/2, f"blah {var}")
        canvas.drawLine(var, var, var*2, var*3, color=0xFFFF00)

    def on_minus(self, event):
        data.var -= 1

    def on_plus(self, event):
        data.var += 1

root = Example()
root.run()
```

`canvas.pixel_density` is the number of physical display pixels per logical
canvas pixel. It is updated before each paint where the backend exposes the
display scale, so moving a window between displays is handled automatically.
Canvas coordinates remain in logical pixels; multiply raster image resolution
by `pixel_density` when generating HiDPI content. Backends that cannot report a
display scale use `1.0`.

![Canvas](screenshots/pyside6_canvas.gif)

## Cookbook

From the repository root, install a backend and the cookbook dependencies:

```shell
env/bin/python -m pip install -e '.[pyside6,dev]'
env/bin/python -m cookbook PySide6
```

The `dev` extra includes Pygments for the code viewer, Matplotlib for the
MatplotlibCanvas example, and Shapely 2.x or newer for DrawShapely.
[cookbook/requirements.txt](cookbook/requirements.txt) remains an equivalent
dependency list. Choose a different backend extra as needed; for Tkinter,
use `-e '.[dev]'` with a Tk-enabled Python. Backend support still determines
which examples are available. Hot reload and Textual development tools are optional.

The code viewer uses a fixed dark Monokai palette. Backends without HTML support
show plain text with the same dark background and light foreground.

Select **HeavyCanvas** for a dark, four-panel synthetic market chart: candles
with Bollinger bands, volume, K/D and RSI. It starts with 500 trading sessions;
choose 1,650 or 6,000 for about 15,000 or 54,000 Painter calls per frame. Hover
for the crosshair and English data tooltip. Wheel up/down over the plot to
zoom in/out around the pointer; **Reset zoom** restores the whole dataset.
Visible session counts and draw-call estimates make large coordinate changes
easy to compare with tooltip-only updates. **Regenerate** creates another
seeded dataset. Data and indicators are cached between pointer updates. The
example uses only the standard library and PUI Canvas, with no market feed or
extra plotting dependency. Tkinter currently draws at its requested Canvas
size and has no hover/wheel events; its chart is static between control changes.

Web sends only the changed command interval when a Canvas frame can reuse its
prefix/suffix, with full frames for initial load, resize, reconnect and recovery.
The browser reconstructs the list and repaints it. Compare full-frame and delta
encoding with `env/bin/python tests/web_canvas_benchmark.py 6000` (or `500`);
no painter API changes are needed.

![Cookbook 1](screenshots/cookbook1.png)
![Cookbook 2](screenshots/cookbook2.png)

`python -m cookbook textual`

Use `make textual` to run the Textual cookbook. For development mode, install
`textual-dev` and use `make textual_dev`.

![Cookbook textual](screenshots/cookbook_textual.png)

`python -m cookbook flet`
![Cookbook flet](screenshots/cookbook_flet.png)

`python -m cookbook tkinter`
![Cookbook tkinter](screenshots/cookbook_tkinter.png)

# Hot Reload
``` shell
pip install 'QPUIQ[reload]'
```
Then PUI will take care of view update [(code)](https://github.com/buganini/PUI/blob/main/PUI/__init__.py#L11)


# Backends
## Tier-1
* PySide6
## Lower Priority
* wx
* tkinter
    * or https://github.com/rdbende/Sun-Valley-ttk-theme
* flet
* textual (Text Mode)
    * no canvas

# Documents
* [Components Reference](https://buganini.github.io/PUI/doc/Reference.html)
* [Layout Strategy](https://buganini.github.io/PUI/doc/Layout.html)

# Used by
* https://github.com/buganini/Kikakuka

# TODO
* Dump with layout parameters and add test cases
* [Toga](https://beeware.org/project/projects/libraries/toga/)
* [ISSUE] flet layout sizing (cookbook scroll example)
* nested state trigger
    * set state in PUIView __init__
    * set state in setup() ?
* Tabs(`tabposition`)
* Lazy List
* UI Flow
    * Navigation Stack
    * View Router
    * Model Window/Dialog
* Layout
    * SwiftUI style overlay ??
* Canvas
    * Arc
    * ...
* State with Pydantic support?
