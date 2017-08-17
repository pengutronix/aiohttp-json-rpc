from aiohttp import web
import aiohttp
import asyncio
import logging

from .exceptions import RpcMethodNotFoundError

from .protocol import (
    JsonRpcMsgTyp,
    encode_request,
    encode_error,
    encode_result,
    decode_msg,
)


default_logger = logging.getLogger('aiohttp-json-rpc.client')


class JsonRpcClient(object):
    _client_id = 0

    def __init__(self, logger=default_logger):
        self._pending = {}
        self._msg_id = 0
        self._logger = logger
        self._handler = {}
        self._methods = {}

        self._id = JsonRpcClient._client_id
        JsonRpcClient._client_id += 1

    def add_methods(self, *methods):
        for prefix, method in methods:
            name = method.__name__

            if prefix:
                name = '{}__{}'.format(prefix, name)

            self._methods[name] = method

    async def _handle_request(self, msg):
        if not msg.data['method'] in self._methods:
            response = encode_error(
                RpcMethodNotFoundError(msg_id=msg.data.get('id', None)))

        else:
            result = await self._methods[msg.data['method']](
                msg.data['params'])

            response = encode_result(msg.data['id'], result)

        self._logger.debug('#%s: > %s', self._id, response)
        self._ws.send_str(response)

    async def _handle_msgs(self):
        self._logger.debug('#%s: worker start...', self._id)

        while not self._ws.closed:
            try:
                raw_msg = await self._ws.receive()

                self._logger.debug('#%s: < %s', self._id, raw_msg.data)

                if raw_msg.type != web.MsgType.text:
                    continue

                msg = decode_msg(raw_msg.data)

                # requests
                if msg.type == JsonRpcMsgTyp.REQUEST:
                    self._logger.debug('#%s: handled as request', self._id)
                    await self._handle_request(msg)
                    self._logger.debug('#%s: handled', self._id)

                # notifications
                elif msg.type == JsonRpcMsgTyp.NOTIFICATION:
                    if msg.data['method'] in self._handler:
                        await self._handler['method'](msg.data)

                # results
                elif msg.type == JsonRpcMsgTyp.RESULT:
                    if msg.data['id'] in self._pending:
                        self._pending[msg.data['id']].set_result(
                            msg.data['result'])

            except Exception as e:
                self._logger.error(e, exc_info=True)

        self._logger.debug('#%s: worker stopped', self._id)

    async def connect(self, host, port, url='/', protocol='ws', cookies=None):
        fqdn = '{}://{}:{}{}'.format(protocol, host, port, url)
        self._session = aiohttp.ClientSession(cookies=cookies)

        self._logger.debug('#%s: ws connect...', self._id)
        self._ws = await self._session.ws_connect(fqdn)
        self._logger.debug('#%s: ws connected', self._id)

        self._message_worker = asyncio.ensure_future(self._handle_msgs())

    async def disconnect(self):
        await self._ws.close()
        await self._session.close()

    async def call(self, method, params=None, id=None, timeout=None):
        if not id:
            id = self._msg_id
            self._msg_id += 1

        self._pending[id] = asyncio.Future()
        msg = encode_request(method, id=id, params=params)

        self._logger.debug('#%s: > %s', self._id, msg)
        self._ws.send_str(msg)

        if timeout:
            await asyncio.wait_for(self._pending[id], timeout=timeout)

        else:
            await self._pending[id]

        result = self._pending[id].result()
        del self._pending[id]

        return result

    async def get_methods(self, timeout=None):
        return await self.call('get_methods', timeout=timeout)

    async def get_topics(self, timeout=None):
        return await self.call('get_topics', timeout=timeout)

    async def get_subscriptions(self, timeout=None):
        return await self.call('get_subscriptions', timeout=timeout)

    async def subscribe(self, topic, handler, timeout=None):
        self._handler[topic] = handler

        return await self.call('subscribe', params=topic, timeout=timeout)

    async def unsubscribe(self, topic, timeout=None):
        if topic in self._handler:
            del self._handler[topic]

        return await self.call('unsubscribe', params=topic, timeout=timeout)
