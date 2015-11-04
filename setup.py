# -*- coding: utf-8 -*-
import sys
from os.path import join, dirname
from setuptools import setup, find_packages


install_requires = [
    'django>=1.7',
    'elasticsearch-dsl>=0.0.9',
    'python-dateutil',
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
    long_description=long_description,
    version='0.1',
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
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2",
        "Framework :: Django"
    ],
    keywords="elasticsearch django springy",
    install_requires=install_requires,
    dependency_links=['https://github.com/elasticsearch/elasticsearch-dsl-py#egg=elasticsearch-dsl-py'],
)
