PYTHON39 ?= env/python39/bin/python

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

textual:
	textual run --dev cookbook.__main__  textual

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
