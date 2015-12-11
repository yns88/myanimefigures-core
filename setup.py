import os
from setuptools import setup


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

with open('commit_count') as commit_count_file:
    git_commit_count = int(commit_count_file.read())

setup(
    name="anime",
    version="0.0.1-%04d" % git_commit_count,
    author="Yunus Rahbar",
    description="The core app logic for MyAnimeFigures",
    long_description=read('README.md'),
    packages=['anime'],
)
