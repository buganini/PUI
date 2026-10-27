# Pyodide backend

The Pyodide cookbook runs Python in a dedicated browser module worker. The page
uses the same DOM, layout, Table and Canvas renderer as the Web backend. A static
HTTP host serves the application; no Python application server or WebSocket is
needed.

## Open the cookbook

Open the [Pyodide cookbook](https://buganini.github.io/PUI/cookbook/cookbook.html)
on GitHub Pages. Its source entry is `PUI/cookbook/cookbook.html`.

This link requires a successful deployment; adding the HTML file does not by
itself publish the site. In repository **Settings → Pages → Build and deployment**,
select **GitHub Actions**, then run
[Publish cookbook and documentation](https://github.com/buganini/PUI/blob/main/.github/workflows/pages.yml) or push to
`main`. The workflow builds and uploads only `dist/pyodide`, including the existing
`PUI/doc/Reference.html` and `PUI/doc/Layout.html` URLs. Markdown/source links in those HTML
pages lead to the corresponding GitHub files.
See [GitHub's custom workflow documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).

## Build and run locally

Python 3.9+ is sufficient for the host-side builder. Install Node.js (tested with
Node 22) and npm/npx. Both browser build targets automatically install locked
dependencies under `env/web-client` using pinned pnpm 11.25.0 through npx; no global
pnpm install is needed. The first install requires network access. Visitors do not
need these build tools:

```sh
python3 -m venv env  # only if the environment does not exist yet
make pyodide
```

On Windows, run `.\build.ps1` from the repository root in PowerShell to install
the locked frontend dependencies and build both Web and Pyodide. Python 3.9+
and Node.js with npm/npx are required; Make is not. See the
[Windows build instructions](web-reference.md#rebuilding-browser-assets) for
Python selection and execution-policy details. Serve `dist/pyodide` with, for
example, `py -3 -m http.server 8868 --directory dist/pyodide` after building.

Open <http://localhost:8868/cookbook/cookbook.html>. `make pyodide-build` only builds
`dist/pyodide`; any static host can serve this directory, including under a URL
prefix. `make pyodide` serves it on localhost:8868. Production hosting needs HTTPS;
localhost HTTP is also a browser secure context. Opening the file with `file://`
is unsupported.

[`cookbook/build_pyodide.py`](../cookbook/build_pyodide.py) uses `ZipFile.write()`
to package Python files from `PUI/`, `PUI/_browser/`, `PUI/pyodide/` and `PUI/cookbook/`,
plus the example image and license. It directly copies the HTML entry, static
index and documentation; it does not generate HTML or rewrite links. The archive
retains source files so the cookbook's source viewer works, without including
native backends or the Web server. The JavaScript build then bundles the renderer
and worker; an archive SHA-256 and a build identity detect mismatched versions.
Generated files belong in `dist/pyodide`, not in the source tree.

## Runtime and lifecycle

The worker loads **Pyodide 314.0.7** from the official jsDelivr CDN at
`https://cdn.jsdelivr.net/pyodide/v314.0.7/full/`. That distribution includes
**Python 3.14.2** and supplies **Pygments 2.20.0** through its package lockfile.
The version is fixed in the worker bootstrap; no `latest` URL is used. These browser
packages do not change PUI's Python 3.9 minimum for shared code and build tools.
The cookbook loads Matplotlib; Shapely is not installed in the browser.
See [Pyodide workers](https://pyodide.org/en/stable/usage/webworker.html) and
[package loading](https://pyodide.org/en/stable/usage/loading-packages.html).

The loading banner disappears after the first applied view. Errors remain visible
with details in the browser console. **Restart Python** terminates the worker,
releases its resources and starts a fresh interpreter. It can also recover from a
busy callback because Python runs off the DOM thread. Reload, navigation away and
restart discard State and worker filesystem contents. Each tab owns its own worker;
there are no cookie sessions, login or resume controls.

Bootstrap creates `PUI.pyodide.runtime.Runtime` before importing and constructing
the app. Application code then uses the familiar declaration:

```python
from PUI.pyodide import Application, Window, Label

class App(Application):
    def content(self):
        with Window():
            Label('Python in the browser')

App(title='Example').start()
```

`start()` schedules the application on Pyodide's existing asyncio loop and returns
the task; it does not run a nested loop. `quit()` tears down the app and its timers.
`TimelineView` uses `loop.call_later`, while native backends retain their existing
thread timer. This first static builder targets the cookbook; a general application
manifest/packaging API is still pending.

## Shared behavior and local transport

- Python widget/runtime/render records live in `PUI/_browser/`. Public imports
  remain under `PUI.web` and `PUI.pyodide`; both export the same shared widget classes.
- Frontend layout, controls, input ordering, DOM/Canvas rendering, CSS and recovery
  live in `browser-client/shared/`. The Pyodide adapter owns worker startup, value
  conversion and local image resources; the Web adapter owns HTTP/WS sessions and
  codecs. Building Pyodide does not include those Web adapters or zstd/MessagePack.
- Events, measurements and ACKs cross `postMessage` as complete plain records.
  Python processes actions serially. Mousemove samples are queued without coalescing;
  pending Canvas frames coalesce repaint requests until presentation ACK. State binding identity
  stays `str(id(owner))`, scoped to the current worker epoch.
- Canvas commands are Python tuples converted directly to JavaScript arrays by
  the worker bridge, using the shared [command format](web-reference.md#canvas-command-arrays);
  no command dict/object conversion or MessagePack is needed.
- DOM and Canvas use the existing revisions, patches and full-snapshot recovery.
  Canvas geometry reuses drawing styles within a frame; text/image state and
  invalid native style fallbacks remain isolated, as in the shared Web renderer.
  There is one outstanding DOM render; Canvas presentation ACKs remain separate.
  Painter commands cross the bridge as a complete frame or splice, never one
  message per drawing command. The client reconstructs command lists and repaints.
- The bridge owns converted records and explicitly normalizes Pyodide's
  `None`/`undefined` mapping to the shared `None`/`null` schema. It does not send live
  Python proxies to the DOM thread. Retained callback proxies belong to the worker
  lifetime; temporary conversion proxies are released after dispatch.
- Runtime-owned snapshots skip repeated generic value scans. Canvas commands are
  recorded without argument type/range validation; the shared browser renderer
  logs and skips individual drawing exceptions, restoring text/image state and
  starting fresh geometry paths before continuing. Native silent ignores stay silent. Python painter/conversion errors
  still fail in the worker. Image-load failures skip those commands and acknowledge
  failure to stop continuous retries. Frame structure, resource ownership, input
  checks and reconstructed-state budgets remain enforced.
- Existing limits remain: 64 outstanding actions, 256 queued inputs, 300,000
  commands per Canvas frame, and shared 5,000,000-item / 64-level / 32 MiB logical
  render budgets. The logical encoded-size budget is not a browser heap estimate.
  HeavyCanvas keeps its 1,000–30,000-session presets here; the larger native-backend
  presets through 1,000,000 sessions are not offered in Pyodide.

Image paths refer to files in the worker's virtual filesystem. The bundled
cookbook includes `PUI/cookbook/assets/windmill.jpg`. Image revisions transfer original
bytes once to an owned Blob URL registry; crop/scale remains browser-side. Old
revisions stay alive while retained render states refer to them, and removal or
restart revokes unused Blob URLs. The 128-image revision and 64 MiB per-file limits
and shared decoded-image/Canvas pixel budgets apply. No Pillow or image re-encoding
is used. Arbitrary remote image URL support and user file import are not provided.

## Capabilities and limits

The cookbook enables layouts, basic controls, TextField/MaskedField, editable
ComboBox autocomplete, Scroll, TimelineView, Tabs, Views, Table (including adapter
editing), Canvas, HeavyCanvas, Image and State binding. Controls and styles follow
the shared browser renderer's behavior, including approximate HBox vertical and
VBox left alignment, Enter/blur field commits and a custom ComboBox candidate
listbox displaying application-defined candidates without additional filtering.
Keyword-only `edit_model` binds typed text to application State for matching,
using the same binding-write path as Web.
The candidate list retains editor focus; see the
[shared autocomplete acceptance criteria](Reference.html#autocomplete-acceptance)
for required validation. The updated candidate UI still needs a Pyodide runtime
interaction check; shared renderer tests alone do not establish that coverage.
Window titles override the application title as in Web. Desktop initial
`Window(size=...)` is ignored; the root uses the available mount-container space,
including when embedded in a div. `.size()` reports its measured content area.

`Html(text, selectable=False)` renders trusted HTML fragments using the shared
Shadow DOM renderer, including retained updates and inherited PUI styles.
See [HTML semantics and trust boundary](web-reference.md#window-and-text-display).

Tree, general dialogs, MarkDown and native widget embedding remain unavailable. DrawShapely is not enabled in this cookbook
build. Unsupported pages show their existing support notice. Blocking calls such
as `PUIView.wait()`, native threads/processes, desktop file access and native socket
libraries are not browser APIs. Use scheduled callbacks instead of blocking waits.

The CDN and compatible browser features are required. No offline guarantee,
persistent filesystem, generic file picker/export API or graceful Python interrupt
is supplied. Source and bundled data are downloadable and inspectable; client-side
code cannot enforce server authorization. This runs trusted application code and
is not an untrusted-Python sandbox.

## Validation

Validated on Linux with Chrome 155.0.8059.39 and Pyodide 314.0.7. Host bridge,
timer and import checks also pass on Python 3.9 and 3.14. Firefox/Safari and mobile
validation remain pending.

Run the local static host, then:

```sh
PYTHONPATH=tests env/bin/python -m unittest -v pyodide_runtime timeline_regression browser_imports
node tests/browser_bundle.cjs
node tests/pyodide_browser.cjs
PUI_PYODIDE_URL=http://localhost:8868/cookbook/cookbook.html node tests/pyodide_bootstrap.cjs
```

The browser suite uses Playwright and Chrome (set `PUI_BROWSER_MODULES` and
`PUI_CHROME` for their installed locations). `PUI_PYODIDE_URL` selects a different
static URL. Browser compatibility and further validation gaps are tracked in
[Pyodide progress](https://github.com/buganini/PUI/blob/main/notes/pyodide-progress.md); shared Web regression checks remain in
[Web development](web-reference.md#development-and-validation).

The existing `tests/web_controls.cjs` and `tests/web_selection.cjs` also run against
this backend by setting `PUI_WEB_URL` to its static cookbook URL. They cover native
control interactions, retained edits, optional selection models and keyboard/ARIA
behavior through the real Python worker. The bootstrap suite also passed under an
additional URL prefix, with CDN/archive failures, retry and independent tabs.

## Inbound file drops

`.drop(callback, extensions=(".txt",))` receives the shared DropEvent. Call `event.accept()` explicitly, or `event.reject(reason)` to display a browser alert. Files are copied into the worker's virtual filesystem before the callback and have `temporary=True`; text and URLs create no files. Only copy is supported; directories are rejected.

`Application.start(upload_limits={...})` accepts partial positive-integer overrides: `max_files=32`, `max_file_bytes=64 * 1024 * 1024`, `max_session_bytes=256 * 1024 * 1024`. The browser and Python check limits and extensions. Rejected batches are removed; accepted files live until runtime cleanup or worker/page termination. Applications can remove them early to reclaim quota. Virtual files do not persist across page reloads.

## URL options and named State refs

Like Web, Pyodide reads `#name=value#other=value` from the page URL before
constructing the application. Percent-decoded values in `PUI.Options` are always
strings; duplicate names use the last value. Invalid entries are logged and skipped.
The application is responsible for parsing values and initializing its State.

Declare `state("page").ref("example.page")` in `content()` to publish that State
value. The default `PUI.pyodide.state_ref_publish` batches declarations after UI
updates and merges changed values into the current hash with `history.replaceState`,
without adding browser history entries. Strings appear without JSON quotes; other
JSON-compatible values are serialized. Unrelated hash entries are preserved.
You can replace the backend's `state_ref_publish(name, value)` callback.

Reloading the page or restarting Python initializes a new application from the
current hash. Editing the hash alone does not write into an existing State.

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
