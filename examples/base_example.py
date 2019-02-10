#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Florian Scherf <f.scherf@pengutronix.de>

from aiohttp.web import Application, run_app
from aiohttp_json_rpc import JsonRpc
import asyncio


@asyncio.coroutine
def ping(request):
    return 'pong'


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    rpc = JsonRpc()

    rpc.add_methods(
        ('', ping),
    )

    app = Application(loop=loop)
    app.router.add_route('*', '/', rpc.handle_request)

    run_app(app, host='0.0.0.0', port=8080)
