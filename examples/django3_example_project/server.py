#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Florian Scherf <f.scherf@pengutronix.de>

from example_project.wsgi import application as django_app
from aiohttp.web import Application, run_app
from aiohttp_wsgi import WSGIHandler
from aiohttp_json_rpc import JsonRpc
from aiohttp_json_rpc.auth.django import DjangoAuthBackend
import asyncio


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    wsgi_handler = WSGIHandler(django_app)
    app = Application(loop=loop)
    rpc = JsonRpc(auth_backend=DjangoAuthBackend())

    app.router.add_route('*', '/rpc', rpc.handle_request)
    app.router.add_route('*', '/{path_info:.*}', wsgi_handler.handle_request)

    run_app(app, host='0.0.0.0', port=8080)
