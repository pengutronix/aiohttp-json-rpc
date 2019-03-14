from functools import partial


def notify(request, topic, data=None, state=False, wait=False):
    return request.environ['aiohttp.request'].app['rpc'].worker_pool.run_sync(
        partial(request.environ['aiohttp.request'].app['rpc'].notify,
                topic, data, state=state),
        wait=wait,
    )
