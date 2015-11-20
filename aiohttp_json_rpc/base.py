import asyncio
from aiohttp import web
import aiohttp
import json


class JsonWebSocketResponse(web.WebSocketResponse):
    JSONRPC = '2.0'
    PARSE_ERROR = -32700
    INVALID_REQUEST_ERROR = -32600
    METHOD_NOT_FOUND_ERROR = -32601
    INVALID_PARAMS_ERROR = -32602
    INTERNAL_ERROR = -32603

    objects = []

    @asyncio.coroutine
    def prepare(self, request):
        self.objects.append(self)

        yield from super().prepare(request)

    @asyncio.coroutine
    def close(self, code=1000, message=b''):
        self.objects.remove(self)

        return super().close(code=code, message=message)

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
    IGNORED_METHODS = ['WEBSOCKET_CLASS']

    def __new__(cls, request):
        return cls._run(cls, request)

    @asyncio.coroutine
    def _run(self, request):
        # check request
        if not self._request_is_valid(self, request):
            return web.Response(status=403)

        # find methods
        self.methods = {}

        for i in dir(self):
            if i.startswith('_') or i in self.IGNORED_METHODS:
                continue

            attr = getattr(self, i)

            if asyncio.iscoroutinefunction(attr):
                self.methods[i] = getattr(self, i)

        # handle request
        if request.method == 'GET':

            # websocket
            if request.headers.get('upgrade', '') == 'websocket':
                ws = self.WEBSOCKET_CLASS()
                yield from ws.prepare(request)
                loop = asyncio.get_event_loop()

                while not ws.closed:
                    msg = yield from ws.receive()

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
                            rsp = yield from self.methods[msg['method']](
                                self, ws, msg)

                            ws.send_response(msg['id'], rsp)

                        except Exception:
                            ws.send_error(msg['id'], ws.INTERNAL_ERROR,
                                          'Internal error.')

                    elif msg.tp == aiohttp.MsgType.close:
                        self._on_ws_close(self, ws)

                    elif msg.tp == aiohttp.MsgType.error:
                        self._on_ws_error(self, ws)

                return ws

            # GET request
            else:
                return web.Response()

    def _request_is_valid(self, request):
        return True

    def _on_ws_close(self, ws):
        # Bye, it was a pleasure to serve you.
        pass

    def _on_ws_error(self, ws):
        # Huh! nevermind...
        pass

    @asyncio.coroutine
    def list_methods(self, ws, params):
        return list(self.methods.keys())
