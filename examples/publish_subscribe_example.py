#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Florian Scherf <f.scherf@pengutronix.de>

from aiohttp.web import Application
from aiohttp_json_rpc import PublishSubscribeJsonRpc
import datetime
import asyncio


class MyRpc(PublishSubscribeJsonRpc):
    @asyncio.coroutine
    def ping(self, ws, params):
        return 'pong'


@asyncio.coroutine
def clock(rpc):
    """
    This task runs forever and notifies all clients subscribed to
    'clock' once a second.
    """

    while True:
        rpc.notify('clock', str(datetime.datetime.now()))

        yield from asyncio.sleep(1)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    myrpc = MyRpc()

    loop.create_task(clock(myrpc))

    app = Application(loop=loop)
    app.router.add_route('*', '/', myrpc)

    handler = app.make_handler()

    server = loop.run_until_complete(
        loop.create_server(handler, '0.0.0.0', 8080))

    loop.run_forever()
