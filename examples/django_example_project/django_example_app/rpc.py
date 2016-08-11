from aiohttp_json_rpc.auth import login_required


@login_required
async def ping(request):
    return 'pong'
