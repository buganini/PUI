# Public API type annotations

PUI ships inline annotations and a `py.typed` marker. They describe editor/static
checking contracts; they do not introduce runtime argument validation or change
accepted call patterns, defaults or callback forwarding.

The initial coverage includes common node modifiers and event registration,
common widget constructors across backends, Canvas drawing methods, Table/Tree
adapter methods, DropEvent and UI posters. Fluent modifiers preserve the concrete
node type, including backend-specific modifier overrides and context entry.
Drawing `color`, `fill` and `stroke` parameters use `int | None` on every backend:
use RGB integers such as `0xff0000`, or `None` for the existing default/no-paint
behavior. Native color objects and color strings are outside the public contract;
annotations do not add runtime checks.

```python
import PUI.PySide6 as UI

button: UI.Button = UI.Button("Save").style(fontSize=14).visible(True)
post = button.get_poster()
post(lambda: print("Ready"), delay=100)  # milliseconds
```

Models use a structural binding contract: a compatible object exposes a readable
and writable `value`. Values remain broad where controls support multiple types,
including numeric TextField bindings. The shared annotation vocabulary lives in
`PUI/_typing.py`; applications do not need to import it to supply bindings.

Dynamic State attributes, arbitrary Table data, backend-native parameters and
callback extra arguments still use `Any` where necessary. Callbacks use
`Callable[..., object]`: callback return values may be ignored, and forwarded
argument lists are not statically checked. No ParamSpec or additional runtime
package is required. Dynamic refs, detailed event payloads, startup forwarding
options and full internal implementation checking remain outside this initial
coverage; annotations do not imply that every backend capability is implemented.

## Python compatibility

Python 3.9 remains the runtime minimum. Postponed annotations allow modern union
spelling without evaluating it on import. Runtime aliases use 3.9-compatible
constructs, and subtype-preserving fluent methods use TypeVar rather than Self.
No new parser syntax or newer `typing` imports are required.

Evaluating annotations with `typing.get_type_hints()` on older Python versions
may fail for modern union expressions. PUI does not depend on this evaluation.
The static checks target the current development interpreter; Python 3.9 is
validated separately for import and runtime behavior.

## Development checks

Pyrefly is a developer tool, not an installation dependency of PUI. With it
installed in the development environment:

```sh
env/bin/python tests/typing/check.py
PYTHONPATH=tests env/bin/python -m unittest type_annotations
PYTHONPATH=tests env/python39/bin/python -m unittest type_annotations
```

The checker uses `--preset default` (the unconfigured basic preset omits relevant
argument checks). Its consumer examples verify concrete fluent return types,
structural bindings, painters, adapters and posters across backend imports. It
also requires thirteen deliberately incorrect calls to be rejected, including `.tVisible()` values and bounds. This is a public
API check, not a claim that all legacy implementation bodies pass type checking.

Application.start() and run() annotate codex/claude with a shared TypedDict
containing optional string key, model and effort fields. An empty dict enables
the provider; None/False disables it. Other startup forwarding remains dynamic.
