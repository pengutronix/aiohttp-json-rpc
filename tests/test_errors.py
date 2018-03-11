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


@pytest.mark.asyncio
async def test_RpcGenericServerDefinedError_raw(rpc_context):
    import json

    from aiohttp_json_rpc import RpcGenericServerDefinedError, raw_response

    ERROR_CODE = -32050
    MESSAGE = 'Computer says no.'

    @raw_response
    async def test_method(request):
        return json.dumps({
            'jsonrpc': '2.0',
            'id': request.msg.data['id'],
            'error': {
                'code': ERROR_CODE,
                'message': MESSAGE,
            },
        })

    rpc_context.rpc.add_methods(('', test_method))
    client = await rpc_context.make_client()

    with pytest.raises(RpcGenericServerDefinedError) as exc_info:
        await client.call('test_method')

    assert exc_info.value.error_code == ERROR_CODE
    assert exc_info.value.message == MESSAGE


@pytest.mark.asyncio
async def test_RpcGenericServerDefinedError(rpc_context):
    from aiohttp_json_rpc import RpcGenericServerDefinedError

    ERROR_CODE = -32050
    MESSAGE = 'Computer says no.'

    async def test_method(request):
        raise RpcGenericServerDefinedError(error_code=ERROR_CODE,
                                           message=MESSAGE)

    rpc_context.rpc.add_methods(('', test_method))
    client = await rpc_context.make_client()

    with pytest.raises(Exception) as exc_info:
        await client.call('test_method')

    assert exc_info.value.error_code == ERROR_CODE
    assert exc_info.value.message == MESSAGE
