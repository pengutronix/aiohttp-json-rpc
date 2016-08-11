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
