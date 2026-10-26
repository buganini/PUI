# PySide6 backend reference

PySide6 is PUI's reference backend. Install it with `pip install 'QPUIQ[pyside6]'`.
For shared component APIs, see the [Components Reference](https://buganini.github.io/PUI/doc/Reference.html).

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
[tests/requirements-python39.txt](../tests/requirements-python39.txt), and
`make check-python39` rejects a different PySide6 version. The check runs the
shared and Qt regression suites; the Flet-specific signature test is skipped in
this environment.
The normal backend extra continues to allow newer versions. Run this check when changing
shared code or the Qt backend. Keep Python 3.10-only syntax and APIs, including
standard-library `ParamSpec`, out of code used by the Python 3.9 baseline.

