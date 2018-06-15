#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Florian Scherf <f.scherf@pengutronix.de>

from aiohttp.web import Application
from aiohttp_json_rpc import JsonRpc
import datetime
import asyncio


@asyncio.coroutine
def clock(rpc):
    """
    This task runs forever and notifies all clients subscribed to
    'clock' once a second.
    """

    while True:
        yield from rpc.notify('clock', str(datetime.datetime.now()))
        yield from asyncio.sleep(1)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()

    rpc = JsonRpc()
    rpc.add_topics('clock')

    loop.create_task(clock(rpc))

    app = Application(loop=loop)
    app.router.add_route('*', '/', rpc)

    handler = app.make_handler()

    server = loop.run_until_complete(
        loop.create_server(handler, '0.0.0.0', 8080))

    loop.run_forever()
