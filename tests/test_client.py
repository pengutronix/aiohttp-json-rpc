import pytest

from aiohttp_json_rpc.client import JsonRpcClient


pytestmark = pytest.mark.asyncio(reason='Depends on asyncio')


async def test_client_connect_disconnect(rpc_context):
    async def ping(request):
        return 'pong'

    rpc_context.rpc.add_methods(
        ('', ping),
    )

    client = JsonRpcClient(
        url='ws://{host}:{port}{url}'.format(
            host=rpc_context.host, port=rpc_context.port,
            url=rpc_context.url,
        )
    )

    await client.connect_url(
        'ws://{host}:{port}{url}'.format(
            host=rpc_context.host, port=rpc_context.port,
            url=rpc_context.url,
        )
    )
    assert await client.call('ping') == 'pong'
    await client.disconnect()
    assert not hasattr(client, '_ws')

    await client.connect(
            host=rpc_context.host, port=rpc_context.port,
            url=rpc_context.url,
        )
    assert await client.call('ping') == 'pong'
    await client.disconnect()


async def test_client_autoconnect(rpc_context):
    async def ping(request):
        return 'pong'

    rpc_context.rpc.add_methods(
        ('', ping),
    )

    client = JsonRpcClient(
        url='ws://{host}:{port}{url}'.format(
            host=rpc_context.host, port=rpc_context.port,
            url=rpc_context.url,
        )
    )

    assert not hasattr(client, '_ws')
    assert await client.call('ping') == 'pong'
    assert hasattr(client, '_ws')
    initial_ws = client._ws

    assert await client.call('ping') == 'pong'
    assert initial_ws is client._ws

    await client.disconnect()
