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
