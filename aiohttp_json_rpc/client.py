import aiohttp
import asyncio
import logging

from yarl import URL

from . import exceptions

from .protocol import (
    JsonRpcMsgTyp,
    encode_request,
    encode_error,
    decode_error,
    encode_result,
    decode_msg,
)


default_logger = logging.getLogger('aiohttp-json-rpc.client')


class JsonRpcClient:
    _client_id = 0

    def __init__(self, logger=default_logger, url=None, cookies=None,
                 loop=None):

        self._pending = {}
        self._msg_id = 0
        self._logger = logger
        self._handler = {}
        self._methods = {}
        self._autoconnect_url = URL(url) if url is not None else url
        self._autoconnect_cookies = cookies
        self._loop = loop or asyncio.get_event_loop()

        self._id = JsonRpcClient._client_id
        JsonRpcClient._client_id += 1

    def add_methods(self, *methods):
        for prefix, method in methods:
            name = method.__name__

            if prefix:
                name = '{}__{}'.format(prefix, name)

            self._methods[name] = method

    async def _handle_request(self, msg):
        if not msg.data['method'] in self._methods:
            response = encode_error(
                exceptions.RpcMethodNotFoundError(
                    msg_id=msg.data.get('id', None)))

        else:
            result = await self._methods[msg.data['method']](
                msg.data['params'])

            response = encode_result(msg.data['id'], result)

        self._logger.debug('#%s: > %s', self._id, response)
        await self._ws.send_str(response)

    async def _handle_msgs(self):
        self._logger.debug('#%s: worker start...', self._id)

        while not self._ws.closed:
            try:
                self._logger.debug('#%s: waiting for messages', self._id)
                raw_msg = await self._ws.receive()

                self._logger.debug('#%s: < %s', self._id, raw_msg.data)

                if raw_msg.type != aiohttp.WSMsgType.text:
                    continue

                msg = decode_msg(raw_msg.data)

                # requests
                if msg.type == JsonRpcMsgTyp.REQUEST:
                    self._logger.debug('#%s: handled as request', self._id)
                    await self._handle_request(msg)
                    self._logger.debug('#%s: handled', self._id)

                # notifications
                elif msg.type == JsonRpcMsgTyp.NOTIFICATION:
                    self._logger.debug('#%s: handled as notification', self._id)  # NOQA

                    if msg.data['method'] in self._handler:
                        await self._handler[msg.data['method']](msg.data)

                        self._logger.debug('#%s: handled', self._id)

                    else:
                        self._logger.debug('#%s: no handler found', self._id)

                # results
                elif msg.type == JsonRpcMsgTyp.RESULT:
                    if msg.data['id'] in self._pending:
                        self._pending[msg.data['id']].set_result(
                            msg.data['result'])

                # errors
                elif msg.type == JsonRpcMsgTyp.ERROR:
                    if msg.data['id'] in self._pending:
                        self._pending[msg.data['id']].set_exception(
                            decode_error(msg)
                        )

            except asyncio.CancelledError:
                raise

            except Exception as e:
                self._logger.error(e, exc_info=True)

        self._logger.debug('#%s: worker stopped', self._id)

    async def connect_url(self, url, cookies=None):
        url = URL(url)
        self._session = aiohttp.ClientSession(cookies=cookies, loop=self._loop)

        self._logger.debug('#%s: ws connect...', self._id)
        self._ws = None
        try:
            self._ws = await self._session.ws_connect(url)
        finally:
            if self._ws is None:
                # Ensure session is closed when connection failed
                await self._session.close()
        self._logger.debug('#%s: ws connected', self._id)

        self._message_worker = asyncio.ensure_future(self._handle_msgs())

    async def connect(self, host, port, url='/', protocol='ws', cookies=None):
        url = URL.build(scheme=protocol, host=host, port=port, path=url)
        await self.connect_url(url, cookies=cookies)

    async def auto_connect(self):
        if self._autoconnect_url is None:
            return

        try:
            self._ws
            return
        except AttributeError:
            await self.connect_url(
                url=self._autoconnect_url,
                cookies=self._autoconnect_cookies,
            )

    async def disconnect(self):
        await self._ws.close()
        await self._session.close()
        del self._ws
        del self._session

    async def call(self, method, params=None, id=None, timeout=1):
        await self.auto_connect()

        if not id:
            id = self._msg_id
            self._msg_id += 1

        self._pending[id] = asyncio.Future()
        msg = encode_request(method, id=id, params=params)

        self._logger.debug('#%s: > %s', self._id, msg)
        await self._ws.send_str(msg)

        if timeout:
            await asyncio.wait_for(self._pending[id], timeout=timeout)

        else:
            await self._pending[id]

        result = self._pending[id].result()
        del self._pending[id]

        return result

    async def get_methods(self, timeout=None):
        return await self.call('get_methods', timeout=timeout)

    async def get_topics(self, timeout=None):
        return await self.call('get_topics', timeout=timeout)

    async def get_subscriptions(self, timeout=None):
        return await self.call('get_subscriptions', timeout=timeout)

    async def subscribe(self, topic, handler, timeout=None):
        self._handler[topic] = handler

        return await self.call('subscribe', params=topic, timeout=timeout)

    async def unsubscribe(self, topic, timeout=None):
        if topic in self._handler:
            del self._handler[topic]

        return await self.call('unsubscribe', params=topic, timeout=timeout)


