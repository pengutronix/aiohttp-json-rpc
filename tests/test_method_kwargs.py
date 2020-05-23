import pytest


@pytest.mark.asyncio
async def test_kwargs(rpc_context):
    # simple coroutine based methods
    async def method1(request, *, a):
        return a

    async def method1_1(request, a, *, b):
        return [a, b]

    async def method2(request, a, *, b, c=1):
        return [a, b, c]

    async def method3(a, b, *, c=1):
        return [a, b, c]

    # class based methods
    class ClassBasedView:
        def __init__(self):
            self.STATE = 1

        async def method1(self, *, a):
            assert self.STATE == 1  # make sure 'self' is always accessible

            return a

        async def method2(self, request, a, *, b, c=1):
            assert self.STATE == 1

            return [a, b, c]

        async def method3(self, a, b, *, c=1):
            assert self.STATE == 1

            return [a, b, c]

    # setup rpc and client
    rpc_context.rpc.add_methods(
        ('', method1),
        ('', method1_1),
        ('', method2),
        ('', method3),
        ('cls', ClassBasedView()),
    )

    client = await rpc_context.make_client()

    # simple coroutine based methods
    assert await client.call('method1', {'kwargs': {'a': 1}}) == 1
    assert await client.call('method1_1',
                             {'args': [1], 'kwargs': {'b': 2}}) == [1, 2]

    assert await client.call('method2',
                             {'args': [1], 'kwargs': {'b': 2}}) == [1, 2, 1]
    assert await client.call('method2',
                             {'args': [1],
                              'kwargs': {'b': 2, 'c': 3}}) == [1, 2, 3]
    assert await client.call('method2',
                             {'kwargs': {'a': 1, 'b': 2, 'c': 3}}) == [1, 2, 3]

    assert await client.call('method3', {'args': [1, 2]}) == [1, 2, 1]
    assert await client.call('method3',
                             {'args': [1, 2], 'kwargs': {'c': 3}}) == [1, 2, 3]
    assert await client.call('method3',
                             {'kwargs': {'a': 1, 'b': 2, 'c': 3}}) == [1, 2, 3]

    # class based methods
    assert await client.call('cls__method1', {'kwargs': {'a': 1}}) == 1

    assert await client.call('cls__method2',
                             {'args': [1], 'kwargs': {'b': 2}}) == [1, 2, 1]
    assert await client.call('cls__method2',
                             {'args': [1],
                              'kwargs': {'b': 2, 'c': 3}}) == [1, 2, 3]
    assert await client.call('cls__method2',
                             {'kwargs': {'a': 1, 'b': 2, 'c': 3}}) == [1, 2, 3]

    assert await client.call('cls__method3', {'args': [1, 2]}) == [1, 2, 1]
    assert await client.call('cls__method3',
                             {'args': [1, 2], 'kwargs': {'c': 3}}) == [1, 2, 3]
    assert await client.call('cls__method3',
                             {'kwargs': {'a': 1, 'b': 2, 'c': 3}}) == [1, 2, 3]
