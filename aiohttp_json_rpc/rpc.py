from copy import copy
import asyncio
import aiohttp
import importlib
import logging
import inspect
import types

from .communicaton import JsonRpcRequest, SyncJsonRpcRequest
from .threading import ThreadedWorkerPool
from .auth import DummyAuthBackend

from .protocol import (
    encode_notification,
    JsonRpcMsgTyp,
    encode_result,
    encode_error,
    decode_msg,
)

from .exceptions import (
    RpcGenericServerDefinedError,
    RpcInvalidRequestError,
    RpcMethodNotFoundError,
    RpcInvalidParamsError,
    RpcInternalError,
    RpcError,
)


class JsonRpcMethod:
    CREDENTIAL_KEYS = ['request', 'worker_pool']

    def __init__(self, method):
        self.method = method

        # method introspection
        try:
            self.argspec = inspect.getfullargspec(method)
            self.introspected = True

        except TypeError:  # unsupported callable
            self.argspec = inspect.getfullargspec(lambda request: None)
            self.introspected = False

        self.defaults = copy(self.argspec.defaults)

        self.args = [i for i in self.argspec.args
                     if i not in self.CREDENTIAL_KEYS + ['self']]

        # required args
        self.required_args = copy(self.args)

        if not (len(self.args) == 1 and self.defaults is None):
            self.required_args = [
                i for i in self.args[:-len(self.defaults or ())]
                if i not in self.CREDENTIAL_KEYS
            ]

        # optional args
        self.optional_args = [
            i for i in (self.args[len(self.args or []) -
                        len(self.defaults or ()):])
            if i not in self.CREDENTIAL_KEYS + ['self']
        ]

        # gen repr string
        args = []

        for i, v in enumerate(self.args[::-1]):
            if self.defaults and not i >= len(self.defaults):
                args.append('{}={}'.format(v, repr(self.defaults[i])))

            else:
                args.append(v)

        args = [
            *[i for i in self.CREDENTIAL_KEYS if i in self.argspec.args],
            *args[::-1],
        ]

        self._repr_str = 'JsonRpcMethod({}({}))'.format(
            self.method.__name__,
            ', '.join(args),
        )

    def __repr__(self):
        return self._repr_str

    async def __call__(self, http_request, rpc, msg):
        params = msg.data['params']
        method_params = dict()

        # convert args
        if params is None:
            params = {}

        if type(params) not in (dict, list):
            params = [params]

        if type(params) == list:
            params = {self.args[i]: v for i, v in enumerate(params)
                      if i < len(self.args)}

        # required args
        for i in self.required_args:
            if i not in params:
                raise RpcInvalidParamsError(message='to few arguments')

            method_params[i] = params[i]

        # optional args
        for i, v in enumerate(self.optional_args):
            method_params[v] = params.get(v, self.defaults[i])

        # validators
        if hasattr(self.method, 'validators'):
            for arg_name, validator_list in self.method.validators.items():
                if not isinstance(validator_list, (list, tuple)):
                    validator_list = [validator_list]

                for validator in validator_list:
                    if isinstance(validator, type):
                        if not isinstance(method_params[arg_name], validator):
                            raise RpcInvalidParamsError(message="'{}' has to be '{}'".format(arg_name, validator.__name__))  # NOQA

                    elif isinstance(validator, types.FunctionType):
                        if not validator(method_params[arg_name]):
                            raise RpcInvalidParamsError(message="'{}': validation error".format(arg_name))  # NOQA

        # credentials
        if 'request' in self.argspec.args:
            if asyncio.iscoroutinefunction(self.method):
                method_params['request'] = JsonRpcRequest(
                    rpc=rpc, http_request=http_request, msg=msg)

            else:
                method_params['request'] = SyncJsonRpcRequest(
                    rpc=rpc, http_request=http_request, msg=msg)

        if 'worker_pool' in self.argspec.args:
            method_params['worker_pool'] = rpc.worker_pool

        # run method
        if asyncio.iscoroutinefunction(self.method):
            return await self.method(**method_params)

        else:
            return await rpc.worker_pool.run(self.method, **method_params)


