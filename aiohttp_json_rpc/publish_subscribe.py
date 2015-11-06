from .base import JsonWebSocketResponse, JsonRpc


class PublishSubscribeJsonWebSocketResponse(JsonWebSocketResponse):
    def __init__(self, *, timeout=10.0, autoclose=True, autoping=True,
                 protocols=()):
        super().__init__(timeout=timeout, autoclose=autoclose,
                         autoping=autoping, protocols=protocols)

        self.subscriptions = set()


class PublishSubscribeJsonRpc(JsonRpc):
    WEBSOCKET_CLASS = PublishSubscribeJsonWebSocketResponse
    IGNORED_METHODS = ['WEBSOCKET_CLASS', 'filter']

    def subscribe(self, ws, params):
        if type(params) is not list:
            params = [params]

        for subscription in params:
            if subscription:
                ws.subscriptions.add(subscription)

        return True

    def unsubscribe(self, ws, params):
        if type(params) is not list:
            params = [params]

        for subscription in params:
            if subscription in ws.subscriptions:
                ws.subscriptions.remove(subscription)

        return True

    def list_subscriptions(self, ws, params):
        return list(ws.subscriptions)

    @classmethod
    def filter(cls, subscriptions):
        if type(subscriptions) is not list:
            subscriptions = [subscriptions]

        subscriptions = set(subscriptions)

        for i in cls.WEBSOCKET_CLASS.objects:
            if len(subscriptions & i.subscriptions) > 0:
                yield i
