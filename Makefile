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

debug:
	textual console -x SYSTEM -x EVENT -x DEBUG -x INFO

publish:
	rm -rf build dist
	python3 setup.py sdist bdist_wheel
	python3 -m twine upload dist/*