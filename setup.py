#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

setup(name='aiohttp-json-rpc',
      version='0.1',
      author='Florian Scherf',
      author_email='f.scherf@pengutronix.de',
      install_requires=['aiohttp>=0.17.0'],
      packages=['aiohttp_json_rpc'],
      zip_safe=False)
