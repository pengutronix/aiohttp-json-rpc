import pytest


@pytest.mark.asyncio
async def test_args(rpc_context):
    # simple coroutine based methods
    async def method1(request, a):
        return a

    async def method2(request, a, b, c=1):
        return [a, b, c]

    async def method3(a, b, c=1):
        return [a, b, c]

    async def method4():
        return [1, 2, 3]

    # class based methods
    class ClassBasedView:
        def __init__(self):
            self.STATE = 1

        async def method1(self, a):
            assert self.STATE == 1  # make sure 'self' is always accessible

            return a

        async def method2(self, request, a, b, c=1):
            assert self.STATE == 1

            return [a, b, c]

        async def method3(self, a, b, c=1):
            assert self.STATE == 1

            return [a, b, c]

        async def method4(self):
            assert self.STATE == 1

            return [1, 2, 3]

    # setup rpc and client
    rpc_context.rpc.add_methods(
        ('', method1),
        ('', method2),
        ('', method3),
        ('', method4),
        ('cls', ClassBasedView()),
    )

    client = await rpc_context.make_client()

    # simple coroutine based methods
    assert await client.call('method1', 1) == 1

    assert await client.call('method2', [1, 2]) == [1, 2, 1]
    assert await client.call('method2', [1, 2, 3]) == [1, 2, 3]
    assert await client.call('method2', {'a': 1, 'b': 2, 'c': 3}) == [1, 2, 3]

    assert await client.call('method3', [1, 2]) == [1, 2, 1]
    assert await client.call('method3', [1, 2, 3]) == [1, 2, 3]
    assert await client.call('method3', {'a': 1, 'b': 2, 'c': 3}) == [1, 2, 3]

    assert await client.call('method4') == [1, 2, 3]
    assert await client.call('method4', [5, 5, 5]) == [1, 2, 3]

    # class based methods
    assert await client.call('cls__method1', 1) == 1

    assert await client.call('cls__method2', [1, 2]) == [1, 2, 1]
    assert await client.call('cls__method2', [1, 2, 3]) == [1, 2, 3]

    assert await client.call('cls__method2',
                             {'a': 1, 'b': 2, 'c': 3}) == [1, 2, 3]

    assert await client.call('cls__method3', [1, 2]) == [1, 2, 1]
    assert await client.call('cls__method3', [1, 2, 3]) == [1, 2, 3]

    assert await client.call('cls__method3',
                             {'a': 1, 'b': 2, 'c': 3}) == [1, 2, 3]

    assert await client.call('cls__method4') == [1, 2, 3]
    assert await client.call('cls__method4', [5, 5, 5]) == [1, 2, 3]


@pytest.mark.asyncio
async def test_to_few_arguments(rpc_context):
    from aiohttp_json_rpc import RpcInvalidParamsError

    async def method1(request, a):
        return a

    async def method2(request, a, b, c=1):
        return [a, b, c]

    # setup rpc and client
    rpc_context.rpc.add_methods(
        ('', method1),
        ('', method2),
    )

    client = await rpc_context.make_client()

    # method1
    with pytest.raises(RpcInvalidParamsError) as exc_info:
        await client.call('method1')

    assert exc_info.value.message == 'to few arguments'

    # method2
    with pytest.raises(RpcInvalidParamsError) as exc_info:
        await client.call('method2', 1)

    assert exc_info.value.message == 'to few arguments'

    with pytest.raises(RpcInvalidParamsError) as exc_info:
        await client.call('method2', {'a': 1, 'c': 1})

    assert exc_info.value.message == 'to few arguments'


@pytest.mark.asyncio
async def test_type_validators(rpc_context):
    from aiohttp_json_rpc import RpcInvalidParamsError, validate

    @validate(a=int)
    async def method(a):
        assert type(a) == int

    rpc_context.rpc.add_methods(
        ('', method),
    )

    client = await rpc_context.make_client()

    await client.call('method', 1)

    with pytest.raises(RpcInvalidParamsError):
        await client.call('method', '1')


@pytest.mark.asyncio
async def test_function_validators(rpc_context):
    from aiohttp_json_rpc import RpcInvalidParamsError, validate

    @validate(a=lambda a: type(a) == int)
    async def method(a):
        assert type(a) == int

    rpc_context.rpc.add_methods(
        ('', method),
    )

    client = await rpc_context.make_client()

    await client.call('method', 1)

    with pytest.raises(RpcInvalidParamsError):
        await client.call('method', '1')


@pytest.mark.asyncio
async def test_introspection_of_unsupported_function_types(rpc_context):
    import inspect

    try:
        inspect.getfullargspec(min)
        pytest.skip('no native C code available')  # FIXME: pypy compatibility

    except Exception:
        pass

    rpc_context.rpc.add_methods(
        ('', min),
    )

    assert not rpc_context.rpc.methods['min'].introspected
    assert rpc_context.rpc.methods['min'].argspec.args == ['request']
