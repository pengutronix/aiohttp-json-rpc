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
