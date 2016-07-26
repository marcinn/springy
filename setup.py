# -*- coding: utf-8 -*-
import sys
from os.path import join, dirname
from setuptools import setup, find_packages


install_requires = [
    'elasticsearch-dsl>=0.0.9',
]

tests_require = []

# use external unittest for 2.6
if sys.version_info[:2] == (2, 6):
    tests_require.append('unittest2')

setup(
    name="springy",
    description="An elasticsearch wrapper for Django",
    license="BSD",
    url="https://github.com/marcinn/springy",
    long_description='',
    version='0.3.6',
    author="Marcin Nowak",
    author_email="marcin.j.nowak@gmail.com",
    packages=find_packages(
        where='.',
        exclude=('springy/tests',)
    ),
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Environment :: Web Environment",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Framework :: Django",
        "Framework :: Django :: 1.7",
        "Framework :: Django :: 1.8",
        "Framework :: Django :: 1.9",
        "Topic :: Text Processing :: Indexing",
    ],
    keywords="elasticsearch django springy",
    install_requires=install_requires,
    dependency_links=['https://github.com/elasticsearch/elasticsearch-dsl-py#egg=elasticsearch-dsl-py'],
)
