class RpcError(Exception):
    MESSAGE = ''

    def __init__(self, data=None):
        self.data = data

    def __str__(self):
        return self.MESSAGE


class RpcInvalidRequestError(RpcError):
    ERROR_CODE = -32600
    MESSAGE = 'Invalid request'


class RpcMethodNotFoundError(RpcError):
    ERROR_CODE = -32601
    MESSAGE = 'Method not found'


class RpcInternalError(RpcError):
    ERROR_CODE = -32603
    MESSAGE = 'Internal Error'


class RpcInvalidParamsError(RpcError):
    ERROR_CODE = -32602
    MESSAGE = 'Invalid params'


class RpcParseError(RpcError):
    ERROR_CODE = -32700
    MESSAGE = 'Invalid JSON was received'
