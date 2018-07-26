import importlib
import asyncio
import pytest
import os

from aiohttp.web import Application

from aiohttp_json_rpc import JsonRpc, JsonRpcClient

try:
    django_settings = importlib.import_module(
        os.environ.get('DJANGO_SETTINGS_MODULE'))

    django_wsgi_application = importlib.import_module(
        '.'.join(django_settings.WSGI_APPLICATION.split('.')[0:-1])
    ).application

    DJANGO = True

except Exception:
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
    async def teardown_server():
        try:
            server.close()
            await server.wait_closed()
            await app.shutdown()
            await handler.shutdown(60.0)

        finally:
            await app.cleanup()

    loop.run_until_complete(teardown_server())


@pytest.yield_fixture
def rpc_context(event_loop, unused_tcp_port):
    rpc = JsonRpc(loop=event_loop, max_workers=4)
    rpc_route = ('*', '/rpc', rpc)

    for context in gen_rpc_context(event_loop, 'localhost', unused_tcp_port,
                                   rpc, rpc_route):
        yield context


@pytest.yield_fixture
def django_rpc_context(db, event_loop, unused_tcp_port):
    from aiohttp_json_rpc.auth.django import DjangoAuthBackend
    from aiohttp_wsgi import WSGIHandler

    rpc = JsonRpc(loop=event_loop,
                  auth_backend=DjangoAuthBackend(generic_orm_methods=True),
                  max_workers=4)

    rpc_route = ('*', '/rpc', rpc)

    routes = [
        ('*', '/{path_info:.*}', WSGIHandler(django_wsgi_application)),
    ]

    for context in gen_rpc_context(event_loop, 'localhost',
                                   unused_tcp_port, rpc, rpc_route,
                                   routes):
        yield context


@pytest.fixture
def django_staff_user(db):
    from django.contrib.auth import get_user_model

    user = get_user_model().objects.create(username='admin', is_active=True,
                                           is_staff=True, is_superuser=True)

    user.set_password('admin')
    user.save()

    user._password = 'admin'

    return user
