#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Florian Scherf <f.scherf@pengutronix.de>

from aiohttp.web import Application
from aiohttp_json_rpc import JsonRpc
import asyncio


class MyRpc(JsonRpc):
    @asyncio.coroutine
    def ping(self, **context):
        return 'pong'


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    myrpc = MyRpc()

    app = Application(loop=loop)
    app.router.add_route('*', '/', myrpc)

    handler = app.make_handler()

    server = loop.run_until_complete(
        loop.create_server(handler, '0.0.0.0', 8080))

    loop.run_forever()
