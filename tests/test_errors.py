import pytest


@pytest.mark.asyncio
async def test_RpcMethodNotFoundError(rpc_context):
    from aiohttp_json_rpc import RpcMethodNotFoundError

    client = await rpc_context.make_client()

    with pytest.raises(RpcMethodNotFoundError):
        await client.call('flux_capatitor_start')


@pytest.mark.asyncio
async def test_RpcInvalidRequestError(rpc_context):
    from aiohttp_json_rpc import RpcInvalidRequestError

    async def test_method(request):
        raise RpcInvalidRequestError

    rpc_context.rpc.add_methods(('', test_method))

    client = await rpc_context.make_client()

    with pytest.raises(RpcInvalidRequestError):
        await client.call('test_method')


@pytest.mark.asyncio
async def test_RpcInvalidParamsError(rpc_context):
    from aiohttp_json_rpc import RpcInvalidParamsError

    async def test_method(request):
        raise RpcInvalidParamsError

    rpc_context.rpc.add_methods(('', test_method))

    client = await rpc_context.make_client()

    with pytest.raises(RpcInvalidParamsError):
        await client.call('test_method')
