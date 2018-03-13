import pytest


@pytest.mark.asyncio
async def test_raw_responses(rpc_context):
    from aiohttp_json_rpc import raw_response

    @raw_response
    async def ping(request):
        return '{{"jsonrpc": "2.0", "result": "pong", "id": {}}}'.format(
            request.msg.data['id'])

    rpc_context.rpc.add_methods(
        ('', ping),
    )

    client = await rpc_context.make_client()
    result = await client.call('ping')

    assert result == 'pong'
