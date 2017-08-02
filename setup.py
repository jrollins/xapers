#!/usr/bin/env python3

# much of the structure here was cribbed from
# https://github.com/pypa/sampleproject

from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

version = {}
with open("lib/xapers/version.py") as f:
    exec(f.read(), version)

setup(
    name = 'xapers',
    version = version['__version__'],
    description = 'Xapian article indexing system.',
    long_description = long_description,
    author = 'Jameson Graef Rollins',
    author_email = 'jrollins@finestructure.net',
    url = 'https://finestructure.net/xapers',
    license = 'GPLv3+',
    keywords = [],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Environment :: Console',
        'Environment :: Console :: Curses',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 3 :: Only'],

    install_requires = [
        'xapian',
        'pybtex',
        'urwid',
        ],

    package_dir = {'': 'lib'},
    packages = [
        'xapers',
        'xapers.parsers',
        'xapers.sources',
        'xapers.nci',
        ],
    # https://chriswarrick.com/blog/2014/09/15/python-apps-the-right-way-entry_points-and-scripts/
    # should we have a 'gui_scripts' as well?
    entry_points={
        'console_scripts': [
            'xapers = xapers.__main__:main',
        ],
    },
)
