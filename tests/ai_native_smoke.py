"""Start the real cookbook and its AI supervisor; no model prompt is sent."""
import sys
import threading
import time
from unittest.mock import patch
from PUI.ai import native

backend = sys.argv[1]
provider = sys.argv[2] if len(sys.argv) > 2 else 'codex'
original_poster = native.poster
original_supervisor = native.Supervisor
seen = []
supervisors = []
errors = []

def poster(app, name):
    post = original_poster(app, name)
    if type(app).__name__ == 'AIApplication':
        deadline = time.monotonic() + 15
        ready_at = None
        def check():
            nonlocal ready_at
            supervisor = supervisors[0]
            now = time.monotonic()
            if supervisor.options.get('cookbook.page') == 'Vbox' and ready_at is None:
                ready_at = now
            if now < deadline and (ready_at is None or now < ready_at + .5):
                schedule()
                return
            if not app.children or app.fields.provider != provider:
                errors.append('AI window was not built')
            if ready_at is None:
                errors.append('Cookbook did not publish its initial page')
            else:
                seen.append(True)
            app.quit()
        def schedule():
            timer = threading.Timer(.1, lambda: post(check))
            timer.daemon = True
            timer.start()
        schedule()
    return post

def supervisor(credentials):
    instance = original_supervisor(credentials,
        command=[sys.executable, '-m', 'cookbook', backend, '--' + provider])
    instance.options.clear()  # Only the real child can publish the checked page.
    supervisors.append(instance)
    return instance

with patch.object(native, 'poster', poster), patch.object(native, 'Supervisor', supervisor), \
     patch.object(sys, 'argv', ['cookbook', backend, '--' + provider]):
    from cookbook.__main__ import main
    main()
transcript = '\n'.join(message['text'] for message in supervisors[0].session.messages)
assert seen and not errors, '\n'.join(errors) + '\n' + transcript
assert 'Traceback' not in transcript and '<ERROR OF' not in transcript, transcript
assert supervisors[0].process is None, 'Cookbook child was not stopped'
print(backend + '/' + provider + ' cookbook and AI window: OK')
