import logging

logger = logging.getLogger('aiohttp_json_rpc.protocol')


class classproperty(object):
    def __init__(self, fget):
        self.fget = fget

    def __get__(self, owner_self, owner_cls):
        return self.fget(owner_cls)


class RpcError(Exception):
    MESSAGE = ''
    ERROR_CODE = None
    _lookup_table = None

    def __init__(self, *args, msg_id=None, data=None, error_code=None,
                 message='', **kwargs):

        if(error_code is not None and
           error_code not in self.lookup_table.keys()):
                raise ValueError('error code out of range')

        self.data = data
        self.msg_id = msg_id
        self.error_code = error_code or self.ERROR_CODE
        self.message = message or self.MESSAGE

        super().__init__(*args, **kwargs)

    def __str__(self):
        return self.MESSAGE

    @classmethod
    def _gen_lookup_table(cls):
        logger.debug('regenerating error lookup table')

        cls._lookup_table = {
            **{
                -32600: RpcInvalidRequestError,
                -32601: RpcMethodNotFoundError,
                -32602: RpcInvalidParamsError,
                -32603: RpcInternalError,
                -32700: RpcParseError,

            },
            **{error_code: RpcGenericServerDefinedError
               for error_code in range(-32000, -32100, -1)}
        }

        for subclass in cls.__subclasses__():
            if subclass is RpcGenericServerDefinedError:
                continue

            if subclass.ERROR_CODE not in cls._lookup_table.keys():
                logger.error('error code %s is unspecified',
                             subclass.ERROR_CODE)

                continue

            cls._lookup_table[subclass.ERROR_CODE] = subclass

    @classmethod
    def invalidate_lookup_table(cls):
        cls._lookup_table = None

    @classproperty
    def lookup_table(cls):
        if not cls._lookup_table:
            cls._gen_lookup_table()

        return cls._lookup_table

    @classmethod
    def error_code_to_exception(cls, error_code: int):
        return cls.lookup_table[error_code]


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


class RpcGenericServerDefinedError(RpcError):
    ERROR_CODE = None
    MESSAGE = 'Generic server defined Error'


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

    return RpcParseError.lookup_table[error_code]
