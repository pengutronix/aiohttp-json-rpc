from aiohttp_json_rpc.django.auth.decorators import login_required


@login_required
async def ping(ws, params):
    return 'pong'
