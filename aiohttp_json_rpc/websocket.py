from aiohttp.web_ws import WebSocketResponse
import json


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
