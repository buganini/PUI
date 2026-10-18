"""Create an application with an AI development window."""
import importlib.util
import keyword
import os
from pathlib import Path
import shlex
import subprocess
import sys
import unicodedata

BACKENDS = ('PySide6', 'wx', 'tkinter', 'flet', 'web')


def choose(title, options):
    print('\n' + title)
    for index, option in enumerate(options, 1):
        print('%d. %s' % (index, option))
    while True:
        value = input('> ').strip()
        if value.isdecimal() and 1 <= int(value) <= len(options):
            return options[int(value) - 1]
        print('Enter a number from 1 to %d.' % len(options))


def valid_name(name):
    return (name.isidentifier() and not keyword.iskeyword(unicodedata.normalize('NFKC', name))
            and unicodedata.normalize('NFKC', name) != '__debug__')


def display_command(command):
    return subprocess.list2cmdline(command) if os.name == 'nt' else shlex.join(command)


def launch(command):
    print('\nRun: ' + display_command(command), flush=True)
    return subprocess.call(command)


def create_application(name, backend, provider, directory=None):
    if not valid_name(name):
        raise ValueError('Application name must be a valid Python class name, not a keyword')
    if backend not in BACKENDS or provider not in ('codex', 'claude'):
        raise ValueError('Unknown backend or AI provider')
    directory = Path(directory or Path.cwd())
    path = directory / (name + '.py')
    # -m keeps Web's Application class importable in fresh session workers.
    alias = '_UI' if unicodedata.normalize('NFKC', name) == 'UI' else 'UI'
    main_flag = '_pui_main' if unicodedata.normalize('NFKC', name) != '_pui_main' else '_pui_entry'
    source = f'''import PUI.{backend} as {alias}

{main_flag} = __name__ == '__main__'


class {name}({alias}.Application):
    def content(self):
        with {alias}.Window(title={name!r}, size=(800, 600)):
            pass


if {main_flag}:
    {name}(title={name!r}).start({provider}={{}}{", bind='localhost:8866'" if backend == 'web' else ''})
'''
    with path.open('x', encoding='utf-8') as target:
        target.write(source)
    return [sys.executable, '-m', name]


def main():
    try:
        provider = choose('AI provider', ('codex', 'claude'))
        from PUI.ai.auth import check_credentials
        print('Checking ' + provider + ' credentials…', flush=True)
        check_credentials(provider)
        backend = choose('Backend', BACKENDS)
        # Check importability before writing the example; never install packages implicitly.
        importlib.import_module('PUI.' + backend)
        while True:
            name = input('Application name (Python class name): ').strip()
            if valid_name(name):
                break
            print('Use a valid Python identifier that is not a keyword.')
        command = create_application(name, backend, provider)
        print('Created ' + str(Path(name + '.py').resolve()))
        return launch(command)
    except (EOFError, KeyboardInterrupt):
        print('\nCancelled.')
        return 130
    except (OSError, ImportError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        print('Error: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
