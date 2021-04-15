# -*- coding: utf-8 -*-

import os
import re

from setuptools import find_packages, setup


def find_version(*paths):
    with open(os.path.join(os.path.dirname(__file__), *paths)) as f:
        text = f.read()
        match = re.search(
            r'^__version__ = (?P<quote>["\'])(?P<ver>[^"\']+)(?P=quote)', text, re.M
        )
        if not match:
            raise RuntimeError("Unable to find version string.")

        return match.group("ver")


VERSION = find_version("pybrat", "__init__.py")


setup(
    name="pybrat",
    description="Parser for brat rapid annotation tool (Brat).",
    version=VERSION,
    url="https://github.com/Yevgnen/pybrat",
    author="Yevgnen Koh",
    author_email="wherejoystarts@gmail.com",
    packages=find_packages(exclude=("tests", "tests.*")),
    include_package_data=True,
    install_requires=[],
    test_suite="tests",
    zip_safe=False,
)
