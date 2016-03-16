#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Florian Scherf <f.scherf@pengutronix.de>

from django_example_project.wsgi import application as django_app
from aiohttp.web import Application
from aiohttp_wsgi import WSGIHandler
from aiohttp_json_rpc import JsonRpc
import asyncio


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    wsgi_handler = WSGIHandler(django_app)
    app = Application(loop=loop)
    rpc = JsonRpc()

    rpc.add_methods(
        ('', 'django_example_app.rpc')
    )

    app.router.add_route('*', '/rpc', rpc)
    app.router.add_route('*', '/{path_info:.*}', wsgi_handler.handle_request)

    handler = app.make_handler()

    server = loop.run_until_complete(
        loop.create_server(handler, '0.0.0.0', 8080))

    loop.run_forever()