class JsonRpcMethod:
    """JSON-RPC callable awaitable method representation.

    Example usage:

    >>> import asyncio
    >>> from .rpc import JsonRpc
    >>> from .pytest import gen_rpc_context
    >>> event_loop = asyncio.get_event_loop()
    >>> rpc = JsonRpc()
    >>> rpc_context_gen = gen_rpc_context(event_loop, 'localhost', 8000,
    ...                                   rpc, ('*', '/rpc', rpc))
    >>> rpc_context = next(rpc_context_gen)
    >>> async def method1(request):
    ...     return 'res1'
    >>> async def method2(request):
    ...     return ('res2 | args: {args} | kwargs: {kwargs}'.
    ...             format(**request.params))
    >>> rpc_context.rpc.add_methods(
    ...     ('', method1),
    ...     ('', method2),
    ... )
    >>> async def jrpc_method_coro():
    ...     jrpc = JsonRpcClient()
    ...     await jrpc.connect_url('ws://localhost:8000/rpc')
    ...     rpc_method1 = JsonRpcMethod(jrpc, 'method1')
    ...     print(await rpc_method1)
    ...     print(await rpc_method1())
    ...     rpc_method2 = JsonRpcMethod(jrpc, 'method2')
    ...     print(await rpc_method2('arg1', key='arg2'))
    ...     await jrpc.disconnect()
    >>> event_loop.run_until_complete(jrpc_method_coro())
    res1
    res1
    res2 | args: ['arg1'] | kwargs: {'key': 'arg2'}
    >>> try:
    ...     next(rpc_context_gen)  # clean-up
    ... except StopIteration:
    ...     pass
    """

    def __init__(self, rpc_client, rpc_method, args=None, kwargs=None):
        self._rpc_client = rpc_client
        self._rpc_method = rpc_method
        self._args = args if args is not None else []
        self._kwargs = kwargs if kwargs is not None else {}

    @property
    def _await_args(self):
        return []

    @property
    def _await_kwargs(self):
        return {
            'params': {
                'args': self._args,
                'kwargs': self._kwargs
            }
        }

    def __await__(self):
        return (
            self._rpc_client.
            call(
                self._rpc_method,
                *self._await_args,
                **self._await_kwargs,
            ).__await__()
        )

    def __call__(self, *args, **kwargs):
        return self.__class__(self._rpc_client, self._rpc_method, args, kwargs)


