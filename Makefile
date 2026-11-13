PYTHON39 ?= env/python39/bin/python
WEB_PYTHON ?= env/bin/python
WEB_BIND ?= localhost:8866
WEB_MOUNT_PATH ?= /pui
WEB_ALLOW_HOSTS ?= *
WEB_TRUSTED_PROXIES ?= 127.0.0.0/8 ::1/128 unix
NODE ?= node
NPX ?= npx
LVGL_PATH ?= $(CURDIR)/lvgl-9.6.0
CMAKE ?= cmake
JOBS ?= $(shell nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)

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

.PHONY: lvgl-checkout build_lvgl_sdl2 build_lvgl_x11 lvgl_sdl2 lvgl_x11
lvgl-checkout:
	@if [ ! -f "$(LVGL_PATH)/lvgl.h" ]; then \
		git clone --depth 1 --branch v9.6.0 https://github.com/lvgl/lvgl.git "$(LVGL_PATH)"; \
	fi

build_lvgl_sdl2: lvgl-checkout
	$(CMAKE) -S csrc -B build-lvgl \
		-DPUI_LVGL_SOURCE_DIR="$(LVGL_PATH)" \
		-DPUI_DRV_SDL2=ON
	$(CMAKE) --build build-lvgl -j $(JOBS)
	LVGL_PATH=$(LVGL_PATH) PUI_DRV=sdl2 PUI_LVGL_BUILD_DIR=$(CURDIR)/build-lvgl python3 PUI/lvgl/build_lvgl_cffi.py

build_lvgl_x11: lvgl-checkout
	$(CMAKE) -S csrc -B build-lvgl \
		-DPUI_LVGL_SOURCE_DIR="$(LVGL_PATH)" \
		-DPUI_DRV_X11=ON
	$(CMAKE) --build build-lvgl -j $(JOBS)
	LVGL_PATH=$(LVGL_PATH) PUI_DRV=x11 PUI_LVGL_BUILD_DIR=$(CURDIR)/build-lvgl python3 PUI/lvgl/build_lvgl_cffi.py

lvgl_sdl2: build_lvgl_sdl2
	python3 -m PUI.cookbook lvgl

lvgl_x11: build_lvgl_x11
	python3 -m PUI.cookbook lvgl

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
