# AI development

Install one or both optional SDKs alongside a supported backend (Python 3.10+):

```sh
pip install 'QPUIQ[pyside6,codex]'
pip install 'QPUIQ[web,claude]'
# In a PUI checkout:
env/bin/python -m pip install -e '.[web,cookbook,codex,claude]'
```

The extras pin `openai-codex==0.163.0` (with its CLI runtime) and
`claude-agent-sdk==0.2.168`. PUI itself still supports Python 3.9 without these extras.

## Create an application

```sh
python -m PUI
```

The interactive launcher selects Codex or Claude, checks its existing credentials,
then asks for a backend and application name. Names must be Python identifiers,
not keywords. It writes `<Name>.py` in the current directory, with class `Name`,
an empty Window and `Application(title=Name)`. Existing files are never overwritten.
It prints and executes `python -m Name` with the current interpreter.

The launcher offers PySide6, wx, tkinter, Flet and Web. Missing credentials cause
an error and exit before any application file is created. Credential checks use
Codex's account status API and Claude's `auth status --json`, without sending a
model prompt. Install/login to the corresponding CLI first (`codex login` or
`claude auth login`). PUI does not parse or copy credential files. The SDK/CLI
handles its configuration, token refresh and OS credential storage.

Cookbook is a source-checkout example, not part of the installed package or launcher.

## Existing applications

```python
import PUI.PySide6 as UI

class Example(UI.Application):
    def content(self):
        with UI.Window(title="Example", size=(800, 600)):
            UI.Label("Edit this application through the AI window")

if __name__ == "__main__":
    Example(title="Example").start(codex={})
```

`Application.start(*, codex=None, claude=None, ...)` and `.run(...)` accept:

| Value | Behavior |
| --- | --- |
| `None` / `False` | Disable that provider |
| `{}` | Enable the provider using existing SDK/CLI login and defaults |
| `{"key": "API_KEY", "model": "...", "effort": "high"}` | Enable with explicit settings; each entry is optional |

Omit `key` to use existing login. Omit `model` or `effort` to retain provider defaults.
Values must be nonempty strings; model names and supported effort levels depend on the provider.
The old `True` and bare API-key string forms are not accepted.

Both providers can be enabled; the interface selects which one receives the prompt.
Their conversations are independent. Authentication and provider errors appear in
the AI interface while the application remains available. After logging in, retry
the prompt. Keys remain on the host; PUI does not send them to the browser or put
them in Options. API-key Codex sessions use a temporary CLI home so they do not
replace the developer's CLI login. Do not pass secrets in command-line arguments.

Textual and Pyodide accept these options but log a warning; they do not open an AI
interface. Calls without enabled providers keep normal application startup.

## Windows and sessions

On PySide6, wx, tkinter and Flet, the supervisor owns a separate AI window and
relaunches the original Python entry command in a fresh child interpreter. Closing
the application leaves the AI window open. Closing the supervisor stops the agent
and child, allowing graceful shutdown before a timeout terminates a stuck child.
Loss of the supervisor's IPC channel also exits the child. Failed child startup
is shown in the AI window without a restart loop; **Restart application** retries.

On Web, the AI sidebar sits to the right of the application, outside its VDOM.
Agent prompts, questions, permissions and history are owned by the gateway and
survive application session renewal. AI access uses the same browser owner/login
as the application, but configured `auth` must return both `auth=True` and
`ai=True`. General login alone does not authorize AI; the sidebar is hidden and
AI WebSocket connections are rejected. Without `auth`, anonymous
owners can use AI. WebSocket Origin and ownership checks apply to AI commands,
conversation history and approval answers. Logout and authentication expiry clear that owner's AI sessions; reauthentication
can resume retained application workers but starts a fresh AI conversation.
Only the browser session that submitted an editing prompt renews; other users'
workers stay alive. Idle conversations are bounded by the server's session capacity.

