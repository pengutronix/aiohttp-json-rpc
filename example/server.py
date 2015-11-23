#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
sys.path.append('..')

import asyncio
import aiohttp
from aiohttp.web import Application, WebSocketResponse
from aiohttp_wsgi import WSGIHandler
from example.wsgi import application as django_app

from aiohttp_json_rpc import JsonRpc, PublishSubscribeJsonRpc
from aiohttp_json_rpc.django import DjangoAuthJsonRpc,\
    DjangoAuthPublishSubscribeJsonRpc

import datetime
import time


class MyJsonRpc(PublishSubscribeJsonRpc):
    running_counter = None

    @asyncio.coroutine
    def start_counter(self, ws, msg):
        if self.running_counter and not self.running_counter.done():
            return False

        @asyncio.coroutine
        def counter(ws, count):
            for i in range(count):
                for client in self.filter('counter'):
                    client.send_notification('counter', i)

                yield from asyncio.sleep(1)

            ws.send_notification('counter', count)

        count = msg['params'] or 10
        loop = asyncio.get_event_loop()
        self.running_counter = loop.create_task(counter(ws, count))

        return True

    @asyncio.coroutine
    def cancel_counter(self, ws, msg):
        try:
            self.running_counter.cancel()
            return True

        except:
            return False

    @asyncio.coroutine
    def ping(self, ws, msg):
        return 'pong'


class MyDjangoAuthJsonRpc(DjangoAuthPublishSubscribeJsonRpc, MyJsonRpc):
    pass


@asyncio.coroutine
def init(loop):
    app = Application(loop=loop)
    wsgi_handler = WSGIHandler(django_app)

    app.router.add_route('*', '/ws/myjrpc', MyJsonRpc)
    app.router.add_route('*', '/ws/mydajrpc', MyDjangoAuthJsonRpc)
    app.router.add_route('*', '/{path_info:.*}', wsgi_handler.handle_request)

    yield from loop.create_server(app.make_handler(), '', 8080)


@asyncio.coroutine
def clock():
    while True:
        now = str(datetime.datetime.now())

        for client in MyJsonRpc.filter('clock'):
            client.send_notification('clock', now)

        yield from asyncio.sleep(1)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init(loop))
    loop.create_task(clock())
    loop.run_forever()
