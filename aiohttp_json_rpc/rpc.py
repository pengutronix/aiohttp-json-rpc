import asyncio
import aiohttp
import importlib
import logging

from .protocol import JsonRpcMsgTyp, decode_msg, encode_result, encode_error
from .websocket import JsonWebSocketResponse
from .communicaton import JsonRpcRequest
from .auth import DummyAuthBackend

from .exceptions import (
    RpcInvalidRequestError,
    RpcMethodNotFoundError,
    RpcInvalidParamsError,
    RpcInternalError,
    RpcError,
)


class JsonRpc(object):
    def __init__(self, auth_backend=None, logger=None):
        self.clients = []
        self.methods = {}
        self.topics = {}
        self.state = {}
        self.logger = logging.getLogger('aiohttp-json-rpc.server')

        # auth backend
        if not auth_backend:
            self.auth_backend = DummyAuthBackend()

        else:
            self.auth_backend = auth_backend

        # methods
        self.add_methods(
            ('', self.get_methods),
            ('', self.get_topics),
            ('', self.get_subscriptions),
            ('', self.subscribe),
            ('', self.unsubscribe),
        )

    def _add_method(self, method, prefix=''):
        if not asyncio.iscoroutinefunction(method):
            return

        name = method.__name__

        if prefix:
            name = '{}__{}'.format(prefix, name)

        self.methods[name] = method

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

            prefix = prefix or arg[0]
            method = arg[1]

            if asyncio.iscoroutinefunction(method):
                self._add_method(method, prefix=prefix)

            elif type(method) == str:
                self._add_methods_by_name(method, prefix=prefix)

            else:
                self._add_methods_from_object(method, prefix=prefix)

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

    @asyncio.coroutine
    def __call__(self, request):
        # prepare request
        request.rpc = self
        self.auth_backend.prepare_request(request)

        # handle request
        if request.method == 'GET':

            # handle Websocket
            if request.headers.get('upgrade', '').lower() == 'websocket':
                return (yield from self.handle_websocket_request(request))

            # handle GET
            else:
                return aiohttp.web.Response(status=405)

        # handle POST
        elif request.method == 'POST':
            return aiohttp.web.Response(status=405)

    async def _handle_rpc_msg(self, http_request, raw_msg):
        try:
            msg = decode_msg(raw_msg.data)
            self.logger.debug('message decoded: %s', msg)

        except RpcError as error:
            http_request.ws.send_str(encode_error(error))

            return

        # handle requests
        if msg.type == JsonRpcMsgTyp.REQUEST:
            self.logger.debug('msg gets handled as request')

            # check if method is available
            if msg.data['method'] not in http_request.methods:
                self.logger.debug('method %s is unknown or restricted',
                                  msg.data['method'])

                http_request.ws.send_str(encode_error(
                    RpcMethodNotFoundError(msg_id=msg.data.get('id', None))
                ))

                return

            # call method
            try:
                json_rpc_request = JsonRpcRequest(
                    http_request=http_request,
                    rpc=self,
                    msg=msg,
                )

                result = await http_request.methods[msg.data['method']](
                    json_rpc_request)

                http_request.ws.send_str(encode_result(msg.data['id'], result))

            except (RpcInvalidParamsError,
                    RpcInvalidRequestError) as error:

                http_request.ws.send_str(encode_error(error))

            except Exception as error:
                logging.error(error, exc_info=True)

                http_request.ws.send_str(encode_error(
                    RpcInternalError(msg_id=msg.data.get('id', None))
                ))

        # handle result
        elif msg.type == JsonRpcMsgTyp.RESULT:
            self.logger.debug('msg gets handled as result')

            http_request.pending[msg.data['id']].set_result(
                msg.data['result'])

        else:
            self.logger.debug('unsupported msg type (%s)', msg.type)

            http_request.ws.send_str(encode_error(
                RpcInvalidRequestError(msg_id=msg.data.get('id', None))
            ))

    async def handle_websocket_request(self, http_request):
        loop = asyncio.get_event_loop()

        http_request.msg_id = 0
        http_request.pending = {}

        # prepare and register websocket
        ws = JsonWebSocketResponse()
        await ws.prepare(http_request)
        http_request.ws = ws
        self.clients.append(http_request)

        while not ws.closed:
            self.logger.debug('waiting for messages')
            raw_msg = await ws.receive()

            if not raw_msg.tp == aiohttp.WSMsgType.TEXT:
                continue

            self.logger.debug('raw msg received: %s', raw_msg.data)
            loop.create_task(self._handle_rpc_msg(http_request, raw_msg))

        self.clients.remove(http_request)
        return ws

    @asyncio.coroutine
    def get_methods(self, request):
        return list(request.methods.keys())

    @asyncio.coroutine
    def get_topics(self, request):
        return list(request.topics)

    @asyncio.coroutine
    def get_subscriptions(self, request):
        return list(request.subscriptions)

    @asyncio.coroutine
    def subscribe(self, request):
        if type(request.params) is not list:
            request.params = [request.params]

        for topic in request.params:
            if topic and topic in request.topics:
                request.subscriptions.add(topic)

                if topic in self.state:
                    request.ws.send_notification(topic, self.state[topic])

        return list(request.subscriptions)

    @asyncio.coroutine
    def unsubscribe(self, request):
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
            if not client.ws:
                continue

            if len(topics & client.subscriptions) > 0:
                yield client

    def notify(self, topic, data=None):
        if type(topic) is not str:
            raise ValueError

        self.state[topic] = data

        for client in self.filter(topic):
            if not client.ws.closed:
                try:
                    client.ws.send_notification(topic, data)

                except Exception as e:
                    self.logger.exception(e)
