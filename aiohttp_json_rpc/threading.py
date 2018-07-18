from concurrent.futures import ThreadPoolExecutor
from functools import partial
import asyncio


class ThreadedWorkerPool:
    def __init__(self, max_workers, loop=None):
        self.loop = loop or asyncio.get_event_loop()

        if max_workers > 0:
            self.executor = ThreadPoolExecutor(max_workers=max_workers)

        else:
            self.executor = None

    async def run(self, func, *args, **kwargs):
        if not isinstance(func, partial):
            func = partial(func, *args, **kwargs)

        if not self.executor:
            return func()

        def _run(func, *args):
            try:
                future.set_result(func())

            except Exception as e:
                future.set_exception(e)

        future = asyncio.Future()
        self.loop.run_in_executor(self.executor, _run, func)

        return await future

    def run_sync(self, coro, *args, wait=True, **kwargs):
        if not isinstance(coro, partial):
            coro = partial(coro, *args, **kwargs)

        future = asyncio.run_coroutine_threadsafe(coro(), loop=self.loop)

        if wait:
            return future.result()

        return future

    def shutdown(self, wait=True):
        if self.executor:
            self.executor.shutdown(wait=wait)
