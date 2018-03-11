import pytest


def test_valid_message():
    from aiohttp_json_rpc.protocol import JsonRpcMsgTyp, decode_msg

    raw_msg = '''
    {
        "jsonrpc": "2.0",
        "id": 0,
        "method": "foo",
        "params": "bar"
    }
    '''

    msg = decode_msg(raw_msg)

    assert msg.type == JsonRpcMsgTyp.REQUEST

    assert msg.data['jsonrpc'] == '2.0'
    assert msg.data['id'] == 0
    assert msg.data['method'] == 'foo'
    assert msg.data['params'] == 'bar'


def test_valid_notification():
    from aiohttp_json_rpc.protocol import JsonRpcMsgTyp, decode_msg

    # id is Null
    raw_msg = '''
    {
        "jsonrpc": "2.0",
        "id": null,
        "method": "foo",
        "params": "bar"
    }
    '''

    msg = decode_msg(raw_msg)

    assert msg.type == JsonRpcMsgTyp.NOTIFICATION

    assert msg.data['jsonrpc'] == '2.0'
    assert msg.data['id'] is None
    assert msg.data['method'] == 'foo'
    assert msg.data['params'] == 'bar'

    # without id
    raw_msg = '''
    {
        "jsonrpc": "2.0",
        "method": "foo",
        "params": "bar"
    }
    '''

    msg = decode_msg(raw_msg)

    assert msg.type == JsonRpcMsgTyp.NOTIFICATION

    assert msg.data['jsonrpc'] == '2.0'
    assert msg.data['id'] is None
    assert msg.data['method'] == 'foo'
    assert msg.data['params'] == 'bar'


def test_valid_error():
    from aiohttp_json_rpc.protocol import JsonRpcMsgTyp, decode_msg

    raw_msg = '''
        {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {
                "code": -32600,
                "message": "Invalid request",
                "data": null
            }
        }
    '''

    msg = decode_msg(raw_msg)

    assert msg.type == JsonRpcMsgTyp.ERROR


def test_invalid_error():
    """
    This test tries to decode an error message with an invalid error code
    """

    from aiohttp_json_rpc import RpcInvalidRequestError
    from aiohttp_json_rpc.protocol import decode_msg

    raw_msg = '''
        {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {
                "code": -32101,
                "message": "Invalid request",
                "data": null
            }
        }
    '''

    with pytest.raises(RpcInvalidRequestError):
        decode_msg(raw_msg)