class JsonRpc(object):
    def __init__(self, loop=None, max_workers=0, auth_backend=None,
                 logger=None):

        self.clients = []
        self.methods = {}
        self.topics = {}
        self.state = {}
        self.logger = logger or logging.getLogger('aiohttp-json-rpc.server')
        self.auth_backend = auth_backend or DummyAuthBackend()
        self.loop = loop or asyncio.get_event_loop()
        self.worker_pool = ThreadedWorkerPool(max_workers=max_workers)

        self.add_methods(
            ('', self.get_methods),
            ('', self.get_topics),
            ('', self.get_subscriptions),
            ('', self.subscribe),
            ('', self.unsubscribe),
        )

    def _add_method(self, method, name='', prefix=''):
        if not callable(method):
            return

        name = name or method.__name__

        if prefix:
            name = '{}__{}'.format(prefix, name)

        self.methods[name] = JsonRpcMethod(method)

    def _add_methods_from_object(self, obj, prefix='', ignore=[]):
        for attr_name in dir(obj):
            if attr_name.startswith('_') or attr_name in ignore:
                continue

            self._add_method(getattr(obj, attr_name), prefix=prefix)

    def _add_methods_by_name(self, name, prefix=''):
        try:
            module = importlib.import_module(name)
            self._add_methods_from_object(module, prefix=prefix)

        except ImportError:
            name = name.split('.')
            module = importlib.import_module('.'.join(name[:-1]))

            self._add_method(getattr(module, name[-1]), prefix=prefix)

    def add_methods(self, *args, prefix=''):
        for arg in args:
            if not (type(arg) == tuple and len(arg) >= 2):
                raise ValueError('invalid format')

            if not type(arg[0]) == str:
                raise ValueError('prefix has to be str')

            prefix_ = prefix or arg[0]
            method = arg[1]

            if callable(method):
                name = arg[2] if len(arg) >= 3 else ''
                self._add_method(method, name=name, prefix=prefix_)

            elif type(method) == str:
                self._add_methods_by_name(method, prefix=prefix_)

            else:
                self._add_methods_from_object(method, prefix=prefix_)

    def add_topics(self, *topics):
        for topic in topics:
            if type(topic) not in (str, tuple):
                raise ValueError('Topic has to be string or tuple')

            # find name
            if type(topic) == str:
                name = topic

            else:
                name = topic[0]

            # find and apply decorators
            def func(request):
                return True

            if type(topic) == tuple and len(topic) > 1:
                decorators = topic[1]

                if not type(decorators) == tuple:
                    decorators = (decorators, )

                for decorator in decorators:
                    func = decorator(func)

            self.topics[name] = func

    async def __call__(self, request):
        # prepare request
        request.rpc = self
        self.auth_backend.prepare_request(request)

        # handle request
        if request.method == 'GET':

            # handle Websocket
            if request.headers.get('upgrade', '').lower() == 'websocket':
                return (await self.handle_websocket_request(request))

            # handle GET
            else:
                return aiohttp.web.Response(status=405)

        # handle POST
        elif request.method == 'POST':
            return aiohttp.web.Response(status=405)

    async def _ws_send_str(self, client, string):
        if client.ws._writer.transport.is_closing():
            self.clients.remove(client)
            await client.ws.close()

        await client.ws.send_str(string)

    async def _handle_rpc_msg(self, http_request, raw_msg):
        try:
            msg = decode_msg(raw_msg.data)
            self.logger.debug('message decoded: %s', msg)

        except RpcError as error:
            await self._ws_send_str(http_request, encode_error(error))

            return

        # handle requests
        if msg.type == JsonRpcMsgTyp.REQUEST:
            self.logger.debug('msg gets handled as request')

            # check if method is available
            if msg.data['method'] not in http_request.methods:
                self.logger.debug('method %s is unknown or restricted',
                                  msg.data['method'])

                await self._ws_send_str(http_request, encode_error(
                    RpcMethodNotFoundError(msg_id=msg.data.get('id', None))
                ))

                return

            # call method
            raw_response = getattr(
                http_request.methods[msg.data['method']].method,
                'raw_response',
                False,
            )

            try:
                result = await http_request.methods[msg.data['method']](
                    http_request=http_request,
                    rpc=self,
                    msg=msg,
                )

                if not raw_response:
                    result = encode_result(msg.data['id'], result)

                await self._ws_send_str(http_request, result)

            except (RpcGenericServerDefinedError,
                    RpcInvalidRequestError,
                    RpcInvalidParamsError) as error:

                await self._ws_send_str(
                    http_request,
                    encode_error(error, id=msg.data.get('id', None))
                )

            except Exception as error:
                logging.error(error, exc_info=True)

                await self._ws_send_str(http_request, encode_error(
                    RpcInternalError(msg_id=msg.data.get('id', None))
                ))

        # handle result
        elif msg.type == JsonRpcMsgTyp.RESULT:
            self.logger.debug('msg gets handled as result')

            http_request.pending[msg.data['id']].set_result(
                msg.data['result'])

        else:
            self.logger.debug('unsupported msg type (%s)', msg.type)

            await self._ws_send_str(http_request, encode_error(
                RpcInvalidRequestError(msg_id=msg.data.get('id', None))
            ))

    async def handle_websocket_request(self, http_request):
        http_request.msg_id = 0
        http_request.pending = {}

        # prepare and register websocket
        ws = aiohttp.web_ws.WebSocketResponse()
        await ws.prepare(http_request)
        http_request.ws = ws
        self.clients.append(http_request)

        while not ws.closed:
            self.logger.debug('waiting for messages')
            raw_msg = await ws.receive()

            if not raw_msg.type == aiohttp.WSMsgType.TEXT:
                continue

            self.logger.debug('raw msg received: %s', raw_msg.data)
            self.loop.create_task(self._handle_rpc_msg(http_request, raw_msg))

        self.clients.remove(http_request)
        return ws

    async def get_methods(self, request):
        return list(request.methods.keys())

    async def get_topics(self, request):
        return list(request.topics)

    async def get_subscriptions(self, request):
        return list(request.subscriptions)

    async def subscribe(self, request):
        if type(request.params) is not list:
            request.params = [request.params]

        for topic in request.params:
            if topic and topic in request.topics:
                request.subscriptions.add(topic)

                if topic in self.state:
                    await request.send_notification(topic, self.state[topic])

        return list(request.subscriptions)

    async def unsubscribe(self, request):
        if type(request.params) is not list:
            request.params = [request.params]

        for topic in request.params:
            if topic and topic in request.subscriptions:
                request.subscriptions.remove(topic)

        return list(request.subscriptions)

    def filter(self, topics):
        if type(topics) is not list:
            topics = [topics]

        topics = set(topics)

        for client in self.clients:
            if client.ws.closed:
                continue

            if len(topics & client.subscriptions) > 0:
                yield client

    async def notify(self, topic, data=None):
        if type(topic) is not str:
            raise ValueError

        self.state[topic] = data
        notification = None
        for client in self.filter(topic):
            try:
                if notification is None:
                    notification = encode_notification(topic, data)
                await self._ws_send_str(client, notification)
            except Exception as e:
                self.logger.exception(e)
