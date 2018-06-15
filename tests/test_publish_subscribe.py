import pytest


@pytest.mark.asyncio
async def test_add_topics(rpc_context):
    client1 = await rpc_context.make_client()
    assert 'topic' not in await client1.get_topics()

    rpc_context.rpc.add_topics('topic')

    client2 = await rpc_context.make_client()
    assert 'topic' in await client2.get_topics()


@pytest.mark.asyncio
async def test_subscribe(rpc_context):
    rpc_context.rpc.add_topics('topic')

    client = await rpc_context.make_client()

    async def dummy_handler(data):
        pass

    assert 'topic' not in await client.get_subscriptions()
    assert 'topic' in await client.subscribe('topic', dummy_handler)
    assert 'topic' in await client.get_subscriptions()


@pytest.mark.asyncio
async def test_unsubscribe(rpc_context):
    rpc_context.rpc.add_topics('topic')

    async def dummy_handler(data):
        pass

    client = await rpc_context.make_client()
    await client.subscribe('topic', dummy_handler)

    assert 'topic' in await client.get_subscriptions()
    assert 'topic' not in await client.unsubscribe('topic')
    assert 'topic' not in await client.get_subscriptions()


@pytest.mark.asyncio
async def test_notify(rpc_context):
    import asyncio

    # setup rpc
    rpc_context.rpc.add_topics('topic')

    async def handler(data):
        if data['method'] == 'topic':
            message.set_result(data)

    # setup client
    message = asyncio.Future()
    client = await rpc_context.make_client()

    await client.subscribe('topic', handler)

    # run test
    await rpc_context.rpc.notify('topic', 'foo')
    await asyncio.wait_for(message, 1)

    result = message.result()

    assert result['method'] == 'topic'
    assert result['params'] == 'foo'


@pytest.mark.asyncio
async def test_state(rpc_context):
    import asyncio

    # setup rpc
    rpc_context.rpc.add_topics('topic')
    await rpc_context.rpc.notify('topic', 'foo')

    # setup client
    message = asyncio.Future()

    async def handler(data):
        if data['method'] == 'topic':
            message.set_result(data)

    client = await rpc_context.make_client()

    await client.subscribe('topic', handler)

    # run test
    await asyncio.wait_for(message, 1)

    result = message.result()

    assert result['method'] == 'topic'
    assert result['params'] == 'foo'


@pytest.mark.asyncio
async def test_notify_on_request(rpc_context, event_loop):
    import asyncio

    # setup rpc
    rpc_context.rpc.add_topics('topic')

    async def method(request):
        await request.send_notification('topic', 'foo')

        return True

    rpc_context.rpc.add_methods(('', method))

    # setup client
    message = asyncio.Future()

    async def handler(data):
        if data['method'] == 'topic':
            message.set_result(data)

    client = await rpc_context.make_client()
    await client.subscribe('topic', handler)

    # run test
    await asyncio.gather(
        client.call('method'),
        asyncio.wait_for(message, 1),
        loop=event_loop,
    )

    result = message.result()

    assert result['method'] == 'topic'
    assert result['params'] == 'foo'
