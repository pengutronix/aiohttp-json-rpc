import asyncio
import aiohttp
from aiohttp.web_ws import WebSocketResponse
import logging
import json
import sys
import os


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

    def send_notification(self, method, params):
        return self.send_request(None, method, params)


class JsonRpc(object):
    WEBSOCKET_CLASS = JsonWebSocketResponse
    IGNORED_METHODS = [
        'handle_websocket_request',
    ]

    def __init__(self, *args, **kwargs):
        self.methods = {}
        self.clients = []

        # find rpc-methods
        for i in dir(self):
            if i.startswith('_') or i in self.IGNORED_METHODS:
                continue

            attr = getattr(self, i)

            if asyncio.iscoroutinefunction(attr):
                self.methods[i] = getattr(self, i)

    @asyncio.coroutine
    def __call__(self, request):
        # check request
        if not self._request_is_valid(request):
            return aiohttp.web.Response(status=403)

        # handle request
        if request.method == 'GET':

            # handle Websocket
            if request.headers.get('upgrade', '') == 'websocket':
                return (yield from self.handle_websocket_request(request))

            # handle GET
            else:
                return aiohttp.web.Response()

        # handle POST
        elif request.method == 'POST':
            return aiohttp.web.Response()

    @asyncio.coroutine
    def handle_websocket_request(self, request):

        # prepare and register websocket
        ws = self.WEBSOCKET_CLASS()
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

                if msg['method'] not in self.methods:
                    ws.send_error(msg['id'],
                                  ws.METHOD_NOT_FOUND_ERROR,
                                  'Method not found.')

                    continue

                # performing response
                try:
                    rsp = yield from self.methods[msg['method']](ws, msg)

                    ws.send_response(msg['id'], rsp)

                except RpcInvalidRequestError as e:
                    ws.send_error(msg['id'], ws.INVALID_REQUEST_ERROR,
                                  str(e))

                except RpcInvalidParamsError as e:
                    ws.send_error(msg['id'], ws.INVALID_PARAMS_ERROR,
                                  str(e))

                except Exception as exception:
                    exc_type, exc_value, exc_traceback = sys.exc_info()

                    while exc_traceback.tb_next:
                        exc_traceback = exc_traceback.tb_next

                    logging.error('{}.{}: {}: {} "{}:{}"'.format(
                        self.__class__.__name__,
                        msg['method'],
                        exc_type.__name__,
                        exc_value,
                        os.path.abspath(
                            exc_traceback.tb_frame.f_code.co_filename),
                        exc_traceback.tb_lineno)
                    )

                    self._on_error(ws, msg, exception)

            elif msg.tp == aiohttp.MsgType.close:
                self._on_close(ws)

            elif msg.tp == aiohttp.MsgType.error:
                self._on_error(ws)

        self.clients.remove(ws)
        return ws

    def _request_is_valid(self, request):
        # Yep! seems legit.
        return True

    def _msg_is_valid(self, msg):
        # Yep! seems legit.
        return True

    def _on_open(self, ws):
        # Hi, what brought you along today?
        pass

    def _on_error(self, ws, msg=None, exception=None):
        ws.send_error(msg['id'], ws.INTERNAL_ERROR, 'Internal error.')

    def _on_close(self, ws):
        # Bye, it was a pleasure to serve you.
        pass

    @asyncio.coroutine
    def list_methods(self, ws, params):
        return list(self.methods.keys())
