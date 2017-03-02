import asyncio

from aiohttp_json_rpc.auth import login_required


@login_required
@asyncio.coroutine
def ping(request):
    return 'pong'