Agents work in the supervisor's startup directory. Turns within that supervisor
are serialized. PUI allows workspace edits, uses the SDK permission mechanism,
and displays requested command, network or outside-workspace approvals. It does
not enable bypass/full-access mode. Agent replies are displayed as plain text.

Before and after each turn, PUI compares recursive file names, `mtime_ns` and size.
Changes, additions or removals renew the application. Failure/cancellation is also
checked because a turn may already have edited files. Ignored directory names are
`.git`, `env`, `.venv`, `venv`, `__pycache__`, `.pytest_cache`, `.mypy_cache`,
`.ruff_cache`, `node_modules`; `*.pyc` and `*.pyo` files are ignored. Directory
symlinks are not followed. This is change detection, not a filesystem sandbox.

Supervisor/application entry configuration stays fixed during a development run.
Restart the whole program manually after changing startup configuration, credentials,
server options or the supervisor itself. AI conversation handles live until the
supervisor exits; they are not restored by PUI after a supervisor restart.

## State across native restarts

The supervisor sets `PUI_IPC` only for managed children. The child connects before
its first UI sync. No environment value means no IPC connection. Connection failure
stops child startup. A private token authenticates each JSON message on a loopback
socket, independently of stdout, with no application-level handshake.

Native backends' default `state_ref_publish(name, value)` forwards named values to
the supervisor. Strings are preserved; other JSON-compatible values use JSON text.
The supervisor drains final messages and supplies the latest values through
`PUI_OPTIONS` when launching the next child. Initialize State from `PUI.Options`;
PUI does not write application State automatically. An overridden publisher must
call the saved default publisher if this forwarding is desired.

```python
import PUI
import PUI.PySide6 as UI

class Example(UI.Application):
    def setup(self):
        self.state = UI.State({"page": PUI.Options.get("example.page", "home")})

    def content(self):
        with UI.Window():
            UI.TextField(self.state("page").ref("example.page"))
```

Web uses its existing URL State refs and Options path when renewing a worker.

## Cookbook targets

From the repository, after installing the relevant backend, `cookbook` and AI extras:

```sh
make pyside6_codex
make pyside6_claude
make wx_codex           # or wx_claude
make tkinter_codex      # or tkinter_claude
make flet_codex         # or flet_claude
make web_codex          # http://localhost:8866/pui/, login test/test123
make web_claude
```

`web_codex` and `web_claude` build browser assets first and accept the same `WEB_BIND`, `WEB_BASE_URL`,
`WEB_ALLOW_HOSTS` and `WEB_TRUSTED_PROXIES` overrides as `make web`. The AI targets
use `WEB_PYTHON` (default `env/bin/python`). SDK login errors appear in the AI area;
the interactive `python -m PUI` launcher additionally checks credentials up front.

After a native child starts or restarts and its UI event loop is ready, it first
requests foreground activation, then notifies the supervisor to restore and activate
its AI window after a 0.5-second delay. Each activation runs on its owning UI thread (PySide6, wx, Tkinter
and Flet); Flet awaits its child activation call before notifying the supervisor. Desktop focus policies may decline the request.
On macOS, wx and Tkinter also activate the owning application through AppKit before
raising the window: raising/focusing a window alone can leave it behind the child process.
No additional dependency is required.

## Model and effort selection

The Web sidebar and native AI supervisor provide Model and Effort controls.
Startup `model`/`effort` options initialize the selections. Changes apply to the
next prompt only and remain local to the AI conversation, separately per provider.
Default (an empty model field in Web) uses the provider configuration; Codex
restores the defaults resolved when its thread started, rather than retaining
a preceding turn's overrides.

Codex model suggestions and model-specific effort choices come from the SDK
model catalog. Custom model names can be entered. Catalog failures appear in
the AI log and do not prevent entering a model manually. Claude accepts a model
name and offers the SDK effort levels; model compatibility is checked by the provider.
Credentials are never included in the UI settings.