class RawJsonRpcMethod(JsonRpcMethod):
    """JSON-RPC awaitable method representation with call() args bypassing.

    Example usage:

    >>> import asyncio
    >>> from .rpc import JsonRpc
    >>> from .pytest import gen_rpc_context
    >>> event_loop = asyncio.get_event_loop()
    >>> rpc = JsonRpc()
    >>> rpc_context_gen = gen_rpc_context(event_loop, 'localhost', 8000,
    ...                                   rpc, ('*', '/rpc', rpc))
    >>> rpc_context = next(rpc_context_gen)
    >>> async def method1(request):
    ...     return 'res1'
    >>> async def method2(request):
    ...     return ('res2 | args: {args} | kwargs: {kwargs}'.
    ...             format(**request.params))
    >>> rpc_context.rpc.add_methods(
    ...     ('', method1),
    ...     ('', method2),
    ... )
    >>> async def jrpc_method_coro():
    ...     jrpc = JsonRpcClient()
    ...     await jrpc.connect_url('ws://localhost:8000/rpc')
    ...     rpc_method1 = RawJsonRpcMethod(jrpc, 'method1')
    ...     print(await rpc_method1(id=3))
    ...     rpc_method2 = RawJsonRpcMethod(jrpc, 'method2')
    ...     print(
    ...         await rpc_method2(
    ...             params={
    ...                 'args': ['arg1'],
    ...                 'kwargs': {'key': 'arg2'},
    ...             },
    ...             timeout=60.0
    ...         )
    ...     )
    ...     await jrpc.disconnect()
    >>> event_loop.run_until_complete(jrpc_method_coro())
    res1
    res2 | args: ['arg1'] | kwargs: {'key': 'arg2'}
    >>> try:
    ...     next(rpc_context_gen)  # clean-up
    ... except StopIteration:
    ...     pass
    """

    @property
    def _await_args(self):
        return self._args

    @property
    def _await_kwargs(self):
        return self._kwargs

    def __call__(self, params=None, id=None, timeout=None):
        return self.__class__(
            self._rpc_client, self._rpc_method,
            kwargs={
                'params': params,
                'id': id,
                'timeout': timeout,
            },
        )


class JsonRpcClientContext:
    """JSON-RPC connection asynchronous context manager.

    Example usage:

    >>> import asyncio
    >>> from yarl import URL
    >>> from .rpc import JsonRpc
    >>> from .pytest import gen_rpc_context
    >>> event_loop = asyncio.get_event_loop()
    >>> rpc = JsonRpc()
    >>> rpc_context_gen = gen_rpc_context(event_loop, 'localhost', 8000,
    ...                                   rpc, ('*', '/rpc', rpc))
    >>> rpc_context = next(rpc_context_gen)
    >>> async def method1(request):
    ...     return 'res1'
    >>> async def method2(request):
    ...     return ('res2 | args: {args} | kwargs: {kwargs}'.
    ...             format(**request.params))
    >>> rpc_context.rpc.add_methods(
    ...     ('', method1),
    ...     ('', method2),
    ... )
    >>> async def jrpc_coro():
    ...     jrpc_url = URL('ws://localhost:8000/rpc')
    ...     async with JsonRpcClientContext(jrpc_url) as jrpc:
    ...         print(await jrpc.method1)
    ...         print(await jrpc.method1())
    ...         print(await jrpc.method2('arg1', key='arg2'))
    >>> event_loop.run_until_complete(jrpc_coro())
    res1
    res1
    res2 | args: ['arg1'] | kwargs: {'key': 'arg2'}
    >>> try:
    ...     next(rpc_context_gen)  # clean-up
    ... except StopIteration:
    ...     pass
    """

    def __init__(self, rpc_url, rpc_cookies=None):
        self._rpc_client = JsonRpcClient()
        self._rpc_url = rpc_url
        self._rpc_cookies = rpc_cookies

    def __getattr__(self, rpc_name):
        return JsonRpcMethod(self._rpc_client, rpc_name)

    async def __aenter__(self):
        await self._rpc_client.connect_url(
            url=self._rpc_url,
            cookies=self._rpc_cookies,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._rpc_client.disconnect()
        return False
