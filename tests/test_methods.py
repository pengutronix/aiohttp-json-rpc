import pytest


@pytest.mark.asyncio
async def test_get_methods(rpc_context):
    client = await rpc_context.make_client()
    methods = await client.call('get_methods')

    assert sorted(methods) == ['get_methods', 'get_subscriptions',
                               'get_topics', 'subscribe', 'unsubscribe']


@pytest.mark.asyncio
async def test_add_methods(rpc_context):
    # without custom methods
    client1 = await rpc_context.make_client()
    methods = await client1.get_methods()

    assert 'method1' not in methods
    assert 'method2' not in methods

    # add methods
    async def method1(request):
        pass

    async def method2(request):
        pass

    rpc_context.rpc.add_methods(
        ('', method1),
        ('', method2),
    )

    client2 = await rpc_context.make_client()
    methods = await client2.call('get_methods')

    assert 'method1' in methods
    assert 'method2' in methods


@pytest.mark.asyncio
async def test_call_method(rpc_context):
    async def add(request):
        return request.params[0] + request.params[1]

    rpc_context.rpc.add_methods(
        ('', add),
    )

    client = await rpc_context.make_client()

    assert await client.call('add', [1, 2]) == 3
