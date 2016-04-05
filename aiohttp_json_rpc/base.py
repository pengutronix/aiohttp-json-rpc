import asyncio
import aiohttp
from aiohttp.web_ws import WebSocketResponse
import importlib
import traceback
import logging
import json
import sys
import os
import io

try:
    from .django import utils as django_utils

    DJANGO = True

except:
    DJANGO = False


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

    def __init__(self, *args, **kwargs):
        self.methods = {}
        self.clients = []

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

    def _get_methods(self, request):
        methods = {}
        user = django_utils.get_user(request) if DJANGO else None

        def run_tests(tests, user):
            for test in tests:
                if not test(user):
                    return False

            return True

        for name, method in self.methods.items():
            if not user and set(dir(method)) & set(['login_required',
                                                    'permissions_required',
                                                    'tests']):
                raise ImportError('Django is not installed')

            # login check
            if hasattr(method, 'login_required') and (
               not user.is_active or not user.is_authenticated()):
                continue

            # permission check
            if hasattr(method, 'permissions_required') and\
               not user.is_superuser and\
               not user.has_perms(method.permissions_required):
                continue

            # user tests
            if hasattr(method, 'tests') and\
               not user.is_superuser and\
               not run_tests(method.tests, user):
                continue

            methods[name] = method

        return user, methods

    @asyncio.coroutine
    def __call__(self, request):
        # check request
        if not self._request_is_valid(request):
            return aiohttp.web.Response(status=403)

        # handle request
        if request.method == 'GET':

            # handle Websocket
            if request.headers.get('upgrade', '') == 'websocket':
                user, methods = self._get_methods(request)

                return (yield from self.handle_websocket_request(
                    request, user, methods))

            # handle GET
            else:
                return aiohttp.web.Response(status=405)

        # handle POST
        elif request.method == 'POST':
            return aiohttp.web.Response(status=405)

    @asyncio.coroutine
    def handle_websocket_request(self, request, user, methods):
        # prepare and register websocket
        ws = JsonWebSocketResponse()
        yield from ws.prepare(request)
        self.clients.append(ws)
        self._on_open(ws)

        while not ws.closed:
            # check and receive message
            msg = yield from ws.receive()

            if not self._msg_is_valid(msg):
                continue

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

                if msg['method'] not in methods:
                    ws.send_error(msg['id'],
                                  ws.METHOD_NOT_FOUND_ERROR,
                                  'Method not found.')

                    continue

                # call method and send response
                try:
                    if msg['method'] == 'get_methods':
                        rsp = yield from self.get_methods(methods)

                    else:
                        context = {
                            'msg': msg,
                            'params': msg.get('params', None),
                            'user': user,
                            'rpc': self,
                            'ws': ws,
                        }

                        rsp = yield from methods[msg['method']](**context)

                    ws.send_response(msg['id'], rsp)

                except RpcInvalidParamsError as e:
                    ws.send_error(msg['id'], ws.INVALID_PARAMS_ERROR,
                                  str(e))

                except Exception as exception:
                    buffer = io.StringIO()
                    traceback.print_exc(file=buffer)
                    buffer.seek(0)

                    for line in buffer.readlines():
                        self.logger.error(line[:-1])

                    self._on_error(ws, msg, exception)
                    ws.send_error(msg['id'], ws.INTERNAL_ERROR,
                                  'Internal error.')

            elif msg.tp == aiohttp.MsgType.close:
                self._on_close(ws)

            elif msg.tp == aiohttp.MsgType.error:
                self._on_error(ws, msg)

        self.clients.remove(ws)
        return ws

    def _request_is_valid(self, request):
        return True

    def _msg_is_valid(self, msg):
        return True

    def _on_open(self, ws):
        pass

    def _on_error(self, ws, msg=None, exception=None):
        pass

    def _on_close(self, ws):
        pass

    @asyncio.coroutine
    def get_methods(self, methods):
        return list(methods.keys())
