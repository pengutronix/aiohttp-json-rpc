#!/usr/bin/env python3.5
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


async def init(loop):
    app = Application(loop=loop)
    wsgi_handler = WSGIHandler(django_app)

    app.router.add_route('*', '/ws/jrpc', JsonRpc)
    app.router.add_route('*', '/ws/ppjrpc', PublishSubscribeJsonRpc)
    app.router.add_route('*', '/ws/dajrpc', DjangoAuthJsonRpc)
    app.router.add_route('*', '/ws/dappjrpc', DjangoAuthPublishSubscribeJsonRpc)

    app.router.add_route('*', '/{path_info:.*}', wsgi_handler.handle_request)

    return await loop.create_server(app.make_handler(), '', 8080)


async def clock():
    while True:
        now = str(datetime.datetime.now())

        for client in DjangoAuthPublishSubscribeJsonRpc.filter('clock'):
            client.send_notification('clock', now)

        await asyncio.sleep(1)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init(loop))
    loop.create_task(clock())
    loop.run_forever()
