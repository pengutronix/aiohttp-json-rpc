import pytest
import logging


@pytest.mark.asyncio
async def test_confirmation(rpc_context):
    # setup rpc
    async def test_method(request):
        a = await request.confirm('just say yes!', timeout=1)

        logging.debug('a = %s', a)

        return a

    rpc_context.rpc.add_methods(('', test_method))

    # setup client
    async def confirm(request):
        return True

    client = await rpc_context.make_client()
    client.add_methods(('', confirm))

    # run test
    assert await client.call('test_method')
