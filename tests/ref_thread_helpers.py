"""Submit from a worker while the test deliberately does not pump the UI."""
from threading import Thread


def call_in_thread(callback):
    errors = []

    def run():
        try:
            callback()
        except BaseException as error:
            errors.append(error)

    thread = Thread(target=run, daemon=True)
    thread.start()
    thread.join(timeout=2)
    if thread.is_alive():
        raise AssertionError('Binder blocked waiting for the UI thread')
    if errors:
        raise errors[0]
