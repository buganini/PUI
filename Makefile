PYTHON39 ?= env/python39/bin/python
WEB_PYTHON ?= env/bin/python
WEB_BIND ?= localhost:8866
WEB_MOUNT_PATH ?= /pui
WEB_ALLOW_HOSTS ?= *
WEB_TRUSTED_PROXIES ?= 127.0.0.0/8 ::1/128 unix
NODE ?= node
NPX ?= npx

runall:
	make pyside6 &
	make tkinter &
	make flet &
	make textual

tkinter:
	python3 -m PUI.cookbook tkinter

flet:
	python3 -m PUI.cookbook flet

pyside6:
	python3 -m PUI.cookbook PySide6

.PHONY: textual textual_dev
textual:
	python3 -m PUI.cookbook textual

textual_dev:
	PUI_BACKEND=textual textual run --dev PUI.cookbook.textual_app

wx:
	python3 -m PUI.cookbook wx

debug:
	# pip3 install textual-dev
	./env/bin/textual console -x SYSTEM -x EVENT -x DEBUG -x INFO

.PHONY: publish
publish: web-build
	rm -rf build dist
	python3 setup.py sdist bdist_wheel
	python3 -m twine upload dist/*

.PHONY: check-python39
check-python39:
	$(PYTHON39) -c 'import sys, PySide6; assert sys.version_info[:2] == (3, 9), "Use Python 3.9"; assert PySide6.__version__ == "6.7.2", "Use PySide6 6.7.2 for this compatibility baseline"'
	PYTHONPATH=tests QT_QPA_PLATFORM=offscreen $(PYTHON39) -m unittest -v \
		pyside6_regression pyside6_canvas pyside6_tabs pyside6_views table_ragged tree_sync scroll_sync \
		signature_regression decorator_signatures dom_lifecycle optional_binding \
		timeline_regression combobox_binding_regression state_binding_lifetime state_threading

# Shared setup for both browser targets; cached installs remain up to date.
.PHONY: browser-deps
browser-deps:
	mkdir -p env/web-client
	cp browser-client/package.json browser-client/pnpm-lock.yaml browser-client/pnpm-workspace.yaml env/web-client/
	$(NPX) --yes pnpm@11.25.0 --dir env/web-client install --ignore-scripts --frozen-lockfile

.PHONY: build web web-build
build: web-build pyodide-build

web: web-build
	$(WEB_PYTHON) -m PUI.cookbook web --bind "$(WEB_BIND)" --mount-path "$(WEB_MOUNT_PATH)" $(foreach host,$(WEB_ALLOW_HOSTS),--allow-host "$(host)") $(if $(strip $(WEB_TRUSTED_PROXIES)),$(foreach proxy,$(WEB_TRUSTED_PROXIES),--trusted-proxy "$(proxy)"),--no-trusted-proxy)

web-build: browser-deps
	$(NODE) browser-client/build.mjs

.PHONY: pyodide pyodide-build
pyodide-build: browser-deps
	$(WEB_PYTHON) -m PUI.cookbook.build_pyodide
	$(NODE) browser-client/build-pyodide.mjs

pyodide: pyodide-build
	$(WEB_PYTHON) -m http.server 8868 --bind localhost --directory dist/pyodide

# AI development keeps the cookbook in a restartable application process.
.PHONY: pyside6_codex pyside6_claude wx_codex wx_claude tkinter_codex tkinter_claude flet_codex flet_claude web_codex web_claude
pyside6_codex pyside6_claude:
	$(WEB_PYTHON) -m PUI.cookbook PySide6 --$(lastword $(subst _, ,$@))

wx_codex wx_claude:
	$(WEB_PYTHON) -m PUI.cookbook wx --$(lastword $(subst _, ,$@))

tkinter_codex tkinter_claude:
	$(WEB_PYTHON) -m PUI.cookbook tkinter --$(lastword $(subst _, ,$@))

flet_codex flet_claude:
	$(WEB_PYTHON) -m PUI.cookbook flet --$(lastword $(subst _, ,$@))

web_codex web_claude: web-build
	$(WEB_PYTHON) -m PUI.cookbook web --bind "$(WEB_BIND)" --mount-path "$(WEB_MOUNT_PATH)" $(foreach host,$(WEB_ALLOW_HOSTS),--allow-host "$(host)") $(if $(strip $(WEB_TRUSTED_PROXIES)),$(foreach proxy,$(WEB_TRUSTED_PROXIES),--trusted-proxy "$(proxy)"),--no-trusted-proxy) --$(lastword $(subst _, ,$@))
