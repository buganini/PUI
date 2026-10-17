# Linux filesystem allowlists

Install `pip install 'QPUIQ[landlock]'` and pass `landlock` to the selected
backend's `Application.start()`. The default `None` leaves access unchanged.

```python
app.start(landlock={
    'read': ['/absolute/path/to/application', '/absolute/path/to/input'],
    'write': ['/absolute/path/to/output'],
})
```

This illustrates the permission syntax, not a complete runtime allowlist.
Add the Python runtime, installed packages, native libraries, fonts, theme
resources, configuration files and devices your application actually needs.
PUI does not automatically grant access to any runtime or system directory.
Lazy imports and native resource loading after startup require permission too.

- `read`: read files and list directories.
- `write`: read and write, create/remove files and directories, rename/link,
  truncate and device operations supported by the kernel. It excludes execution.
- `execute`: execute files. Add read permissions separately when needed.

Each value is a sequence of existing file or directory paths. Directory grants
cover descendants. Paths are resolved to absolute paths; symlinks do not grant
access to targets outside allowed hierarchies. Grants are additive: a narrower
read rule cannot override a broader write rule. An empty mapping denies all
handled filesystem operations. There is no blacklist mode.

Linux requires the optional `landlock` package and kernel Landlock ABI 3 or newer
(normally Linux 6.2+ with Landlock enabled). PUI supports the binding on x86-64,
AArch64 and RISC-V 64. Missing support, invalid paths or failure to install the
policy abort startup; PUI never silently runs unrestricted on Linux. Other
platforms, including Pyodide, log a warning and ignore the option.

## When restrictions take effect

Web applies the allowlist in each worker before importing the application
factory. The HTTP gateway, authentication callback and other sessions are not
restricted by that worker. Application imports executed by the launcher before
starting the server are outside this boundary.

Desktop backends apply it when `start()` is called, before entering their event
loop. Constructors, UI setup and imports already executed remain outside this
boundary. The restriction cannot be undone. Future child processes/threads
inherit it. Existing threads are not retroactively restricted, so PUI refuses
to apply a policy when `/proc/self/task` shows multiple threads. Disable hot
reload and arrange startup before background threads; native toolkits may
already have created threads and therefore be incompatible with this entrypoint.
The legacy `run()` shortcut does not accept this option; use `start()`.

## Boundaries

Denied opens raise `PermissionError`; file navigation may show errors or omit
inaccessible entries depending on the toolkit. Landlock does not hide all path
metadata. Already-open descriptors and loaded memory remain accessible. It does
not revoke existing network sockets, impose CPU/memory limits, restrict Python
APIs or provide a complete sandbox for hostile code. This integration uses only
filesystem rules; network/process isolation requires separate controls.
