#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

__name__ == '__main__' and setup(name='aiohttp-json-rpc',
      version='0.11.2',
      author='Florian Scherf',
      url='https://github.com/pengutronix/aiohttp-json-rpc/',
      author_email='f.scherf@pengutronix.de',
      license='Apache 2.0',
      install_requires=['aiohttp>=3,<3.5'],
      python_requires='>=3.5',
      packages=find_packages(),
      zip_safe=False,
      entry_points={
          'pytest11': [
              'aiohttp-json-rpc = aiohttp_json_rpc.pytest',
          ]
     })
