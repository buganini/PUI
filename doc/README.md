# PUI documentation

Start with the [Hello World example](../README.md#hello-world), then use the
reference for component APIs and the cookbook to explore their behavior.

## API and layout

| Document | Contents |
| --- | --- |
| [Components Reference](https://buganini.github.io/PUI/doc/Reference.html) | Backend support matrices, Application/PUIView, State bindings, events and component APIs |
| [Layout Strategy](https://buganini.github.io/PUI/doc/Layout.html) | Sizing priorities, weights, container precedence, Grid spans and adaptive layout |
| [Type annotations](typing.md) | Public annotations, editor support and static checking |

## Examples

| Resource | Contents |
| --- | --- |
| [Interactive cookbook](https://buganini.github.io/PUI/cookbook/cookbook.html) | Run component examples directly in the browser with Pyodide |
| [Cookbook source](../PUI/cookbook/) | Source for the shared backend demos; run locally with `python -m PUI.cookbook <backend>` |
| [Standalone examples](../PUI/examples/README.md) | Small applications, backend selection, extra dependencies and the shared-State dual-backend example |

## Backend guides and remaining work

The common reference defines shared APIs. Backend guides describe usage and
platform-specific behavior; progress documents track missing features, partial
support and outstanding validation. A pending validation item does not necessarily
mean the feature is unimplemented.

| Backend | Guide | Remaining work |
| --- | --- | --- |
| PySide6 | [PySide6 reference](pyside6-reference.md), including Python 3.9 compatibility | — |
| wxPython | Shared APIs in the Components Reference | [wx progress](wx-progress.md) |
| Tkinter | Shared APIs in the Components Reference | [Tkinter progress](tkinter-progress.md) |
| Flet | Shared APIs in the Components Reference | [Flet progress](flet-progress.md) |
| Textual | Shared APIs and terminal behavior in the Components Reference | [Textual progress](textual-progress.md) |
| Web — server-side Python | [Web reference](web-reference.md): startup, authentication, reverse tunnels, dual backend and browser builds | [Web progress](web-progress.md) |
| Pyodide — client-side Python | [Pyodide reference](pyodide-reference.md): browser worker, static cookbook and deployment | [Pyodide progress](pyodide-progress.md) |

A dash means there is no separate progress document, not that all validation is complete.

## Optional integrations

| Document | Contents |
| --- | --- |
| [AI development](ai-reference.md) | Codex/Claude setup, permissions and application lifecycle |
| [AI remaining work](ai-progress.md) | Missing integrations and pending provider/platform checks |
| [Linux filesystem allowlists](landlock.md) | Landlock configuration and limitations |

## Internals and design notes

These documents explain implementation details or historical design context;
use the API and backend references above when writing an application.

| Document | Contents |
| --- | --- |
| [Virtual DOM](DOM.md) | Declaration reconciliation flow |
| [Declaration design](Declaration.md) | Historical imperative-to-declarative design notes, including removed approaches |
| [Native UI notes](UI-NOTES.md) | Toolkit sizing and layout references |
| [Web wire contract](web-api.md) | Browser transport, messages, patches and protocol proposals; proposed capabilities do not imply implemented support |
