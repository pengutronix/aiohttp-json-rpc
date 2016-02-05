from .base import JsonWebSocketResponse, JsonRpc
import asyncio


class PublishSubscribeJsonWebSocketResponse(JsonWebSocketResponse):
    def __init__(self, *, timeout=10.0, autoclose=True, autoping=True,
                 protocols=()):
        super().__init__(timeout=timeout, autoclose=autoclose,
                         autoping=autoping, protocols=protocols)

        self.subscriptions = set()


class PublishSubscribeJsonRpc(JsonRpc):
    WEBSOCKET_CLASS = PublishSubscribeJsonWebSocketResponse
    IGNORED_METHODS = [
        'filter',
        'notify',
    ]

    @asyncio.coroutine
    def subscribe(self, ws, msg):
        subscriptions = msg['params']

        if type(subscriptions) is not list:
            subscriptions = [subscriptions]

        for subscription in subscriptions:
            if subscription:
                ws.subscriptions.add(subscription)

        return True

    @asyncio.coroutine
    def unsubscribe(self, ws, msg):
        subscriptions = msg['params']

        if type(subscriptions) is not list:
            subscriptions = [subscriptions]

        for subscription in subscriptions:
            if subscription in ws.subscriptions:
                ws.subscriptions.remove(subscription)

        return True

    @asyncio.coroutine
    def list_subscriptions(self, ws, msg):
        return list(ws.subscriptions)

    def filter(self, subscriptions):
        if type(subscriptions) is not list:
            subscriptions = [subscriptions]

        subscriptions = set(subscriptions)

        for client in self.clients:
            if len(subscriptions & client.subscriptions) > 0:
                yield client

    def notify(self, subscription, msg):
        if type(subscription) is not str:
            raise ValueError

        for client in self.filter(subscription):
            client.send_notification(subscription, msg)
