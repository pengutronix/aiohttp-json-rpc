import pytest

from aiohttp_json_rpc import rpc


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
async def test_add_methods_diff_prefixes(rpc_context):
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
        ('prefix1', method1),
        ('prefix2', method2),
    )

    client2 = await rpc_context.make_client()

    # Do this so we don't rely on internal naming scheme
    assert any(m.startswith('prefix1') and m.endswith('method1')
               for m in (await client2.get_methods()))

    assert any(m.startswith('prefix2') and m.endswith('method2')
               for m in (await client2.get_methods()))


@pytest.mark.asyncio
async def test_call_method(rpc_context):
    async def add(request):
        return request.params[0] + request.params[1]

    rpc_context.rpc.add_methods(
        ('', add),
    )

    client = await rpc_context.make_client()

    assert await client.call('add', [1, 2]) == 3


@pytest.mark.asyncio
async def test_call_method_and_unpack_args(rpc_context, caplog):
    @rpc.unpack_request_args
    async def add_extra(arg1, arg2, extra):
        return str(arg1 + arg2) + ' ' + extra

    @rpc.unpack_request_args
    async def ping():
        return 'pong'

    rpc_context.rpc.add_methods(
        ('', add_extra),
        ('', ping),
    )

    client = await rpc_context.make_client()

    actual = await client.call(
        'add_extra',
        params={
            'args': [1, 2],
            'kwargs': {'extra': 'val'}
        }
    )
    expected = '3 val'
    assert actual == expected

    assert await client.call('ping') == 'pong'
