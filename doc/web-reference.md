# Web backend reference

Web-specific startup, deployment and widget behavior live here. The
[common reference](Reference.html) defines shared component APIs and backend
differences; [Web progress](web-progress.md) tracks missing work, and the
[wire contract](web-api.md) describes the Python/JavaScript protocol.

- [Installation and startup](#installation-and-startup)
- [Application titles](#application-titles)
- [Binding and reverse proxies](#binding-and-reverse-proxies)
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
env\Scripts\python -m PUI.cookbook web --bind localhost:8866 --base-url /pui
```

With an activated environment, run
`python -m PUI.cookbook web --bind localhost:8866 --base-url /pui` without Make on
Linux, macOS or Windows. Open **http://localhost:8866/pui/** and sign in with
**test / test123** for ordinary access, or **dev / dev123** for AI access when
Codex/Claude is enabled. The cookbook demonstrates optional Web authentication.
`make web` uses `env/bin/python`; override `WEB_PYTHON` to select another environment.

The Web backend currently supports
Application, Window, VBox/HBox, Stack, Grid, Label, Button, TextField, MaskedField, Text, ProgressBar, Spacer, Divider and
Scroll, Views, Tabs, Checkbox, RadioButton, ComboBox, Table, Image and Canvas geometry/text/images. It is not yet included in
the common reference's full backend matrix.
Constructing an unsupported Web widget raises `NotImplementedError` naming that
widget, for example `Tree is not implemented by the Web backend`.

The cookbook also includes HeavyCanvas, DrawShapely, TimelineView,
Table(Adapter) and State Binding. Text/Spacer/Divider support the shell. Other examples show
"Not Supported for this backend"; [Web progress](web-progress.md) tracks remaining
widgets and validation gaps.

HeavyCanvas defaults to 1,000 synthetic sessions and offers 1,000, 3,000,
5,000, 7,500, 10,000, 15,000, 20,000, 25,000 and 30,000 sessions. Each session
adds about nine drawing commands; hover adds a crosshair and tooltip, and wheel
zoom exercises large command replacements.
The larger native-backend presets (120,000 through 1,000,000 sessions) are not
offered in Web; its Canvas and transport limits remain unchanged.

For an importable Application class/factory:

```shell
python -m PUI.web myapp:MyApplication --bind 127.0.0.1:8000 --base-url /tools/pui
```

From a Python launcher:

```python
from myapp import MyApplication

if __name__ == "__main__":
    MyApplication().start(bind="localhost:8866", base_url="/pui", session_ttl=900)
```

The Python entry point is `Application.start(*, factory=None, auth=None, auth_prompt='', socket_mode=None, **kwargs)`;
`run(**kwargs)` delegates to it without building the UI in the gateway.
Server options are `bind='127.0.0.1:8000'`, `base_url='/'`,
`mount_path=None`, `allow_hosts=None`, `trusted_proxies=None`, `session_ttl=900`
and `max_sessions=64`, with optional `auth=None`, `auth_prompt=''` and `socket_mode=None`.

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
overridable with `--bind` or `WEB_BIND`. Public `base_url` is independent of bind.

```shell
make web WEB_BIND='127.0.0.1:8866'
make web WEB_BIND='[::1]:8866'
make web WEB_BIND='./pui.sock'
```

For an explicit Unix socket mode in a Python launcher:

```python
MyApplication().start(bind="/run/pui/pui.sock", socket_mode=0o666, base_url="/pui")
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

The public `base_url` is independent of the upstream `mount_path`; use
`mount_path="/"` for prefix-stripping proxies.

Chrome cookbook tests pass through both prefix-preserving HTTPS/WSS and a
prefix-stripping nginx proxy; `tests/web_proxy.py` reproduces the latter using
existing nginx, Node and Playwright/Chrome installations; see
[Development and validation](#development-and-validation) for commands.
For HTTPS terminated at a proxy with an HTTP upstream, preserve the public Host
and overwrite `X-Forwarded-Proto` with the original `http` or `https` scheme
(nginx: `proxy_set_header X-Forwarded-Proto $scheme;`). Path-only `base_url`
works with HTTPS Origin validation and Secure cookies when this header comes
from a trusted proxy. The browser resolves the relative WebSocket URL as WSS.
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
an empty value disables trust. An absolute HTTPS `base_url`, such as
`make web WEB_BASE_URL=https://example.com/pui`, can still fix the public origin
explicitly and takes precedence over the request origin.
`Application.start()` and `run()` accept independent `allow_hosts=None`
(equivalent to `["*"]`). Supply a list of exact host names to restrict all HTTP
routes; matching ignores case and request ports, and accepts bracketed IPv6.
An empty list denies all hosts. CLI `--allow-host` is repeatable, and Make uses
`WEB_ALLOW_HOSTS="example.com localhost"`. Host entries contain no scheme, path or
port; partial wildcards are not supported. WebSocket Origin validation is
unchanged by `allow_hosts`, including its default `"*"`.

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
    bind="localhost:8866", base_url="/pui",
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

Web linear layouts compute expansion from the parent: HBox shares free width,
VBox/Window shares free height. On that main axis, only siblings at the highest
nonzero priority grow: positive weight (4), shrinkable widgets such as Canvas,
Text and enabled Scroll axes (3), a container's own axis (2), then its cross
axis (1). Static controls have priority 0; TextField expands only horizontally.
HBox's X/Y priorities are 2/1, VBox's are 1/2. Equal unweighted priorities share
extra space; positive weights divide space proportionally, subject to minimum
sizes. `weight=0` keeps the preferred main-axis size without growing or
collapsing it. Weights do not propagate beyond their immediate container.

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
specification differences are recorded in [the Web plan](web-progress.md).

## Widgets

### Window and text display

Button uses `.click()` and `disabled=False`. Label click handlers are keyboard
accessible. Text displays literal preformatted text; Html/Markdown are not yet
supported. Window fills the browser viewport; initial `maximize` has no OS-window
effect. `icon` and initial `fullscreen=True` log warnings and are ignored so
shared desktop declarations can render; these features remain unimplemented.

Nested/multiple Windows, pointer/key handlers and unsupported input/change handlers raise
explicit server errors. Invalid dimensions/fonts are rejected before publication.

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
when read-only, and input + datalist when editable. Enter/blur commits editable
text: an exact label match selects the first matching option; otherwise it writes
free text and index `-1`. `.change()` receives the selected index or free text.
Item values remain Python values and pass through existing Binding conversion/
validation. The current wire value domain still applies to exposed models and
options. Optional ComboBox models retain internal selection/text, and `disabled=True`
disables both selection and typing. Rebinding or changing choices invalidates
old selection/edit tokens. Pending local selections and newer typing survive
older server replies; committed text reads back the setter's authoritative value.

The [ComboBox cookbook](../PUI/cookbook/combobox.py) includes a destination
autocomplete: type `Tai` or `Tok` to narrow the native browser suggestions,
choose a full label such as `Taipei Taoyuan (TPE)`, then press Enter or leave
the field to commit `TPE` to its separate State binding. Unmatched text remains
free text. `editable=True` is required; the default `False` renders a select
that cannot accept typed text. Popup appearance and filtering follow the browser's
native datalist behavior.

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

The [HeavyCanvas cookbook](../PUI/cookbook/heavycanvas.py) accepts native pixel,
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
[tests/requirements-web.txt](../tests/requirements-web.txt).

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

Node and pnpm are development tools only. From the checkout:

```shell
mkdir -p env/web-client
cp browser-client/package.json browser-client/pnpm-lock.yaml browser-client/pnpm-workspace.yaml env/web-client/
pnpm --dir env/web-client install --ignore-scripts --frozen-lockfile
make build
```

`make build` rebuilds the Web browser bundle (`make web-build` remains available).
The generated `PUI/web/static/client.js` is ignored by Git; JavaScript sources
live in `browser-client/`. Both `make web` and `make publish` run the build first.
Release source archives and wheels include the built bundle, so installed users
do not need Node or pnpm. Git checkouts need the build dependencies above.
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

`Application.start(codex=True, claude=True, ...)` optionally adds a browser sidebar
using SDK/CLI credentials; either argument also accepts an API key string.
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

`.visible(value=True)` accepts a boolean computed in `content()`. Web and Pyodide
hide the retained DOM element with `display: none`, including its padding and
margin. Showing it reuses the element and its local editor draft. Tabs/Views
selection still controls which page is displayed. Visibility is presentation,
not an authorization boundary; hidden nodes remain in snapshots and may keep
running application work. See [common modifiers](Reference.html#common-modifiers)
for scope and other backends.
