import os
from setuptools import setup


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name="anime",
    version="0.0.1",
    author="Yunus Rahbar",
    description="The core app logic for MyAnimeFigures",
    long_description=read('README.md'),
    packages=['anime'],
)
