import asyncio
import aiohttp
import importlib
import logging
import json

from .exceptions import RpcInvalidRequestError, RpcInvalidParamsError
from .websocket import JsonWebSocketResponse
from .communicaton import JsonRpcRequest
from .auth import DummyAuthBackend


class JsonRpc(object):
    def __init__(self, auth_backend=None):
        self.clients = []
        self.methods = {}
        self.topics = {}
        self.state = {}

        # auth backend
        if not auth_backend:
            self.auth_backend = DummyAuthBackend()

        else:
            self.auth_backend = auth_backend

        # setup logging
        formatter = logging.Formatter(
            fmt='%(levelname)s:{}: %(message)s'.format(
                self.__class__.__name__)
        )

        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.addHandler(handler)

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

    @asyncio.coroutine
    def handle_websocket_request(self, request):
        # prepare and register websocket
        ws = JsonWebSocketResponse()
        yield from ws.prepare(request)
        request.ws = ws
        self.clients.append(request)

        while not ws.closed:
            # check and receive message
            msg = yield from ws.receive()

            # handle message
            if msg.tp == aiohttp.WSMsgType.TEXT:

                # parse json
                try:
                    msg = json.loads(msg.data)

                    if 'id' not in msg:
                        msg['id'] = None

                    if 'params' not in msg:
                        msg['params'] = []

                except ValueError:
                    ws.send_error(None, ws.PARSE_ERROR,
                                  'Invalid JSON was received.')
                    continue

                # check args
                if not {'jsonrpc', 'method'} <= set(msg):
                    ws.send_error(
                        msg['id'], ws.INVALID_REQUEST_ERROR,
                        'Invalid request.')

                    continue

                if not type(msg['method']) == str:
                    ws.send_error(msg['id'],
                                  ws.INVALID_REQUEST_ERROR,
                                  'Method has to be a string.')

                    continue

                if msg['method'] not in request.methods:
                    ws.send_error(msg['id'],
                                  ws.METHOD_NOT_FOUND_ERROR,
                                  'Method not found.')

                    continue

                # call method and send response
                try:
                    json_rpc_request = JsonRpcRequest(
                        http_request=request,
                        rpc=self,
                        msg=msg,
                    )

                    response = yield from request.methods[msg['method']](
                        json_rpc_request)

                    ws.send_response(msg['id'], response)

                except RpcInvalidParamsError as e:
                    ws.send_error(msg['id'], ws.INVALID_PARAMS_ERROR, str(e))

                except RpcInvalidRequestError as e:
                    ws.send_error(msg['id'], ws.INVALID_REQUEST_ERROR, str(e))

                except Exception as e:
                    logging.error(e, exc_info=True)

                    ws.send_error(msg['id'], ws.INTERNAL_ERROR,
                                  'Internal error.')

        self.clients.remove(request)
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
