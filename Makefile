PYTHON39 ?= env/python39/bin/python
WEB_PYTHON ?= env/bin/python
WEB_BIND ?= localhost:8866
WEB_BASE_URL ?= /pui
WEB_ALLOW_HOSTS ?= *
WEB_TRUSTED_PROXIES ?= 127.0.0.0/8 ::1/128 unix
NODE ?= node

runall:
	make pyside6 &
	make tkinter &
	make flet &
	make textual

tkinter:
	python3 -m cookbook tkinter

flet:
	python3 -m cookbook flet

pyside6:
	python3 -m cookbook PySide6

.PHONY: textual textual_dev
textual:
	python3 -m cookbook textual

textual_dev:
	PUI_BACKEND=textual textual run --dev cookbook.textual_app

wx:
	python3 -m cookbook wx

debug:
	# pip3 install textual-dev
	./env/bin/textual console -x SYSTEM -x EVENT -x DEBUG -x INFO

publish:
	rm -rf build dist
	python3 setup.py sdist bdist_wheel
	python3 -m twine upload dist/*

.PHONY: check-python39
check-python39:
	$(PYTHON39) -c 'import sys, PySide6; assert sys.version_info[:2] == (3, 9), "Use Python 3.9"; assert PySide6.__version__ == "6.7.2", "Use PySide6 6.7.2 for this compatibility baseline"'
	PYTHONPATH=tests QT_QPA_PLATFORM=offscreen $(PYTHON39) -m unittest -v \
		pyside6_regression pyside6_canvas pyside6_tabs pyside6_views table_ragged tree_sync scroll_sync \
		signature_regression decorator_signatures dom_lifecycle optional_binding \
		timeline_regression combobox_binding_regression state_binding_lifetime

.PHONY: web web-build
web:
	$(WEB_PYTHON) -m cookbook web --bind "$(WEB_BIND)" --base-url "$(WEB_BASE_URL)" $(foreach host,$(WEB_ALLOW_HOSTS),--allow-host "$(host)") $(if $(strip $(WEB_TRUSTED_PROXIES)),$(foreach proxy,$(WEB_TRUSTED_PROXIES),--trusted-proxy "$(proxy)"),--no-trusted-proxy)

web-build:
	$(NODE) browser-client/build.mjs

.PHONY: pyodide pyodide-build
pyodide-build:
	$(WEB_PYTHON) -m cookbook.build_pyodide
	$(NODE) browser-client/build-pyodide.mjs

pyodide: pyodide-build
	$(WEB_PYTHON) -m http.server 8868 --bind localhost --directory dist/pyodide
