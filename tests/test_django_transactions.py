from aiohttp.web import Application, MsgType
from aiohttp_json_rpc import JsonRpc, RpcInvalidParamsError
import aiohttp
import asyncio
import json
import pytest
import logging

logger = logging.getLogger('test')


async def watchdog(futures):
    logger.info('Watchdog: started')

    await asyncio.sleep(2)

    for future in futures:
        if not future.done():
            future.cancel()

            logger.error(
                'Watchdog: killed Client #{}'.format(future.client_id))

    return 0


async def client(id, url, numbers, sleep=0):
    def encode_message(method, params=None, id=None):
        return json.dumps({
            'jsonrpc': '2.0',
            'id': id,
            'method': method,
            'params': params,
        })

    logger.info('Client #{}: started'.format(id))

    if sleep:
        logger.info('Client #{}: sleeps for {}s'.format(id, sleep))
        await asyncio.sleep(sleep)

    session = aiohttp.ClientSession()

    async with session.ws_connect(url) as ws:
        msg = encode_message('add', id=0, params={
            'client_id': id,
            'numbers': numbers,
        })

        logger.debug('Client #{}: > {}'.format(id, msg))
        ws.send_str(msg)

        try:
            async for msg in ws:
                if msg.type == MsgType.text:
                    logger.debug('Client #{}: < {}'.format(id, msg.data))
                    msg_data = json.loads(msg.data)

                    assert msg_data['id'] == 0

                    return msg_data['result']

        finally:
            await ws.close()
            await session.close()

    return 1


async def add(request):
    from django.db import transaction

    from django_project.models import Item

    try:
        client_id = request.params['client_id']
        numbers = request.params['numbers']

    except:
        raise RpcInvalidParamsError

    try:
        logger.debug(
            'Client #{}: try open transaction'.format(client_id))

        with transaction.atomic():
            logger.debug(
                'Client #{}: transaction opened'.format(client_id))

            for number in numbers:
                item = Item.objects.create(number=number, client_id=client_id)

                logger.debug(
                    'Client #{}: created {}'.format(client_id, repr(item)))

                await asyncio.sleep(0.1)

        logger.debug(
            'Client #{}: transaction commited'.format(client_id))

    except Exception as e:
        logger.error(
            'Client #{}: transaction aborted because of {}({})'.format(
                client_id, e.__class__.__name__, e))

        return 1

    return 0


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_cuncurrent_transactions(event_loop, unused_tcp_port):
    """
    This test tests aiohttp_json_rpc.django.patch_db_connections.

    The test sets up a JsonRpc and starts two concurrent clients.
    Both clients try to open a Django transaction.
    The test is successful if only the first client is able to commit its
    database changes.

    Note:
        The transactions are slowed down artificial and Client #2 sleeps 200ms
        on start using asyncio.sleep to make the test log more readable and
        ensure the transactions are concurrent.

    Note:
        The test starts an watchdog to make sure the test does not hang if the
        rpc communication is broken or hanging.
    """

    from django_project.models import Item
    from aiohttp_json_rpc.django import patch_db_connections

    def create_client(client_id, *args, **kwargs):
        url = 'http://localhost:{}'.format(unused_tcp_port)
        future = asyncio.ensure_future(client(client_id, url, *args, **kwargs))
        future.client_id = client_id

        return future

    patch_db_connections()

    # just to be sure
    assert Item.objects.count() == 0

    # setup rpc
    app = Application(loop=event_loop)
    rpc = JsonRpc()

    rpc.add_methods(
        ('', add),
    )

    app.router.add_route('*', '/', rpc)

    await event_loop.create_server(
        app.make_handler(), 'localhost', unused_tcp_port)

    # setup clients and watchdog
    tasks = [
        create_client(1, list(range(0, 10))),
        create_client(2, list(range(2, 5)), sleep=0.2),
    ]

    tasks = [
        *tasks,
        asyncio.ensure_future(watchdog(tasks)),
    ]

    # run
    await asyncio.gather(*tasks)

    # checks
    assert Item.objects.filter(client_id=1).count() == 10
    assert not Item.objects.filter(client_id=2).exists()

    assert tasks[0].result() == 0  # client #1
    assert tasks[1].result() == 1  # client #2
    assert tasks[2].result() == 0  # watchdog
