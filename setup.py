from setuptools import setup, find_packages
from pathlib import Path
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")
from PUI import __version__

setup(
    name='qpuiq',
    version=__version__,
    url='https://github.com/buganini/PUI',
    author='Buganini Chiu',
    author_email='buganini@b612.tw',
    description='"PUI" Python Declarative UI Framework',
    packages=find_packages(),
    package_data={"PUI.web": ["static/*.js", "static/*.css", "static/*.wasm", "static/*.txt"]},
    python_requires='>=3.9',
    extras_require={
        "pyside6": ["PySide6"],
        "wx": ["wxPython"],
        "flet": ["flet[desktop,web]>=1.0.4,<2"],
        "textual": ["textual"],
        "web": ["aiohttp>=3.13.5,<4", "msgpack>=1.1.2,<2", "zstandard>=0.25,<1"],
        "dev": ["pygments", "matplotlib", "shapely>=2.0"],
        "landlock": ["landlock==1.0.0.dev5; sys_platform == 'linux'"],
        "reload": ["jurigged"],
        "tkinter": [],  # Native Python/OS Tk support, not a PyPI package.
    },
    long_description=long_description,
    long_description_content_type='text/markdown'
)
