PYTHON39 ?= env/python39/bin/python
WEB_PYTHON ?= env/bin/python
WEB_BASE_URL ?= /pui
WEB_ALLOW_HOSTS ?= *
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
		pyside6_regression pyside6_tabs pyside6_views table_ragged tree_sync scroll_sync \
		signature_regression decorator_signatures dom_lifecycle optional_binding \
		timeline_regression combobox_binding_regression

.PHONY: web web-build
web:
	$(WEB_PYTHON) -m cookbook web --host localhost --port 8866 --base-url "$(WEB_BASE_URL)" $(foreach host,$(WEB_ALLOW_HOSTS),--allow-host "$(host)")

web-build:
	$(NODE) web-client/build.mjs
