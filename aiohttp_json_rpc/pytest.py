import importlib
import asyncio
import pytest
import os

from aiohttp_wsgi import WSGIHandler
from aiohttp.web import Application

from aiohttp_json_rpc import JsonRpc, JsonRpcClient

try:
    django_settings = importlib.import_module(
        os.environ.get('DJANGO_SETTINGS_MODULE'))

    django_wsgi_application = importlib.import_module(
        '.'.join(django_settings.WSGI_APPLICATION.split('.')[0:-1])
    ).application

    DJANGO = True

except:
    DJANGO = False

__all__ = [
    'rpc_context',
]

if DJANGO:
    __all__.append('django_rpc_context')


class RpcContext(object):
    def __init__(self, app, rpc, host, port, url):
        self.app = app
        self.rpc = rpc
        self.host = host
        self.port = port
        self.url = url
        self.clients = []

    async def make_clients(self, count, cookies=None):
        clients = [JsonRpcClient() for i in range(count)]

        await asyncio.gather(
            *[i.connect(self.host, self.port, url=self.url,
                        cookies=cookies or {}) for i in clients]
        )

        self.clients += clients

        return clients

    async def make_client(self, cookies=None):
        clients = await self.make_clients(1, cookies=cookies)

        return clients[0]

    async def finish_connections(self):
        await asyncio.gather(
            *[i.disconnect() for i in self.clients]
        )


def gen_rpc_context(loop, host, port, rpc, rpc_route, routes=(),
                    RpcContext=RpcContext):
    # make app
    app = Application(loop=loop)

    app.router.add_route(*rpc_route)

    for route in routes:
        app.router.add_route(*route)

    # make handler
    handler = app.make_handler()

    server = loop.run_until_complete(loop.create_server(handler, host, port))

    # create RpcContext
    rpc_context = RpcContext(app, rpc, host, port, rpc_route[1])

    yield rpc_context

    # teardown clients
    loop.run_until_complete(rpc_context.finish_connections())

    # teardown server
    server.close()
    loop.run_until_complete(server.wait_closed())
    loop.run_until_complete(app.shutdown())
    loop.run_until_complete(handler.finish_connections(1))
    loop.run_until_complete(app.cleanup())


@pytest.yield_fixture
def rpc_context(event_loop, unused_tcp_port):
    rpc = JsonRpc()
    rpc_route = ('*', '/rpc', rpc)

    for context in gen_rpc_context(event_loop, 'localhost', unused_tcp_port,
                                   rpc, rpc_route):
        yield context


if DJANGO:
    @pytest.yield_fixture
    def django_rpc_context(db, event_loop, unused_tcp_port):
        from aiohttp_json_rpc.auth.django import DjangoAuthBackend

        rpc = JsonRpc(auth_backend=DjangoAuthBackend())
        rpc_route = ('*', '/rpc', rpc)

        routes = [
            ('*', '/{path_info:.*}', WSGIHandler(django_wsgi_application)),
        ]

        for context in gen_rpc_context(event_loop, 'localhost',
                                       unused_tcp_port, rpc, rpc_route,
                                       routes):
            yield context
