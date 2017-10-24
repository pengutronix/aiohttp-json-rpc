class RpcError(Exception):
    MESSAGE = ''

    def __init__(self, msg_id=None, data=None):
        self.data = data
        self.msg_id = msg_id

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


_EXCEPTION_LOOKUP_TABLE = {
    e.ERROR_CODE: e for e in RpcError.__subclasses__()
}


def error_code_to_exception(error_code: int):
    """
    Translates a given error code to the corresponding exception.

    Parameters
    ----------
    error_code : int
        A valid RPC error code.

    Returns
    -------
        One of the RpcError exception classes defined in this file.

    Raises
    ------
    KeyError
        When the given ``error_code`` does not correspond to any
        known RPC exception.
    """
    # RPC error messages without an error code are illegal, according
    # to the spec. To check this is unnecessary because the
    # ``protocol.decode_msg`` function raises a ``RpcInvalidRequestError``
    # in this case before. Therefore any error code passed to this
    # function must either map to a known subclass of RpcError or not exist.

    return _EXCEPTION_LOOKUP_TABLE[error_code]
