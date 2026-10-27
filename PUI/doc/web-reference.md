# Web backend reference

Web-specific startup, deployment and widget behavior live here. The
[common reference](Reference.html) defines shared component APIs and backend
differences; [Web progress](https://github.com/buganini/PUI/blob/main/notes/web-progress.md) tracks missing work, and the
[wire contract](web-api.md) describes the Python/JavaScript protocol.

- [Installation and startup](#installation-and-startup)
- [In-process execution (passthru)](#in-process-execution-passthru)
  - [Shared State with PySide6](#shared-state-with-pyside6)
- [Application titles](#application-titles)
- [Binding and reverse proxies](#binding-and-reverse-proxies)
- [Reverse tunnel](#reverse-tunnel)
- [Authentication](#authentication)
- [Sessions and reconnection](#sessions-and-reconnection)
- [State bindings](#state-bindings)
- [URL Options and State refs](#url-options-and-state-refs)
- [Layout and sizing](#layout-and-sizing)
- [Widgets](#widgets)
- [Canvas](#canvas)
- [Image](#image)
- [Table](#table)
- [Transport and runtime](#transport-and-runtime)
- [Development and validation](#development-and-validation)

## Installation and startup

Install `QPUIQ[web]` for aiohttp, msgpack and zstandard plus their transitive
dependencies. Browser JS/CSS/WASM assets ship in the wheel; no Node or CDN is
required at runtime. Add `cookbook` for the cookbook's Pygments, Matplotlib and
Shapely dependencies, or `reload` for jurigged. From a checkout on Linux/macOS:

```shell
python3 -m venv env
env/bin/python -m pip install -e '.[web,cookbook]'
make web
```

On Windows, from the checkout:

```powershell
py -3 -m venv env
env\Scripts\python -m pip install -e ".[web,cookbook]"
.\build.ps1
env\Scripts\python -m PUI.cookbook web --bind localhost:8866 --mount-path /pui
```

With an activated environment, run
`python -m PUI.cookbook web --bind localhost:8866 --mount-path /pui` without Make on
Linux, macOS or Windows. Open **http://localhost:8866/pui/** and sign in with
**test / test123** for ordinary access, or **dev / dev123** for AI access when
Codex/Claude is enabled. The cookbook demonstrates optional Web authentication.
`make web` uses `env/bin/python`; override `WEB_PYTHON` to select another environment.

The Web backend currently supports
Application, Window, VBox/HBox, Stack, Grid, Label, Button, TextField, MaskedField, Text, ProgressBar, Spacer, Divider and
Scroll, Splitter, Views, Tabs, Checkbox, RadioButton, ComboBox, Table, Image and Canvas geometry/text/images. It is not yet included in
the common reference's full backend matrix.
Constructing an unsupported Web widget raises `NotImplementedError` naming that
widget, for example `Tree is not implemented by the Web backend`.

The cookbook also includes HeavyCanvas, DrawShapely, TimelineView,
Table(Adapter) and State & Binding. Text/Spacer/Divider support the shell. Other examples show
"Not Supported for this backend"; [Web progress](https://github.com/buganini/PUI/blob/main/notes/web-progress.md) tracks remaining
widgets and validation gaps.

HeavyCanvas defaults to 1,000 synthetic sessions and offers 1,000, 3,000,
5,000, 7,500, 10,000, 15,000, 20,000, 25,000 and 30,000 sessions. Each session
adds about nine drawing commands; hover adds a crosshair and tooltip, and wheel
zoom exercises large command replacements.
The larger native-backend presets (120,000 through 1,000,000 sessions) are not
offered in Web; its Canvas and transport limits remain unchanged.

For an importable Application class/factory:

```shell
python -m PUI.web myapp:MyApplication --bind 127.0.0.1:8000 --mount-path /tools/pui
```

From a Python launcher:

```python
from myapp import MyApplication

if __name__ == "__main__":
    MyApplication().start(bind="localhost:8866", mount_path="/pui", session_ttl=900)
```

The Python entry point is `Application.start(*, factory=None, auth=None, auth_prompt='', socket_mode=None, wstunnel=None, **kwargs)`;
`run(**kwargs)` delegates to it without building the UI in the gateway.
Server options are `bind='127.0.0.1:8000'`,
`mount_path=None`, `allow_hosts=None`, `trusted_proxies=None`, `session_ttl=900`
and `max_sessions=64`, with optional `auth=None`, `auth_prompt=''` and `socket_mode=None`.

### Starting and stopping from another thread

`start()` blocks until the server exits and finishes cleanup. `stop()` can be
called from another thread and blocks until HTTP/WebSocket connections, session
workers, the tunnel process and the event loop have been closed. Repeated calls
are safe. A stop requested before or during startup is remembered, preventing a
late-starting server from being left running.

`wait_started(timeout=None)` waits for a listener to be ready and returns its
TCP URL (including the allocated port for `bind="127.0.0.1:0"`) or its Unix socket
path. Startup errors propagate to both `start()` and `wait_started()`. If stopped
before becoming ready, `wait_started()` raises `RuntimeError`. An optional timeout
raises `TimeoutError` without stopping the server.

```python
from concurrent.futures import ThreadPoolExecutor

web_app = MyApplication()
with ThreadPoolExecutor(max_workers=1) as executor:
    serving = executor.submit(web_app.start, bind="127.0.0.1:0", passthru=True)
    try:
        url = web_app.wait_started()
        run_desktop_ui()
    finally:
        web_app.stop()
        serving.result()
```

Blocking `stop()` cannot be called on the Web server's own thread: it raises
`RuntimeError` to avoid waiting on itself. Use the controlling thread to stop the
server. Signal handling is enabled on the main thread and disabled on background
threads. Application code does not need to manage aiohttp, `Gateway`, or tunnel
lifecycle callbacks.

### Application workers

When `factory` is omitted, the instance's importable class is constructed without
arguments separately in each client worker. Instance state is not transferred.
CLI launchers use `Application` from `PUI.web` with
`Application().start(factory='module:Class', **options)` to defer application
imports; `module:factory` must return an Application instance.
The cookbook uses `Cookbook().start(**options)` directly; its gateway imports
the application and constructs a launcher without building its UI. Each worker
imports the application independently and constructs its own instance/State.
Application code does not need to call `PUI.web.server.serve` directly.
Linux uses a `forkserver` context with no preloaded modules; macOS and Windows
use `spawn`. The gateway does not change the application's global multiprocessing
start method. Guard launcher calls with `if __name__ == "__main__":` and keep
module imports safe to repeat in spawned interpreters. IPC uses standard-library
socket pairs and asyncio streams; each worker still handles one client serially.
The native strategy and an additional Linux spawn suite cover session isolation,
resume/expiry, failures, shutdown and backpressure. Native macOS/Windows execution,
Windows Proactor I/O, console interrupts and frozen applications remain unverified.

## Filesystem restrictions

Install `QPUIQ[web,landlock]` and pass `landlock={"read": [...], "write": [...]}`
to `Application.start()` (or `serve()`). Linux workers apply the policy before
importing the application factory, including newly created/renewed sessions.
The HTTP gateway remains unrestricted. See [Landlock](landlock.md) for explicit
runtime permissions, failure behavior and security boundaries.

## In-process execution (passthru)

Use `app.start(passthru=True)` to run the existing application instance in the
calling process, without worker processes or a multiprocessing supervisor.
The call blocks and owns its event loop; it can run in a background thread
(with signal handling disabled automatically). Application callbacks run on
that thread. State operations are synchronized; use `with state:` for compound
updates and consistent multi-field reads when sharing State with another backend.
Keep native widget access on its owning UI thread.

```python
app.start(passthru=True, bind="127.0.0.1:8000")
```

CLI factories are also supported:

```shell
python -m PUI.web myapp:App --passthru
python -m PUI.cookbook web --passthru
```

Passthru keeps the existing HTTP/WebSocket protocol and an I/O helper thread.
It supports one server per process and one retained browser session: it forces
`max_sessions=1` and `session_ttl=0`. Page loads and transient disconnects automatically reconnect to that session,
without a Resume/Renew/Logout menu. Renewal and logout endpoints are disabled.
This is not a multi-client broadcast mode. Authentication expiry can still end
the session. An existing application instance cannot be reused
after destruction; supply `factory=App` (a callable) or `factory="myapp:App"`
if sessions must be recreated.

By default, only the same identity can resume or take over the retained session:
the same username with authentication, or the same browser owner cookie without
authentication. Another identity is rejected because the single session slot is
occupied. To allow another browser or account to take over:

```python
app.start(passthru=True, permissive_takeover=True)
```

`permissive_takeover` defaults to `False` and requires `passthru=True`; otherwise
`True` raises `ValueError`. It preserves the existing application state and closes
the previous connection with `Session taken over`. Authentication is still
required when configured. Only one connection is active; this does not enable
simultaneous clients. The CLI equivalent is `--passthru --permissive-takeover`.

Callbacks must not block the server event loop. Synchronous Web dialogs are
unavailable, and combining passthru with Landlock or Codex/Claude worker restart
is rejected. Runtime registrations and Options remain process-global; their
previous values are restored when the server closes. The default isolated
worker mode is unchanged.

### Shared State with PySide6

The [dual_backend example](../examples/dual_backend.py) opens PySide6 on the
main thread and runs Web in a background `Thread` with `passthru=True`, in the
same process. Both applications use one `State` object and the same UI declarations.

```shell
python -m pip install 'QPUIQ[pyside6,web]'
python -m PUI.examples.dual_backend
```

When running from a source checkout, [build the browser assets](#rebuilding-browser-assets)
first (`make web-build`, or `.\build.ps1` on Windows). Published packages include them.

The example binds to `127.0.0.1:0`; the OS assigns a free port. Open the URL printed
by the server, then edit the text, increment the counter or move the pointer over
the curve in either UI. The shared cursor is a sample index rather than a pixel
position, so each Canvas can map it to its own size and coordinate system.

Startup waits for `web_app.wait_started()` before starting the desktop event loop.
Closing the desktop window calls `web_app.stop()` and joins the Web thread.
The example demonstrates shared State; it does not provide synchronization for
simultaneous edits from both threads.

The optional `--wstunnel-url`, `--wstunnel-token` and `--wstunnel-bind` arguments
expose the Web UI through a [reverse tunnel](#reverse-tunnel). The relay listener
defaults to `tcp://127.0.0.1:0` when `--wstunnel-bind` is omitted.

## Application titles

`Application(title='')` sets the initial browser page title. The login page
shows that title as its heading, or `PUI` if empty, and uses
`Sign in · <title>` as its browser title. `Window(title=None)` inherits the
application title or `PUI` fallback. An explicit Window title overrides the
page title after rendering, including `''` to clear it; the login page keeps
the application title. The cookbook uses `PUI Cookbook`.

Web forwards the launcher's title to the gateway and workers without changing
the no-argument application factory contract. With the generic CLI, use
`--title "My app"`; a title set only in the deferred worker constructor becomes
visible after the first render, while the gateway/login page initially uses PUI.
HTML titles are escaped. Subsequent renders use Window.title when explicitly
set; changing it back to None restores the application title/PUI fallback.

## Binding and reverse proxies

`bind` replaces `host`/`port` (CLI `--bind` replaces `--host`/`--port`). Accept
`localhost:8866`, `127.0.0.1:8866`, `[::1]:8866`, or a Unix socket path such as
`/run/pui/pui.sock` or `./pui.sock`; a `pathlib.Path` explicitly denotes a socket.
TCP ports range from 0 (OS-assigned) through 65535. Unix socket binds are available
on Linux/macOS, and listen without a TCP port. Parent directories must already
exist; filesystem permissions and umask govern proxy access. `socket_mode=None`
leaves the socket permissions unchanged; an integer such as `0o666` applies that
mode after binding and before serving. Values from `0` through `0o7777` are
accepted; TCP ignores the option. Directory permissions still apply. Existing entries
are never replaced. Shutdown removes only this process's socket; stale sockets
left by a forced termination require explicit removal after checking ownership.
Windows supports TCP binds only. The cookbook/Make default is `localhost:8866`,
overridable with `--bind` or `WEB_BIND`. `mount_path` configures upstream routes independently of bind.

```shell
make web WEB_BIND='127.0.0.1:8866'
make web WEB_BIND='[::1]:8866'
make web WEB_BIND='./pui.sock'
```

For an explicit Unix socket mode in a Python launcher:

```python
MyApplication().start(bind="/run/pui/pui.sock", socket_mode=0o666, mount_path="/pui")
```

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

Public endpoints are page-relative, so the gateway does not need a public
`base_url`. `mount_path` controls upstream routes only and remains independent
of the browser-visible path. Use `mount_path="/"` if the proxy strips the entire
public prefix, or any other mount if the proxy preserves/maps requests to it.

For example, exposing an upstream mounted at `/` under `/demo/`:

```nginx
location = /demo { return 308 /demo/; }
location /demo/ {
    proxy_pass http://127.0.0.1:8000/;
    proxy_cookie_path / /demo/;
    proxy_http_version 1.1;
    proxy_set_header Host $http_host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

Normalize the public entry URL to end in `/`. Cookies use the upstream mount
as their Path; rewrite it to the public prefix when they differ, including on
login/logout responses. This keeps multiple PUI apps on one origin isolated.
Login, logout and renew redirect using `../` from their `pui/*` endpoints.
Failed-login pages adjust their asset/form links relative to that endpoint.

`base_url`, `--base-url` and `WEB_BASE_URL` have been removed. Existing deployments
that used them to select upstream routes should set `mount_path`, `--mount-path`
or `WEB_MOUNT_PATH` explicitly; deployments that used them only to describe a
proxy's public prefix now configure that prefix solely in the proxy.

Chrome cookbook tests pass through both prefix-preserving HTTPS/WSS and a
prefix-stripping nginx proxy; `tests/web_proxy.py` reproduces the latter using
existing nginx, Node and Playwright/Chrome installations; see
[Development and validation](#development-and-validation) for commands.
For HTTPS terminated at a proxy with an HTTP upstream, preserve the public Host
and overwrite `X-Forwarded-Proto` with the original `http` or `https` scheme
(nginx: `proxy_set_header X-Forwarded-Proto $scheme;`). HTTPS Origin validation
and Secure cookies use this header when it comes from a trusted proxy. The browser resolves the relative WebSocket URL as WSS.
`trusted_proxies=None` trusts loopback (`127.0.0.0/8`, `::1/128`) and Unix sockets.
A string or list of IP addresses/CIDRs and the literal `"unix"` replaces those
defaults; `[]` disables all header trust. Unix peers are identified by the
transport socket's AF_UNIX family, never by a client-supplied header.
For a proxy on another machine or container network, for example, use
`trusted_proxies=["192.0.2.10", "2001:db8::/64"]` on `start()`, or
`make web WEB_TRUSTED_PROXIES="192.0.2.10 2001:db8::/64"`.
The immediate socket peer decides trust; forwarded client addresses and hosts
are ignored. Trusted peers must send one `http` or `https` value; malformed or
duplicate headers return HTTP 400. Untrusted peers' protocol headers are ignored.
CLI `--trusted-proxy` is repeatable; `--no-trusted-proxy` disables trust. Make
uses space-separated `WEB_TRUSTED_PROXIES`, defaulting to the loopback networks and `unix`;
an empty value disables trust. The request Host and effective scheme determine
the Origin used for validation; public endpoints inherit the browser origin.
`Application.start()` and `run()` accept independent `allow_hosts=None`
(equivalent to `["*"]`). Supply a list of exact host names to restrict all HTTP
routes; matching ignores case and request ports, and accepts bracketed IPv6.
An empty list denies all hosts. CLI `--allow-host` is repeatable, and Make uses
`WEB_ALLOW_HOSTS="example.com localhost"`. Host entries contain no scheme, path or
port; partial wildcards are not supported. WebSocket Origin validation is
unchanged by `allow_hosts`, including its default `"*"`.

## Reverse tunnel

Install the Rust version of [erebe/wstunnel](https://github.com/erebe/wstunnel/releases)
and put `wstunnel` (`wstunnel.exe` on Windows) on PATH. No extra Python dependency
is needed. Enable the tunnel with a server URL and shared-secret token:

```python
MyApplication().start(
    bind="127.0.0.1:0",
    wstunnel={
        "url": "wss://relay.example.com/_puitunnel",
        "token": "your-secret-token",
    },
)
```

PUI starts a managed `wstunnel client` process with
`-R tcp://127.0.0.1:0:<PUI-host>:<PUI-port>` after binding its TCP listener.
The relay allocates the remote port automatically; its actual number appears in
**the relay's INFO-level server log**, not the PUI/client log. wstunnel does not send the
allocated listener address back to the client, so PUI cannot print a remote URL.
The default remote listener is loopback-only: a reverse proxy on the relay can publish
it as an HTTP endpoint. HTTP and WebSocket traffic use the same TCP tunnel.

For a stable remote entry point, the relay's `--restrict-config` can allow the
requested port `0` and map it to a fixed port with `port_mapping: [0:8080]`.
Upstream caches reverse listeners by requested bind address; multiple clients
requesting `127.0.0.1:0` on the same relay may share a listener. Use separate
relay instances or distinct remote binds for independent applications.

Set optional `wstunnel["bind"]` to choose the **relay-side listener**.

### Direct TCP access

On the relay, start wstunnel on TCP port 8081:

```shell
wstunnel server --restrict-http-upgrade-path-prefix your-secret-token ws://0.0.0.0:8081
```

On the machine running PUI, request a fixed public TCP listener on the relay:

```python
MyApplication().start(
    bind="127.0.0.1:0",
    wstunnel={
        "url": "ws://relay.example.com:8081",
        "token": "your-secret-token",
        "bind": "tcp://0.0.0.0:8080",
    },
)
```

Once the client connects, open `http://relay.example.com:8080/` in the browser.
Port 8081 accepts the tunnel connection; port 8080 serves PUI through that tunnel,
including its WebSocket connection. Allow both ports through the relay's firewall.
`0.0.0.0` makes the reverse listener reachable from other machines; use
`tcp://127.0.0.1:8080` to keep it accessible only on the relay.
This example uses plain WebSocket transport and HTTP, without TLS or nginx.

### Unix socket behind nginx

```python
MyApplication().start(
    bind="127.0.0.1:0",
    mount_path="/",
    wstunnel={
        "url": "wss://relay.example.com/_puitunnel/",
        "token": "your-secret-token",
        "bind": "unix://myapp/UUID",
    },
)
```

The default is `tcp://127.0.0.1:0`; a fixed TCP port such as
`tcp://127.0.0.1:8080` and IPv6 such as `tcp://[::1]:8080` also work.
`unix://myapp/UUID` uses a path relative to the relay process working directory.
With `/run/wstunnel` as that directory, the socket is
`/run/wstunnel/myapp/UUID`; nginx uses this resolved absolute path below.
The relay must support Unix sockets. Socket paths cannot contain `:`.
PUI appends its local TCP destination, producing
`-R unix://myapp/UUID:<PUI-host>:<PUI-port>`.
This setting is separate from `.start(bind=...)`, which selects PUI's local listener.

Set `wstunnel["wstunnel"]` to an executable path, for example
`"/opt/tools/wstunnel"` or `"C:/Tools/wstunnel.exe"`. If omitted, PUI executes
`wstunnel` directly, relying on the system PATH lookup. The value is passed as
one executable argument, not interpreted as a shell command.

PUI combines the URL path and token into `/_puitunnel/<token>/events`, passing
the prefix through the child process environment. No global environment variable
is needed; an inherited `WSTUNNEL_HTTP_UPGRADE_PATH_PREFIX` is overridden for that
child only. The token is not passed on the command line.

On the relay, save this restriction configuration as
`/etc/wstunnel/restrictions.yaml`:

```yaml
restrictions:
  - name: "PUI Unix sockets"
    match:
      - !PathPrefix '^your-secret-token$'
    allow:
      - !ReverseTunnel
        protocol: [Unix]
        unix_path: '^myapp/[A-Za-z0-9_-]+$'
```

Use this allowlist to prevent clients from creating socket files at arbitrary
locations on the server. A relative path alone does not provide that restriction.
The anchored `unix_path` pattern allows only a single socket name under `myapp/`;
absolute paths, `../` traversal and additional subdirectories do not match.
Keep `myapp/` a server-managed directory, not a client-controlled symlink.
This rule allows only reverse Unix tunnels for the matching token, with no
forward tunnels or reverse TCP listeners. The path prefix is the token after
nginx strips `/_puitunnel/`; replace the example token in both the client and
YAML, escaping any regex metacharacters in the YAML pattern.
See the [upstream restriction format](https://github.com/erebe/wstunnel/blob/main/restrictions.yaml).

The relay has two separate listeners: the wstunnel server accepts tunnel
connections on TCP port 8081, while this client's reverse listener is the Unix
socket `/run/wstunnel/myapp/UUID`. Prepare the directory with permissions that let
wstunnel create sockets and nginx connect to them, then start the relay with the
restriction file and a fixed working directory:

```shell
mkdir -p /run/wstunnel/myapp
cd /run/wstunnel
wstunnel server --restrict-config /etc/wstunnel/restrictions.yaml ws://127.0.0.1:8081
```

For systemd, set `WorkingDirectory=/run/wstunnel` to preserve the same path
resolution, and arrange for the socket directory to exist before startup.

Inside nginx's HTTPS `server` block for `relay.example.com`, configure both routes:

```nginx
# PUI's wstunnel client connects here to establish the tunnel.
location ^~ /_puitunnel/ {
    proxy_pass http://127.0.0.1:8081/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_read_timeout 3600s;
    proxy_send_timeout 3600s;
}

# Browsers reach PUI through the reverse Unix listener created by that client.
location = /myapp/UUID { return 308 /myapp/UUID/; }
location ^~ /myapp/UUID/ {
    # Consider using auth_request to protect access to the tunneled PUI service.
    # https://nginx.org/en/docs/http/ngx_http_auth_request_module.html
    proxy_pass http://unix:/run/wstunnel/myapp/UUID:/;
    proxy_cookie_path / /myapp/UUID/;
    proxy_http_version 1.1;
    proxy_set_header Host $http_host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 3600s;
    proxy_send_timeout 3600s;
}
```

The first route removes `/_puitunnel/`, so wstunnel receives `/<token>/events`.
A root tunnel URL connects directly using the token as the prefix.

Once the PUI client connects and creates the reverse listener, open
`https://relay.example.com/myapp/UUID/`. The second route sends HTTP and WebSocket
traffic to the **same Unix socket resolved from `wstunnel["bind"]`**, which forwards
it through the tunnel to PUI's local TCP listener. Its `:/` suffix replaces the
public `/myapp/UUID/` prefix with `/`, matching `mount_path="/"`; the cookie rewrite
keeps cookies scoped to the public prefix. The socket path and public URL path
are independent. See nginx's [Unix-socket `proxy_pass` syntax](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_pass).

`url` and `token` are required; `bind` and `wstunnel` are optional. No other keys are accepted. The URL uses `ws://` or `wss://`, optionally
with a routing path, without credentials, query parameters or a fragment. Path
segments and tokens use URL-safe letters, digits, `.`, `_`, `~` and `-`;
`.` and `..` segments are rejected. PUI enables server certificate verification
for TLS.

The tunnel process stops when the Web server shuts down. Normal session workers
and `passthru=True` are supported. Network reconnects are handled by wstunnel;
if its process exits, PUI logs the exit and keeps serving locally. The local PUI listener must use TCP; the relay listener can use TCP or a Unix socket. Configure authentication, the upstream `mount_path` and host/proxy options
as with other reverse proxies. Public URLs remain relative to the entry page.

## Authentication

`auth(username, password)` must return a dictionary with boolean `auth` and `ai`
permissions. `auth=True` admits login; `ai=True` additionally permits AI access.
Missing fields default to False; non-boolean fields and non-dictionary results
(including bare True) deny login. `auth=False` always denies login, even with
`ai=True`. `auth=None`
leaves access open. The callback stays in the gateway and is never pickled into workers.
Failed credentials start an account-specific cooldown of 1, 2, 4, 8, 16,
then 30 seconds (capped). Success clears the counter. During cooldown or an
in-flight validation, further attempts for the same exact username return HTTP
429 with Retry-After without invoking auth. Different cookies do not bypass it.
Usernames are not normalized by PUI; aliases handled by custom auth may have
separate counters. Failure records expire after 15 minutes of inactivity or
server restart. At most 4,096 account records are retained; when full, new
accounts receive HTTP 503 rather than evicting active cooldowns. This limits
repeated guesses per account. Additionally, each source may start at most 10
credential validations in a rolling 60-second window; excess receives 429 with
Retry-After. Successful and failed validations both count. The source table is
bounded to 4,096 active sources; if full, unseen sources are temporarily refused.
Direct peer IP is used unless the peer is a trusted proxy. For trusted proxies,
X-Forwarded-For is walked right-to-left, skipping trusted proxies and selecting
the first untrusted address. Malformed headers fall back to the direct peer;
Unix sockets without a usable forwarded address share one bucket. Untrusted
peers cannot select their source by supplying forwarding headers.

Synchronous callbacks run in a thread; async callbacks are awaited. Exceptions
and other return values deny access. The cookbook supplies
the following options to `start()`:

```python
Cookbook().start(
    bind="localhost:8866", mount_path="/pui",
    auth=lambda username, password: {"auth": {"test": "test123", "dev": "dev123"}.get(username) == password, "ai": username == "dev"},
    auth_prompt="User: test/test123 · Developer (AI): dev/dev123",
)
```

Custom authentication is configured in the Python launcher; the generic Web CLI
remains open without a callback. Login is checked before creating a worker.
Optional `auth_prompt` is a string
displayed below the login title as escaped plain text, preserving line breaks.
`None` or an empty string hides the prompt; it has no effect without `auth`.

The main application page and login pages (including failed sign-in responses)
send `Content-Security-Policy: frame-ancestors 'none'` and
`X-Frame-Options: DENY`. Browser framing is disabled even for the same origin,
with or without authentication. Open the application as a top-level page.

When auth is configured, the entry URL serves a login form until authorization
succeeds. Only successful login issues the signed `pui_owner` cookie; it is
HttpOnly, SameSite=Lax, scoped to the public base path, Secure under HTTPS and
has no persistent browser expiry. Server-side authorization expires after
`auth_idle_timeout=4200` seconds without processed user input or
`auth_max_age=86400` seconds after login, whichever comes first. Both start()
options require finite positive seconds. Shared tabs use the same owner activity
clock. Render/ACK/heartbeat traffic does not refresh it; processed widget/binding
input and AI prompt/answer/cancel actions do. Active operation cannot extend the
absolute maximum age. It stores no credentials. This browser authorization
is independent of worker TTL/resume IDs: resume, renewal and worker crashes keep the login.
Expiry closes application connections (code 4004) and clears AI conversations,
but detaches rather than terminates workers: their ordinary session_ttl starts.
The login record stores the exact successful username server-side. Reauthenticating
in the same browser with the same username rotates the cookie, invalidates the old
token and transfers retained workers to the new owner. The resume marker remains
stable, preserving per-tab resume IDs; worker State survives while the worker is
still retained. Different usernames do not inherit workers. This is not cross-device
session discovery; aliases/case variants are distinct. AI permissions are refreshed
from the new auth result. Logout deliberately does not preserve workers.

Logout revokes the cookie and ends every worker owned by that
browser login, including active tabs and TTL 0 workers. A gateway restart changes its signing key and requires login
again. `pui_login` is a separate-purpose signed CSRF cookie, removed on success;
POST also rejects foreign Origin headers. Login pages are not cached, credentials
are not echoed/logged, and forms are limited to 8 KiB. Public packaged assets
remain accessible; unauthenticated WebSockets return 403 and images return 404.
Logout uses a native POST form with a cookie-bound CSRF token, Origin validation
and a 1 KiB body limit. The gateway tracks valid owner tokens so revoked
cookies cannot reconnect or read images. It deletes both cookies and redirects
to the entry URL. Auth requires another login; anonymous apps issue a fresh cookie.

With `auth=None`, at most 1,024 anonymous owner records without a worker are
kept in an LRU cache. A valid cookie lookup refreshes its position. Owners of
starting, active or retained workers are protected until their last worker is
reaped, including `session_ttl=0` sessions; worker capacity remains governed by
`max_sessions`. An evicted cookie cannot attach a WebSocket or access images;
reloading the entry URL obtains a fresh anonymous cookie. Authenticated owner
records are excluded from this cache; expired records may remain for reauthentication
but cannot authorize requests. Logout or gateway shutdown removes them. The login form's `pui_login` CSRF cookie requires no owner record.

## Sessions and reconnection

There is one worker per exact username when auth is configured, or per browser
owner when auth is absent. New tabs/devices logged in as the same username attach
to that worker, even without a saved resume ID. The newest connection takes over:
the old socket closes with code 4005 and displays a takeover notice without
automatic reconnection. Reloading the old page can explicitly reclaim it. State
and PID are retained; connection epochs and pending browser drafts are replaced.
Only the current connection's owner can access that worker's resources or renew it.
Logging out or expiring a displaced browser owner does not stop the new owner's worker.

`session_ttl=900` retains the worker/State after its active connection disconnects.
`session_ttl=0` (CLI `--session-ttl 0`) means no disconnect expiry, replacing
the former immediate-expiry behavior. Retained workers still count toward
`max_sessions`. Renew session reaps the selected worker; Logout reaps all workers
for that browser owner. Explicit application quit, worker failure and server
shutdown still clean up workers.

Reconnecting changes the connection epoch and sends a full snapshot without
replaying callbacks. The connection banner hides after the view synchronizes,
without reserving layout space; connection loss or view recovery shows it again.
With a saved per-tab session ID, reload or recoverable connection loss waits for
a choice before connecting:

| Authentication | Actions |
| --- | --- |
| Configured | **Resume session** / **Renew session** / **Logout** |
| `auth=None` | **Resume session** / **Renew session** |

Saved IDs are scoped to the current browser owner and gateway signing key.
Loading the entry page after a gateway restart or a different-owner login discards stale
IDs and connects directly, without offering to resume an inaccessible worker.
Same-browser reauthentication preserves the marker. First visits connect directly
and can take over the same username’s existing worker. Resume retains Python state when available;
expired sessions start fresh. Renew session clears the tab's resume ID, ends its
selected worker through a CSRF-protected HTTP POST and returns to the entry URL
to start fresh. It keeps the login cookie and other session IDs. If the selected
ID still has a connection in another tab, that connection closes with code 4003
and displays Session renewed with a Continue link.

Logout clears the login cookie and all workers for that owner. Other connected
tabs clear their UI and resume IDs on WebSocket close code 4001 and display
Logged out with a Continue link; another login is required. Separate browser
owners are unaffected.

The old UI is inert until the new snapshot applies, and unsent edits/actions are
discarded. Resume takes over an active connection belonging to the same username
(or anonymous owner); foreign-user resume IDs are rejected.
Failed connection attempts retry the chosen option; another loss after connection
asks again.
Edit sequence deduplication restarts with each connection epoch, so retained
editors accept new input immediately after reconnecting or reloading.

## State bindings

State object IDs identify registered attribute bindings;
custom scalar bindings use their binding object ID. List keys are safe integers;
dictionary keys are strings or safe integers (integer `1` and string `"1"` remain
distinct). Structural list edits revoke all bindings on that list. Dictionary
deletion/recreation revokes only that key; ordinary value writes retain tokens.
These checks also reject old input callbacks before the next redraw. Mutate
containers through State methods; editing the original Python container directly
bypasses reactive notification and lifetime tracking.
Shared bindings retain one source registration and separate editor attachments.
Removing/rebinding an editor invalidates old actions; re-registering the same
Python object creates fresh tokens. Independent subviews and TimelineView queue
redraws on the worker loop. Shutdown clears queued views and registrations and
ignores late timer requests.

## URL Options and State refs

The browser parses `#name=value#other=value` after WebSocket `ready` and sends
the values through the gateway to the session worker. Percent-encode each name
and value, for example `#example.text=hello#example.count=123`.
Options values are always strings: `123`, `true`, `null`, CSV and JSON text are
not parsed or converted. Empty values are allowed. Duplicate names use the last
value. Malformed entries or invalid percent encoding are skipped with a warning;
messages still obey the existing size and structure limits.
Login, renewal and logout preserve the fragment across their form navigation;
the fragment is not included in the HTTP request.

The worker fills the same `PUI.Options` dictionary before importing and creating
the application and running its first `setup()`/`content()`. The supervisor does
not receive these values in its own Options. Application code chooses what to
read, how to validate it and in what order to initialize State:

```python
import PUI
import PUI.web as UI

class Example(UI.Application):
    def setup(self):
        self.state = UI.State()
        try:
            self.state.count = int(PUI.Options.get('example.count', '0'))
        except ValueError:
            self.state.count = 0

    def content(self):
        with UI.Window():
            UI.TextField(self.state('count').ref('example.count'))
```

The application converts and validates strings itself (an integer here). It can
also split CSV or parse JSON explicitly when needed. Options are untrusted URL
input, not automatic State writes or a new path to arbitrary
Python attributes. Read them in worker initialization, not in a launcher instance
constructed before `start()` in the supervisor. On resume, Options refreshes to
the connecting URL but the existing application is retained: setup is not rerun
and State is not restored from the hash. Its current subscriptions publish back
to the URL. Manual hash changes after connection do not write State or refresh
Options. Renew session creates a worker and uses the current hash on startup.

`state(key).ref(name)` returns the binding. Declare it in `content()` to subscribe
the browser to that value, independently of the node-ref registry. Existing State
dependency tracking triggers redraws; no extra change callbacks are installed.
After sync, the worker batches the current subscriptions. Each view rebuild
replaces its own declarations; independent subview redraws preserve other views'
subscriptions. Removing a declaration or destroying a view stops its updates,
but does not delete the last value from the URL. Repeated names use the last
published declaration, so use fixed namespaced names to avoid accidental overlap.
JSON-compatible scalars, lists and dictionaries are supported, including nested
State lists/dictionaries. Non-serializable values are skipped with a warning.
String values are written without JSON quotes; other values use JSON text.
All values become plain strings in Options when the URL is read on a connection.

For each received batch, the browser compares the resulting text with the
URL-decoded strings. Only changed entries are merged
into the current hash. Unsubscribed entries and existing name order are retained;
new names are appended. One `history.replaceState` updates the URL per changed
batch, preserving `history.state`, path and query without adding a history entry.
There is no hash-change feedback into State. Do not subscribe passwords or other
secrets: these values are visible in the address bar and copied URLs.

The cookbook subscribes its selected page with
`self.state('page').ref('cookbook.page')`. For example,
`http://localhost:8866/pui/#cookbook.page=Button` opens the Button example
in a new session. Selecting an example updates that URL value; missing or unknown
page names fall back to the first example. Resume keeps the existing selection.
URL synchronization is Web-only; other backends, including Pyodide, currently
use a no-op `state_ref_publish(name, value)` by default.

Replace `PUI.web.state_ref_publish` to customize publication for all Web views.
The callback runs synchronously for each `.ref()` declaration during `content()`
and receives the original Python value, before JSON serialization or batching.
An override replaces URL publication unless it calls the saved default:

```python
import PUI.web as UI

default_publish = UI.state_ref_publish

def publish(name, value):
    print(name, value)
    default_publish(name, value)

UI.state_ref_publish = publish
```

Configure it in the application module imported by the worker, or in `setup()`;
changing only the supervisor's module does not configure spawned workers.
Overrides apply to existing and nested views in that backend and are independent
of other backends. Rebuilds may publish unchanged values; the default Web path
still batches subscriptions and suppresses unchanged wire messages. See
[the common reference](Reference.html#state-refs) for the callback contract.

## Layout and sizing

The shared [container precedence rule](Layout.html#container-precedence) applies:
the parent determines final geometry and interprets child sizing requirements
according to its layout policy.

Web linear layouts compute expansion from the parent: HBox shares free width,
VBox/Window shares free height. On that main axis, only siblings at the highest
nonzero priority grow: positive weight (5), shrinkable widgets such as Canvas,
Text and enabled Scroll axes (4), a container's own axis (3), inherited child demand (2), then its cross
axis (1). Static controls have priority 0; TextField expands only horizontally.
HBox's base X/Y priorities are 3/1, VBox's are 1/3. Equal unweighted priorities share
extra space; positive weights divide space proportionally, subject to minimum
sizes. `weight=0` keeps the preferred main-axis size without growing or
collapsing it. Numeric weights do not propagate beyond their immediate container. Visible child demand at priority 2 or higher promotes an otherwise lower-priority container to 2 on that axis, recursively. Fixed-axis dimensions and main-axis weight=0 block inherited expansion.

Web HBox defaults to vertical middle alignment; VBox defaults to horizontal left
alignment. Compact controls and children with an explicit cross-axis size are
centered. Children that support cross-axis expansion and have no explicit size
on that axis still stretch to fill it; weight alone does not stretch that axis.
Explicit Canvas width/height disables automatic expansion only on that axis; a positive main-axis weight can still
grow it beyond its explicit minimum. Other explicit Web dimensions retain
their existing CSS size/minimum behavior. Nested containers can shrink to fit
the viewport; Scroll content keeps its natural extent on its scrolling axis.
Hidden pages do not compete for space. Reconciliation recomputes sibling sizing
after weight changes, removal and reparenting while retaining DOM elements.
Grid/Stack children retain CSS Grid sizing. Chrome desktop/mobile viewport
checks are in `tests/web_sizing.cjs` and `tests/web_layout.cjs`; unresolved
specification differences are recorded in [the Web plan](https://github.com/buganini/PUI/blob/main/notes/web-progress.md).

## Widgets

### Window and text display

Button uses `.click()` and `disabled=False`. Label click handlers are keyboard
accessible. Text displays literal preformatted text. `Html(text, selectable=False)`
renders a trusted HTML fragment in a Shadow DOM, with native browser formatting,
links, images and fragment-local CSS. PUI font/color styles inherit into the
fragment; background, padding and layout apply to its host. Unchanged HTML keeps
its DOM during unrelated updates, and changed HTML replaces the fragment.
This API does not sanitize HTML: escape untrusted values before interpolation.
Shadow DOM isolates styles and IDs, not script privileges. URLs resolve relative
to the page, and embedded controls are not PUI bindings. Use this for content,
not script initialization (`innerHTML` does not run inserted script elements).
Markdown remains unimplemented. Web and Pyodide share this renderer.

Window fills the available browser viewport; desktop initial `size` is
ignored rather than converted to CSS dimensions. `.size()` reports the actual
measured content area. Initial `maximize` has no OS-window
effect. `icon` and initial `fullscreen=True` log warnings and are ignored so
shared desktop declarations can render; these features remain unimplemented.

Nested/multiple Windows, pointer/key handlers and unsupported input/change handlers raise
explicit server errors. Invalid dimensions/fonts are rejected before publication.

Desired `.layout(width=..., height=...)` dimensions stop automatic expansion on
those axes. `.layout(minWidth=..., minHeight=...)` sets CSS minimums without
changing expansion priority. Desired dimensions can also provide minimum hints;
positive weight and Grid allocation can still expand a child beyond its desired
size. An unspecified Canvas axis retains priority 4.

### Text inputs

TextField uses `model`, optional
`edit_model`, and keyword-only `placeholder=None`. With only `model`, typing stays
local until Enter/blur; input events are sent only for `edit_model` or `.input()`.
Drafts survive input-only updates; Enter/blur commits reconcile with the authoritative value,
including rejected edits and empty patches.

MaskedField uses `<input type="password">` with the same draft, IME,
Enter/blur and retention handling as TextField. Masking changes display only;
bindings and callbacks still receive the original text. Text inputs retain
their native height in HBox and column containers; explicit layout height/weight
still overrides sizing. Removed styles and dimensions restore native defaults.

### Selection controls

Checkbox supports scalar booleans, list membership and dictionary keys, using
native inputs; RadioButton uses native radio inputs grouped by model and parent.
Both accept keyword-only `disabled=False`; `True` disables the native input and
rejects incoming actions while still reflecting programmatic model changes.
Their `.click()` callbacks run after model updates. ComboBox uses a native select
when read-only, and input + a custom candidate listbox when editable. Enter/blur commits editable
text: an exact label match selects the first matching option; otherwise it writes
free text and index `-1`. `.change()` receives the selected index or free text.
Item values remain Python values and pass through existing Binding conversion/
validation. The current wire value domain still applies to exposed models and
options. Optional ComboBox models retain internal selection/text, and `disabled=True`
disables both selection and typing. Rebinding or changing choices invalidates
old selection/edit tokens. Pending local selections and newer typing survive
older server replies; committed text reads back the setter's authoritative value.

`ComboBox(autoexpand=True)` automatically opens candidates while typing.
The browser displays the application-declared ComboBoxItem children without filtering.
Use `edit_model=state("query")` to receive typed text directly in application State
that determines the candidates; `.input(callback)` remains available and runs after
the draft binding write. `index_model`, `text_model` and `edit_model` are keyword-only.
Draft writes do not commit text_model;
selection and Enter/blur retain their existing commit behavior.
The input retains focus while candidates update; arrow keys move the highlight,
Enter or a click accepts it, Escape closes the popup, and Tab commits and moves
focus. Typing never inserts the first candidate. Browser composition events
suspend suggestions during IME composition. Candidate clicks commit once without
an earlier blur submission. Selection preserves the existing first-exact-label
mapping rule, including duplicate labels. The choices button lists all options,
also with `autoexpand=False`; false disables suggestions while typing.
Pyodide uses the same renderer. No third-party popup dependency is required.
See the [autocomplete acceptance criteria](Reference.html#autocomplete-acceptance)
for focus, keyboard, composition, synchronization and accessibility validation.

The [ComboBox cookbook](../cookbook/combobox.py) demonstrates `tai tok`, which
matches both Taipei and Tokyo. Selecting a label commits its value to a separate
State binding; unmatched free text commits on Enter/blur. `editable=True` is
required; the default renders a non-editable select.

### Views and Tabs

Web Views and Tabs share the optional model and `ref(name).select(key)` binder contracts in the
[common reference](Reference.html#views).
Inactive pages remain in the DOM, preserving local drafts, cursor and scroll
positions; hidden pages are excluded from keyboard traversal. Tabs use explicit
IDs or label fallback (first match), and support all four header positions,
native buttons, arrow/Home/End navigation and linked tab/tabpanel ARIA roles.
The scrollable header and padded content share a border; selected tabs have an
indicator facing the content, with a separate visible keyboard-focus outline.
East/West headers are vertical lists with upright text. Removed pages and rebound
models reject stale selection events.

### Scroll

Scroll supports `.scrollX()` / `.scrollY()` and `END`, retaining offsets across redraws and resize. Positive
values are offsets from the start, negative values from the end. Repeating the
same declaration preserves manual scroll; calling a mounted handle explicitly
issues a new request. End-relative offsets follow content growth, using native
ResizeObserver and scroll events without sending scroll traffic to Python.

### Splitter

`Splitter(vertical=False)` places panes side by side; `vertical=True` stacks
them. Drag a separator to resize its two adjacent panes, leaving other panes'
shares unchanged. Nested Splitters are supported. Hidden children do not receive
space or separators; empty and single-pane containers have no separator.

Pane ratios remain local to the browser across server redraws and Cookbook page
changes. Resizing the container preserves these ratios; changes to visible pane
order/count or orientation reset them to equal shares. Ratios are not serialized
to State and reset when the page is reloaded. Panes can shrink to one pixel;
use Scroll inside panes for content that should remain accessible at small sizes.

Separators can receive keyboard focus. Left/Right (horizontal layout) or Up/Down
(vertical layout) move the separator by 10 CSS pixels, or 50 with Shift.
Home/End shrink the preceding/following pane to its minimum. Pointer capture keeps
dragging active outside the separator. Chrome mouse and keyboard interactions,
retained panes, nested/vertical layouts and adaptive child sizing are tested;
real touch and other browser engines remain unverified. Pyodide shares this
renderer; combined CDN-runtime verification is still pending.

### Grid and ProgressBar

Grid uses CSS Grid with zero-based row/column and
positive rowspan/columnspan (default 1); placement requires a Grid parent.
ProgressBar uses native HTML progress, clamps values to its nonnegative maximum,
and displays indeterminate progress when maximum is zero. Both cookbook examples
are enabled.

### Stack

Web uses one CSS Grid cell shared by all children. DOM order controls paint and
native hit-testing order; keyed reorder/removal retains the surviving elements.
Use the usual `.layout()` dimensions/weight and `.style()` modifiers. The Web
Stack cookbook and Chrome overlap, reorder and pointer-target checks are enabled.

### TimelineView

Web queues timer redraws on the worker event loop; the TimelineView cookbook is
enabled and Chrome checks verify live timestamp updates. Removed timers stop and
late shutdown callbacks are ignored.

## Canvas

Web and Pyodide reuse geometry fill/stroke/width settings within each frame,
avoiding full Canvas 2D state save/restore for individual geometric primitives.
Changed settings reset to frame defaults before native assignment, so ignored
invalid colors or widths cannot inherit the previous shape's styles. Text and
images still isolate transforms, clipping and opacity with save/restore.

Web records line/polyline/cubic/polygon/rectangle/ellipse and text commands in
Python, then replays a complete frame through Canvas 2D. Painting waits for
positive visible browser dimensions; `pixel_density` is devicePixelRatio.
Resize, DPR changes, hiding/showing and context restoration invalidate the old
measurement/bitmap. DOM ACKs do not wait for drawing. A truthy painter return
requests another frame only after an accepted presentation acknowledgement;
duplicate ACKs cannot grant extra credit. Changes while awaiting presentation
coalesce into the next paint, while other widgets can keep updating.

### Command differences

Web transports changed Canvas lists with one prefix/suffix splice against the
last acknowledged render's `frame_rev`. At least eight unchanged commands must
be reusable; otherwise it sends the complete frame. The browser checks the
base revision, prepares a new full command list, then clears and redraws it.
Unchanged command records are shared internally without copying or mutating the
previous list. Initial load, reconnect, recovery and measurement changes send
complete frames. Invalid bases use snapshot recovery; retries are deduplicated
by render revision. Reconstructed state is checked against the same command,
item, depth and serialized-byte budgets. This reduces transport/encoding work;
the Python painter and full browser repaint still run.

### Performance measurements

HeavyCanvas shows completed-render FPS in a browser-local overlay. Enable
**Run continuously (FPS)** to keep the normal painter/Canvas ACK pipeline busy.
Also enable **Full-frame changes** to change every drawing command's color each
frame, forcing the diff to choose `put_canvas` rather than a reusable prefix/suffix.
The chart uses a subtle 16-step blue-channel tint cycle; source data and geometry
stay unchanged. This tests full command transmission, not incompressible data:
Zstandard can still reuse compression history.
`Canvas(..., show_fps=True)` counts successful Canvas replay completions, updates
about twice per second and retains the last reading while idle. It does not measure
physical screen presentation or request latency, and adds no network messages.


Run server-side profiling with:

```sh
env/bin/python tests/web_canvas_benchmark.py 30000 --moves 20 --warmup 3
```

The default is 1,000 samples; accepted counts match the Web HeavyCanvas menu.
The script compares identical seeded hover frames at 900 × 720 using full-frame
and delta encoding. Each encoder keeps its own level-3, 4 MiB Zstandard stream.
Warm-up frames update both compression histories but are excluded from medians.
Data generation and the initial full frame are outside the measured samples.

JSON output includes runtime versions, painter/command recording, snapshot
excluding painter, offer/indexing, diff, and MessagePack-plus-compression times,
as well as full/delta encoded sizes. These are server-side stage measurements,
not end-to-end latency: they exclude browser decompression, MessagePack decoding,
Canvas replay, network and display presentation. Run locally for current numbers
rather than relying on timings from earlier implementations.

### Drawing errors

Canvas arguments are recorded without type/range validation. The browser invokes
Canvas 2D directly; if one command throws, it logs the Canvas ID, command index
and error with `console.warn` and continues with the next command. Text/image
context changes are restored; geometry starts a new path and applies its own
styles. Unknown opcodes are logged and skipped. Values that Canvas 2D
silently ignores (such as some NaN/Infinity arguments) keep that native behavior.
They do not cause a session failure or full-snapshot recovery.

Python painter exceptions and values that MessagePack cannot serialize still
fail on the Python side; render packing does not repeat its type checks. Frame
revisions, measurements, bitmap/resource budgets,
image URL ownership, render structure and untrusted browser input remain checked.

### Text and drawing limits

Text uses browser measureText with the Canvas CSS font-family/weight; `size` is
points (96/72 CSS pixels per point), or inherited font size when None. Nine
anchors refer to the measured multiline text block, rotation is around `(x,y)`,
and `w`/`h` clip from the block's top-left. Newlines are preserved without automatic
wrapping; unspecified clipping dimensions use the measured block. Browser font
metrics are not guaranteed pixel-identical to Qt. Stroke width zero is one
physical pixel; PUI RGB integers are converted to CSS colors. The recorder limits
frames to 300,000 commands, 20,000 points per command and 65,536 characters per text
command. The browser retains the frame command cap and limits bitmaps to 16,384 logical
pixels per dimension, DPR at most 8, 16,777,216 bitmap pixels per Canvas and
33,554,432 across the session. Protocol byte/item limits also apply.
Canvas images support HTTP resources, source rectangles, opacity and browser-side
crop/scale operations as described under [Image](#image). The Canvas cookbook
is enabled; Chrome tests cover drawing pixels, DPR, text clipping/rotation,
resize/visibility, intact replay, recovery and independent presentation credits.

### Shapely geometry

Web `drawShapely()` expands caller-provided points, lines, polygon rings and
geometry collections into display-list commands. Polygon interiors use an
even-odd compound path to preserve holes; empty geometries draw nothing. The
backend does not import Shapely or add it to the Web extra; the DrawShapely
cookbook uses its existing optional Shapely dependency. Path commands share
the 20,000-point limit across all their rings.

### Pointer and wheel events

The [HeavyCanvas cookbook](../cookbook/heavycanvas.py) accepts native pixel,
line and page wheel directions for zoom without converting them to angle units.

Web Canvas supports `.click()`, `.dblclick()`, `.mousedown()`, `.mouseup()`,
`.mousemove()`, `.mouseenter()`, `.mouseleave()` and `.wheel()`. Pointer events
carry local logical `x/y`, PUI `button/buttons` and `modifiers`, `pointer_id` and
`cancelled`. Capture preserves dragging/release outside the Canvas; lost capture
or cancellation emits a cancelled mouseup. Native Pointer Events determine
multi-button chord behavior. Mousemove callbacks retain every accepted sample in order, using the same
bounded action queue as other inputs. With no pending Canvas frame, the painter
runs immediately on refresh. While a frame awaits presentation ACK, state changes
only mark the Canvas dirty; the next paint uses the latest state after ACK.
Press/click commits a focused editor first. Disconnect discards queued actions.

Wheel events retain raw `delta_x`, `delta_y` and `delta_mode` (`pixel`, `line`,
`page`). Only pixel mode sets `x_delta=-delta_x`, `y_delta=-delta_y`; line/page
modes leave these at zero. `h_delta`/`v_delta` are always zero, with no invented
angle conversion. Registered wheel handlers prevent native page scrolling;
press/release/move handlers set `touch-action: none` on that Canvas. Removing
those handlers restores native defaults. The browser context menu remains
native. Pointer/wheel events use the existing bounded action queue; overflow remains explicit. Chrome tests cover capture,
outside release, cancellation, commit ordering, modifiers, raw wheel modes,
delayed-result input ordering, event boundaries and reconnect reset;
native touch devices and other browser engines still need validation.

## Image

Web `Image(path)` serves registered original files over HTTP with
`?mtime=<st_mtime_ns>`, `Cache-Control: private, no-cache`, ETag/Last-Modified and
conditional GET/304. Files are restricted to their browser owner and retained
session, respect public base URLs/proxy mount paths, and update their URL when
reconciliation observes a changed mtime. There is no filesystem watcher.
The native img element preserves aspect ratio inside explicit dimensions.

`ImageResource.load()`, `canvas.loadImage()` and `canvas.drawImage()` support
the existing source rectangle and opacity arguments. Resource `.crop()`/`.scale()`
return new descriptors; the browser performs chained operations after decoding.
Crop coordinates are integers; crop/scale dimensions are positive integers up to
16,384. Keep-aspect scaling fits within the requested rectangle. quality=0 disables
browser smoothing; other values enable high-quality native smoothing. Browser
format support and resampling determine results; Qt pixel equality is not promised.
No Pillow or server-side conversion is required.

Limits are 128 registered files/session, 64 MiB/file and 32 transforms/resource.
The Canvas cache permits 8 concurrent loads, 15 seconds/load, 128 decoded
source/transform entries, 16,777,216 pixels/decoded image and 33,554,432 cached
pixels/session. Decoded limits are checked after browser decoding. Canvas image failures
are logged and their commands skipped; other commands still draw. The frame is
acknowledged as failed without granting continuous paint credit; other controls
continue working. Removed resources retire after render consumers release
them; HTTP cache eviction remains browser-managed. See [HTTP image resources](web-api.md#http-image-resources).

## Table

Web uses a native HTML table for TableNode rows and BaseTableAdapter, with row/column
headers, scrolling, click/double-click callbacks and arrow-key navigation.
Read-only adapters (`editable(row, col) == False`) only need `data()` for cell
values; Web does not call `editData()` or `setData()` for those cells.
Editable choices are always shown as native select controls in their cells;
selecting an option commits immediately. Click other editable cells or press
Enter to edit inline: input for str/int/float/None, checkbox for bool.
Select/input editors have no border, outline, padding or margin; the focused
cell uses a background highlight. Entering text edit mode preserves the cell's
display dimensions: the input shrinks into the available space, including with
prefix/suffix decorations, and long drafts scroll inside it without resizing
rows or columns. Committed values still participate in normal content sizing.
Enter/blur commits text, Escape cancels;
checkbox changes commit immediately. Pending submissions disable their
editor until Python responds. Invalid values leave the editor open with an error.
Raw values stay separate from display labels; choice indexes resolve to Python
values before existing binding conversion. Only bindings or .set() enable editing.
Keyed rows retain unchanged drafts across moves; changed data/choices/bindings and
removed cells revoke old events. Adapter reconciliation cancels drafts because
adapters provide coordinates without stable row IDs. Reconnect cancels local drafts.
autofit=True uses browser content sizing; False freezes initial column widths.
Tables are limited to 10,000 cells. Native column resizing, sorting, embedded
widgets, virtualized large data and multi-selection remain unimplemented.

## Transport and runtime

Web uses the `pui.v1.msgpack.zstd-stream` WebSocket subprotocol. Python keeps one
downstream zstd compression context per connection, with a 4 MiB history window,
and block-flushes once after each complete DOM/Canvas render batch. All operations
and drawing updates in that batch share one MessagePack render envelope.
Control messages such as results and errors flush at their own message boundaries.
The browser uses bundled compress-utils 0.10.1 Zstandard WASM for compression and
decompression, including a persistent downstream decoder. Reconnect resets compression history even
when application state resumes; render retries are encoded again in stream order.
Upstream events retain independent, content-sized zstd frames using compress-utils
level 1 (native Zstandard level 2). Painter APIs and separate DOM/Canvas ACKs are unchanged.

### Limits

Web Python and browser codecs allow 5,000,000 aggregate value/key items,
8 MiB compressed, 32 MiB decoded, a 16 MiB decoder window and 64 nesting levels.
Render states share the item budget across widgets and Canvas frames. Item-count and nesting
errors report their separate thresholds; exceeding a limit ends that session.
Byte/item limits apply to each complete message, not the lifetime of the stream.

The [Web API](web-api.md) describes server-generated patches, bounded binary
framing, revision/ACK recovery and independent Canvas presentation confirmations.
Canvas advertises geometry/text capabilities. Packaged JS/WASM requires no
Node or CDN at runtime; tested Python dependencies are pinned in
[tests/requirements-web.txt](https://github.com/buganini/PUI/blob/main/tests/requirements-web.txt).

### Validation and recovery

Current message bodies are validated before dispatch. Invalid edits do not invoke
setters/callbacks, and repeated input sequences do not repeat callbacks. Older
value revisions may still update a live binding; future revisions are rejected.
Shared malformed binary fixtures pass in Python and Chrome; other engines remain
unverified.

### Flow control and timeouts

Worker startup and gateway-to-worker IPC drain waits have 30-second limits.
A browser output write that stalls for 30 seconds is logged and its transport
aborted, retaining the worker under the normal TTL. A partially transmitted frame
is never retried on that connection. Worker-to-gateway IPC writes have a 60-second
limit, allowing the gateway time to drop the slow browser and resume draining;
failure of that internal channel ends the worker. WebSocket close attempts have
a one-second deadline followed by transport abort. Real TCP pressure and unread
IPC-peer tests cover these paths and retained-worker resumption.
Shutdown also reaps
blocked workers using bounded graceful/terminate/kill steps. A blocked worker's
IPC drain does not hold the admission lock for other clients; retained workers
and workers still being reaped count toward capacity.
Chrome DOM tests cover keyed focus/selection and local draft retention, commit
normalization, synthetic composition ordering and snapshot repair after partial
application failure. Canonical records advance only after the full DOM update
succeeds. Native desktop/mobile IME behavior remains unverified.
Chrome WebSocket tests also cover partial DOM failure, discarded ACK/resync
ordering, same-session snapshot recovery and retained drafts/focus. Fatal client
protocol errors close with application code 4002; a full input queue uses 4008.
Both keep a visible error and require reloading rather than automatic retries.
The client permits up to 64 outstanding actions and 256 queued actions. Each
result releases one credit; overflow stops further actions and ignores late
replies. Mousemove uses these same credits without replacing queued samples.
All actions retain their order. Chrome pressure tests verify these limits and preserved error status.
An unacknowledged render retries the same immutable body after 30 seconds, at
most twice. A further timeout disconnects with code 1013 and retains the worker
under its normal TTL; reconnection starts with a fresh snapshot. Callbacks are
never replayed. A matching ACK releases the single render credit and cancels its
deadline; duplicate ACKs cannot grant extra credits.

### Snapshot ownership

The worker shares published snapshots, Canvas frames and binding records as
read-only data through diffing, encoding, ACKs and retries. Updates build new
records instead of changing retained versions. Mutable application-owned model
values and choice contexts are still detached when read. Shared Web/Pyodide
Painter helpers construct commands as fixed-position tuples; recording
checks the active callback and command budget, then appends each tuple unchanged.
Diff compares these tuples directly, MessagePack encodes them as arrays, and the
browser reads array fields without rebuilding command objects. Integer Canvas
colors use a 128-entry LRU cache per worker
for hexadecimal strings, shared across Canvas instances and frames; other values
pass through without entering the cache. Runtime-owned snapshots skip the generic
recursive value walk in `offer(trusted=True)`, and finishing a Canvas frame does
not scan its commands. Each snapshot is structurally indexed
once. Its retained index follows the snapshot through diffing, ACK promotion
and recovery; retries reuse the
outstanding body. Standalone `diff()` retains strict input validation. Downstream
render packing checks the envelope, then calls MessagePack directly and caps the
result at 32 MiB (8 MiB compressed). It does not recursively inspect Python values;
the decoder enforces per-message item/depth limits, and the browser checks retained
state budgets. Render numbers pass through to native drawing; other message types
and incoming events retain strict value checks. A small command splice cannot
bypass retained-state limits.
During DOM recovery, old snapshots and patch retries receive discarded ACKs;
only a newer snapshot may restore synchronization. Obsolete renders do not
consume recovery attempts. Persistent DOM failures stop after three recovery
attempts; Chrome tests cover both paths.

### Lifecycle checks

`env/bin/python tests/web_soak.py --rounds 100 --clients 4` runs an optional Linux
lifecycle check using real workers, session resume/expiry races and shutdown with
an active render. It reports descriptor counts, RSS, compressed snapshot/patch
bytes and local action-to-render latency. On Python 3.14.4 (2026-10-15), 400
cycles completed in 53.4 seconds: 134 resumed, 266 expired, gateway descriptors
stayed at 10, RSS grew from 48.1 to 48.7 MiB, and all workers were reaped. The tiny
fixture's median worker RSS was 44.0 MiB; local action p50/p95 was 1.74/2.42 ms.
These measurements describe this fixture and host, not application capacity or
browser/Internet latency. Longer runs and real application workloads remain needed.

### Canvas command arrays

The internal Web/Pyodide Canvas format is shared by full frames and command
splices. The public Painter API is unchanged. Python uses tuples and browser
transports deliver arrays; no intermediate dict/list conversion is required.

| Opcode | Array fields, in order |
| --- | --- |
| `line` | opcode, x1, y1, x2, y2, color, width |
| `polyline` | opcode, points, color, width |
| `cubic` | opcode, start, control1, control2, end, color, width |
| `polygon` | opcode, points, fill, stroke, width |
| `rect` | opcode, x1, y1, x2, y2, fill, stroke, width |
| `ellipse` | opcode, x, y, rx, ry, fill, stroke, width |
| `text` | opcode, x, y, text, w, h, size, color, rotate, anchor |
| `path` | opcode, subpaths, fill_rule, fill, stroke, width |
| `image` | opcode, resource, transforms, x, y, width, height, src_x, src_y, src_width, src_height, opacity |

Optional fields keep their positions with `None` / `null`. Points remain arrays
of coordinates; compound subpaths retain their `points` and `closed` fields.
Command opcodes remain strings. Resource, frame revision and aggregate size/count
limits are unchanged.

## Development and validation

Browser widget declarations, binding/action handling, render diffs, painter
recording and table behavior live in the internal `PUI._browser` package.
`PUI.web` retains its public imports and supplies server startup, thread-safe
scheduling, HTTP image resources and network transport. Shared modules must not
import Web server dependencies; `tests/browser_imports.py` checks that boundary.

Front-end sources live in `browser-client/shared` and `browser-client/web`.
The shared controller owns input ordering, action credit, render credit
and recovery; Web supplies WebSocket/session handling and HTTP image validation.
`tests/browser_bundle.cjs` checks that the shared bundle has no backend or codec
dependencies. Built assets remain in `PUI/web/static` with unchanged public URLs.
The [Pyodide backend](pyodide-reference.md) uses those shared layers with a local
worker bridge and owned Blob resources; its static cookbook build is separate
from Web's server and codec bundle.

Run the Python transport/lifecycle tests from the checkout with the Web
environment activated:

```shell
python -m unittest discover -s tests -p "web_*.py"
```

The suites cover Python 3.9 and 3.14. Linux exercises both its native forkserver
strategy and the additional spawn suite; the Chrome cookbook/codec checks also
cover spawned workers. Native macOS/Windows execution remains unverified.
Descriptor/RSS soak and nginx proxy harnesses are Linux-specific.

With nginx, Node and Playwright/Chrome already installed, run an isolated
prefix-stripping proxy check:

```shell
env/bin/python tests/web_proxy.py
env/bin/python tests/web_proxy.py --unix
```

The second command tests a Unix socket upstream and its cleanup on shutdown.
Set `PUI_NODE` and `PUI_BROWSER_MODULES` if these tools are outside normal search
paths. The harness starts services on temporary ports and cleans them up without
changing the system proxy.

### Rebuilding browser assets

Install Node.js (tested with Node 22) with npm/npx, then run from the checkout:

```shell
make web-build
```

Both `make web-build` and `make pyodide-build` automatically prepare `env/web-client`
and install locked dependencies using `npx --yes pnpm@11.25.0`; a global pnpm install
is unnecessary. The first install requires network access. Dependency installation
must succeed before bundling starts. `make web-build` builds the Web browser bundle;
`make pyodide-build` builds the static Pyodide site. Use `make build` to build
both without starting either server; the shared dependency setup runs once.

On Windows, install Node.js with npm/npx and Python 3.9+, then use PowerShell:

```powershell
.\build.ps1
```

This installs the same locked dependencies once, builds `PUI/web/static/`, and
builds the complete static site in `dist/pyodide/`, without Make or a global pnpm
installation. It stops on any failed step and does not start servers or publish
packages. The script uses `env/Scripts/python.exe` if present, then an activated
virtual environment, then `py -3` or `python` on PATH. Override it with
`.\build.ps1 -Python 'C:\path\to\python.exe'`. If local script execution is blocked,
run `powershell -NoProfile -ExecutionPolicy Bypass -File .\build.ps1`; this applies
only to that PowerShell process. The script itself works from any current directory.

The generated `PUI/web/static/client.js` is ignored by Git; JavaScript sources
live in `browser-client/`. Both `make web` and `make publish` run the build first.
Release source archives and wheels include the built bundle, so installed users
do not need Node or pnpm. Git checkouts need Node.js and npm/npx as described above.
The GitHub Pages workflow separately uses `make pyodide-build` to generate its
browser assets in `dist/pyodide`.

Restart the server after rebuilding. This uses the pinned @msgpack/msgpack,
compress-utils and esbuild packages; upstream modules are bundled
without edits.

## Named references

`PUI.web.ref` and `PUI.pyodide.ref` are the same lookup function as
`PUI.ref`, reading an internal registry within that Python process/runtime. Use fixed names with `.ref("myapp.component.name")` and call
`ref("myapp.component.name")` after the node update has completed. Both
backends export the same `ref` function as `PUI`; missing names raise `KeyError`. Web session workers have separate
registries. Ref values remain Python objects and are not serialized to clients.
Every binder stores its original node in `.node`; queued commands resolve
`.node.get_node()` at execution time. Each update registers a new binder. Tabs and Views
binders provide `.select(key)`, queued on the Python event loop.
See [the common reference](Reference.html#refs) for lifetime and binder rules.

Window binders expose `maximize(bool)`, `minimize(bool)` and `fullscreen(bool)`
for API compatibility, but currently log warnings without changing browser
state. Browser window maximize/minimize are not exposed by ordinary page APIs;
fullscreen additionally needs browser user activation and is not implemented.

## AI development sidebar

`Application.start(codex={}, claude={}, ...)` optionally adds a browser sidebar
using SDK/CLI credentials; optional key, model and effort dictionary entries configure each provider.
With configured auth, it requires both auth and ai permissions from the login
result; ordinary users see no sidebar and cannot connect to the AI WebSocket.
Without auth, anonymous owners retain access when AI is enabled. It preserves AI
conversation history while renewing the initiating session after workspace edits.
See [AI development](ai-reference.md) for installation, permissions and lifecycle.

## Inbound file drops

Use `.drop(callback, extensions=(".txt", ".json"))` and explicitly call `event.accept()` or `event.reject(reason)`. The browser checks extensions and per-drop limits before uploading; the server repeats validation. A rejected batch displays an alert. Text/URLs need no upload. Directories and move/link operations are unsupported.

Files are uploaded together through authenticated, owner/session-scoped HTTP multipart requests, then delivered through the ordinary WebSocket event path. Uploads require Origin and CSRF-token checks and a live target token; stale targets reject the drop. The callback receives server paths, never browser source paths. All uploaded DropFiles have `temporary=True`.

`Application.start(upload_limits={...})` accepts partial overrides of these positive integer defaults: `max_files=32` per drop, `max_file_bytes=64 * 1024 * 1024`, `max_session_bytes=256 * 1024 * 1024`. In-progress bytes count toward the session quota. Deleting files in application code releases their quota.

Storage uses a private temporary root, session directory, drop UUID and file UUID; original filenames are metadata. Partial files use `.part`. Rejected/incomplete batches are discarded. Accepted files survive reconnect/resume and are removed on renew, retirement or worker exit. Worker cleanup is backed by supervisor cleanup after worker crashes and normal server shutdown; abrupt termination of both processes cannot guarantee cleanup. Copy or move files elsewhere to preserve them. Landlock configurations must explicitly permit the temporary area when uploads are needed.

### Visibility

`.visible(value)` accepts a boolean computed in `content()`. Web and Pyodide
hide the retained DOM element with `display: none`, including its padding and
margin. Showing it reuses the element and its local editor draft. Tabs/Views
selection still controls which page is displayed. Visibility is presentation,
not an authorization boundary. Hidden nodes freeze child synchronization: retained children
remain in snapshots, initially hidden children are not mounted, and showing the node
refreshes its subtree. Timers and background application work can continue. See [common modifiers](Reference.html#common-modifiers)
for scope and other backends.
The Textual-only `.tVisible()` modifier is ignored by Web and Pyodide, including its boolean value.

### Responsive layout

See the [shared Responsive layout guide](Reference.html#responsive-layout) for API choices and examples.

Container `.size()` lazily enables a browser `ResizeObserver` and returns a binding
whose value is initially `None`, then `(width, height)` in content-box CSS pixels.
Measurements exclude border and padding and travel through the existing connection;
Python reads the latest received measurement. `.visible(value)` sets the baseline;
`.wideVisible(minWidth, value)` overrides it when the nearest physical parent
reaches the inclusive width threshold. Unknown size leaves the baseline unchanged.
Width conditions and direct reads of `.size().value` use ordinary State subscriptions:
each changed size rebuilds the declaring view; an identical size does not notify.
`.wideLayout()` and `.wideStyle()` use the same parent measurement and State
subscription. The update path is browser `ResizeObserver` → connection → worker
size State → Python `content()` → DOM patch. Rules are not compiled into CSS media
or container queries: a threshold change therefore requires a server round trip.
Any changed size can refresh the subscribed view, even when it remains on the same
side of a breakpoint. A new node declaration uses the latest received measurement;
it does not synchronously ask the browser to measure again.

Observers are released with their DOM elements and reinstalled after connection recovery.
Use an externally sized parent to avoid content-size/layout feedback loops.


## Worker lifecycle logs

The supervisor logs worker start, readiness, attach/resume/takeover, detach,
stop reason and exit code through `PUI.web.lifecycle`. Forced terminate/kill,
startup failures and unexpected IPC loss are warnings. Logs identify workers
by PID and omit cookies, resume tokens and credentials.

When no logging handler is configured for this logger or its ancestors,
`Application.start()` installs an INFO stderr handler with timestamps. Existing
application logging configuration takes precedence. Session TTL expiry, renew,
logout and server shutdown are identified in stop/exit logs.

### Adaptive direction

`HVBox(minWidth)` and `VHBox(minHeight)` observe the nearest physical parent's content size and change CSS flex direction without replacing their DOM children.
Thresholds use CSS pixels; unknown sizes use vertical and horizontal respectively.
`HBox(inverse=True)` and `VBox(inverse=True)` use `row-reverse` and
`column-reverse`. Both adaptive boxes accept `inverseH=False` and `inverseV=False`,
selecting the flag for the current direction. Reversal preserves DOM child order,
focused inputs and local drafts; keyboard tab order remains DOM order. Native
reverse flow starts at the opposite main-axis edge. Virtual PUI views add no DOM
wrapper, so their direct controls participate in the same flow; nested physical
containers retain their own direction. Pyodide uses the same browser renderer.
See [common reference](Reference.html#hvbox) for the shared contract.

## Imperative blocking dialogs

`Information(message="Information", title="Information Dialog")`,
`Warning(message="Warning", title="Warning Dialog")` and
`Critical(message="Critical", title="Critical Dialog")` display a native browser
alert and return `None` after dismissal.
`Confirm(message="Confirm", title="Confirm Dialog")` returns `True` for OK or
`False` for Cancel. `Prompt(prompt="Input", title="Input Dialog", default="")`
returns the entered string (including an empty string), or `None` on Cancel.

These are **imperative, blocking** functions, not declarative nodes or async functions:

```python
def on_delete(event):
    if UI.Confirm("Delete this item?", title="Delete"):
        delete_item()
```

Call them on the application thread from callbacks after startup, rather than during
construction, `setup()` or initial `content()`. Background threads must use
`get_poster()` to schedule the callback. The callback pauses until the browser replies;
a separate worker transport thread continues receiving WebSocket messages relayed by
the supervisor. Other application events queue without executing, and timers/redraws
wait. Each worker allows one pending dialog. Disconnect, takeover or transport closure
unblocks it with `ConnectionError`; dialogs are not replayed on resume.

The browser owns appearance and may suppress dialogs, in which case its native return
value is used. `title` is prepended to the message rather than setting a window title;
Information/Warning/Critical have the same alert appearance. State changes made before
the call are rendered after the callback finishes, not automatically flushed before
the dialog. The Cookbook Dialog page demonstrates these functions. File pickers and
declarative `Dialog` remain separate, unsupported Web features. Pyodide's browser-worker
bridge does not implement these blocking helpers.

### Adaptive Grid

`Grid().columns(1, dense=None).wideColumns(400, 2).wideColumns(600, 3)` uses the same
parent-width observations as `wideLayout`. Python calculates effective cells;
CSS uses `repeat(n, minmax(0, 1fr))` tracks. Computed positions do not change node
IDs or binding registrations. The keyword-only `dense` argument of `.columns()`
defaults to `None`: backfill starts at the previous visible sibling's
starting row, without moving above it. `dense=True` searches from the top-left;
`dense=False` only advances the placement cursor. `.wideColumns()` retains that
mode while changing the column count. Backfill can change visual
order relative to declaration/Tab order. Hidden children occupy no automatic cell; oversized column
spans clamp to the current column count without changing their declaration.
Pyodide shares this layout path. See [Grid reference](Reference.html#grid).

### Grid cell sizing

Web and Pyodide stretch Grid children to fill their assigned cells, including spans
expanded by `columns(expandChildren=True)`. Explicit layout width/height remain
minimum sizes rather than preventing the element background from filling its cell.

### Divider orientation

Divider is vertical in horizontal containers and horizontal in vertical containers.
It fills the cross axis without consuming extra main-axis space. Web and Pyodide
update its orientation when an adaptive container changes direction.

## Matplotlib Canvas

`MatplotlibCanvas(plotter, *args, **kwargs)` uses the shared PUI Canvas renderer.
See [Canvas Functions](Reference.html#canvas-functions) for paths, TRGB colors,
RGBA resources and native clipping, and [MatplotlibCanvas](Reference.html#matplotlibcanvas)
for adapter limits. The [Matplotlib cookbook](../cookbook/matplotlib.py) exercises
six chart cases. Web requires the optional `matplotlib` dependency on the server;
Pyodide requires `loadPackage('matplotlib')`, which the static cookbook now loads.
Text is sent as glyph paths. Navigation controls and advanced stroke styles remain pending.

Matplotlib callbacks registered with `figure.canvas.mpl_connect()` receive mouse,
vertical scroll and keyboard events. Click the plot to focus keyboard input;
Tab moves focus normally. Coordinates use logical pixels with Matplotlib's
bottom-left origin. Blur/reconnect clears held input. Navigation controls and
automatic wheel zoom are not installed. Register callbacks once per retained
Figure and call `event.canvas.draw_idle()` to repaint without rerunning the plotter.
