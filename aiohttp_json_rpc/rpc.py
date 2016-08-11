import asyncio
import aiohttp
from aiohttp.web_ws import WebSocketResponse
import importlib
import traceback
import logging
import json
import io

from .auth import DummyAuthBackend


class RpcError(Exception):
    def __init__(self, message=''):
        self.message = message

    def __str__(self):
        return str(self.message)


class RpcInvalidRequestError(RpcError):
    def __init__(self, message='Invalid request'):
        self.message = message


class RpcInvalidParamsError(RpcError):
    def __init__(self, message='Invalid params'):
        self.message = message


class JsonWebSocketResponse(WebSocketResponse):
    JSONRPC = '2.0'
    PARSE_ERROR = -32700
    INVALID_REQUEST_ERROR = -32600
    METHOD_NOT_FOUND_ERROR = -32601
    INVALID_PARAMS_ERROR = -32602
    INTERNAL_ERROR = -32603

    def send_request(self, id, method, params=None):
        message = {
            'jsonrpc': self.JSONRPC,
            'id': id,
            'method': method,
        }

        if params:
            message['params'] = params

        message = json.dumps(message)
        return self.send_str(message)

    def send_response(self, id, result):
        message = {
            'id': id,
            'jsonrpc': self.JSONRPC,
            'result': result,
        }

        message = json.dumps(message)
        return self.send_str(message)

    def send_error(self, id, code, message, data=None):
        message = {
            'jsonrpc': self.JSONRPC,
            'id': id,
            'error': {
                'code': code,
                'message': message,
            },
        }

        if data:
            message['error']['data'] = data

        message = json.dumps(message)
        return self.send_str(message)

    def send_notification(self, method, params=None):
        return self.send_request(None, method, params)


class JsonRpc(object):
    IGNORED_METHODS = [
        'handle_websocket_request',
    ]

    def __init__(self, auth_backend=None):
        self.clients = []
        self.methods = {}
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

        # find rpc-methods
        self._add_methods_from_object(self, ignore=self.IGNORED_METHODS)

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

    @asyncio.coroutine
    def __call__(self, request):
        # prepare request
        request.rpc = self
        self.auth_backend.prepare_request(request)

        # handle request
        if request.method == 'GET':

            # handle Websocket
            if request.headers.get('upgrade', '') == 'websocket':
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
        self.clients.append(ws)

        while not ws.closed:
            # check and receive message
            msg = yield from ws.receive()

            # handle message
            if msg.tp == aiohttp.MsgType.text:

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
                    if msg['method'] == 'get_methods':
                        rsp = yield from self.get_methods(request)

                    else:
                        context = {
                            'msg': msg,
                            'params': msg.get('params', None),
                            'rpc': self,
                            'ws': ws,
                        }

                        rsp = yield from request.methods[msg['method']](
                            **context)

                    ws.send_response(msg['id'], rsp)

                except RpcInvalidParamsError as e:
                    ws.send_error(msg['id'], ws.INVALID_PARAMS_ERROR, str(e))

                except RpcInvalidRequestError as e:
                    ws.send_error(msg['id'], ws.INVALID_REQUEST_ERROR, str(e))

                except Exception as exception:
                    buffer = io.StringIO()
                    traceback.print_exc(file=buffer)
                    buffer.seek(0)

                    for line in buffer.readlines():
                        self.logger.error(line[:-1])

                    ws.send_error(msg['id'], ws.INTERNAL_ERROR,
                                  'Internal error.')

        self.clients.remove(ws)
        return ws

    @asyncio.coroutine
    def get_methods(self, request):
        return list(request.methods.keys())

    @asyncio.coroutine
    def subscribe(self, params, ws, **kwargs):
        if not hasattr(ws, 'topics'):
            ws.topics = set()

        if type(params) is not list:
            params = [params]

        for topic in params:
            if topic and topic not in ws.topics:
                ws.topics.add(topic)

                if topic in self.state:
                    ws.send_notification(topic, self.state[topic])

        return True

    @asyncio.coroutine
    def unsubscribe(self, params, **kwargs):
        if not hasattr(kwargs['ws'], 'topics'):
            kwargs['ws'].topics = set()

            return True

        if type(params) is not list:
            params = [params]

        for topic in params:
            if topic in kwargs['ws'].topics:
                kwargs['ws'].topics.remove(topic)

        return True

    @asyncio.coroutine
    def get_topics(self, params, **kwargs):
        return list(getattr(kwargs['ws'], 'topics', set()))

    def filter(self, topics):
        if type(topics) is not list:
            topics = [topics]

        topics = set(topics)

        for client in self.clients:
            if not hasattr(client, 'topics'):
                continue

            if len(topics & client.topics) > 0:
                yield client

    def notify(self, topic, data=None):
        if type(topic) is not str:
            raise ValueError

        self.state[topic] = data

        for client in self.filter(topic):
            client.send_notification(topic, data)
