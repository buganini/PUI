from setuptools import setup, find_packages
from pathlib import Path
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name='QPUIQ',
    version='0.1.2',
    url='https://github.com/buganini/PUI',
    author='Buganini Chiu',
    author_email='buganini@b612.tw',
    description='"PUI" Python Declarative UI Framework',
    packages=find_packages(),    
    long_description=long_description,
    long_description_content_type='text/markdown'
)
