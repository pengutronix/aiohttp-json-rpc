import pytest


@pytest.mark.asyncio
async def test_async_notification_api(rpc_context):
    # setup rpc
    async def test_method(request):
        await request.send_notification('test', 'payload')
        return True

    rpc_context.rpc.add_methods(
        ('', test_method),
    )

    # setup client
    client = await rpc_context.make_client()
    messages = []

    async def test_handler(data):
        messages.append(data)

    await client.subscribe('test', test_handler)

    # run test
    assert await client.call('test_method')
    assert len(messages) == 1 and messages[0]['params'] == 'payload'


@pytest.mark.asyncio
async def test_sync_notification_api(rpc_context):
    # setup rpc
    def test_method(request):
        request.send_notification('test', 'payload')
        return True

    rpc_context.rpc.add_methods(
        ('', test_method),
    )

    # setup client
    client = await rpc_context.make_client()
    messages = []

    async def test_handler(data):
        messages.append(data)

    await client.subscribe('test', test_handler)

    # run test
    assert await client.call('test_method')
    assert len(messages) == 1 and messages[0]['params'] == 'payload'


@pytest.mark.asyncio
async def test_async_method_api(rpc_context):
    # setup rpc
    async def server_method(request):
        assert await request.call('client_method')
        return True

    rpc_context.rpc.add_methods(
        ('', server_method),
    )

    # setup client
    client = await rpc_context.make_client()

    async def client_method(client):
        return True

    client.add_methods(
        ('', client_method),
    )

    # run test
    assert await client.call('server_method')


@pytest.mark.asyncio
async def test_sync_method_api(rpc_context):
    # setup rpc
    def server_method(request):
        assert request.call('client_method')
        return True

    rpc_context.rpc.add_methods(
        ('', server_method),
    )

    # setup client
    client = await rpc_context.make_client()

    async def client_method(client):
        return True

    client.add_methods(
        ('', client_method),
    )

    # run test
    assert await client.call('server_method')
