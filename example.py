#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: Florian Scherf <f.scherf@pengutronix.de>

import asyncio
import aiohttp
from aiohttp.web import Application, WebSocketResponse
from aiohttp_json_rpc import PublishSubscribeJsonRpc
import datetime


class MyRpc(PublishSubscribeJsonRpc):
    @asyncio.coroutine
    def ping(self, ws, params):
        """
        all rpc-methods have to be coroutines.
        """

        return 'pong'

    def _request_is_valid(self, request):
        # Yep! seems legit.
        return True

    def _msg_is_valid(self, msg):
        # Yep! seems legit.
        return True

    def _on_open(self, ws):
        # Hi, what brought you along today?
        pass

    def _on_close(self, ws):
        # Bye, it was a pleasure to serve you.
        pass

    def _on_error(self, ws, msg=None, exception=None):
        # Huh! nevermind...
        super()._on_error(ws, msg, exception)


@asyncio.coroutine
def clock(rpc):
    while True:
        rpc.notify('clock', str(datetime.datetime.now()))

        yield from asyncio.sleep(1)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    myrpc = MyRpc()

    app = Application(loop=loop)
    app.router.add_route('*', '/', myrpc)

    handler = app.make_handler()
    server = loop.run_until_complete(
        loop.create_server(handler, '0.0.0.0', 8080))

    # create tasks
    tasks = [
        loop.create_task(clock(myrpc)),
    ]

    # serve
    try:
        print('Starting server on 0.0.0.0:8080')
        loop.run_forever()

    except KeyboardInterrupt:
        print('Stopping server')

    finally:
        loop.run_until_complete(handler.finish_connections(1.0))
        server.close()
        loop.run_until_complete(server.wait_closed())
        loop.run_until_complete(app.finish())

        for task in tasks:
            task.cancel()

        loop.run_until_complete(asyncio.wait(tasks))

    loop.close()
