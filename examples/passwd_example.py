#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Florian Scherf <f.scherf@pengutronix.de>

from aiohttp_json_rpc.auth.passwd import PasswdAuthBackend
from aiohttp_json_rpc.auth import login_required
from aiohttp_json_rpc import JsonRpc
from aiohttp.web import Application
import asyncio
import os


@asyncio.coroutine
def ping(request):
    return 'pong'


@login_required
@asyncio.coroutine
def pong(request):
    return 'ping'


if __name__ == '__main__':
    PASSWD_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               'user.db')  # login: admin:admin

    loop = asyncio.get_event_loop()
    rpc = JsonRpc(auth_backend=PasswdAuthBackend(PASSWD_FILE))

    rpc.add_methods(
        ('', ping),
        ('', pong),
    )

    app = Application(loop=loop)
    app.router.add_route('*', '/', rpc)

    handler = app.make_handler()

    server = loop.run_until_complete(
        loop.create_server(handler, '0.0.0.0', 8080))

    loop.run_forever()
