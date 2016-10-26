#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(name='aiohttp-json-rpc',
      version='0.6.2',
      author='Florian Scherf',
      url='https://github.com/pengutronix/aiohttp-json-rpc/',
      author_email='f.scherf@pengutronix.de',
      license='Apache 2.0',
      install_requires=['aiohttp>=0.20,<0.22'],
      packages=find_packages(),
      zip_safe=False)
