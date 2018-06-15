import asyncio

from aiohttp_json_rpc.client import JsonRpcClient


async def handler(data):
    if data['method'] == 'clock':
        print(data)


async def run():
    message = asyncio.Future()
    client = JsonRpcClient()
    await client.connect_url('ws://127.0.0.1:8080/')
    await client.subscribe('clock', handler)
    await asyncio.sleep(5)
    await client.disconnect()


def main():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run())


if __name__ == '__main__':
    main()
