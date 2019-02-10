#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Florian Scherf <f.scherf@pengutronix.de>

from aiohttp.web import Application, run_app
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
    app.router.add_route('*', '/', rpc.handle_request)

    run_app(app, host='0.0.0.0', port=8080)
