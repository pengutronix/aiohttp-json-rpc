from .base import JsonRpc
import asyncio


class PublishSubscribeJsonRpc(JsonRpc):
    @asyncio.coroutine
    def subscribe(self, ws, msg):
        if not hasattr(ws, 'subscriptions'):
            ws.subscriptions = set()

        subscriptions = msg['params']

        if type(subscriptions) is not list:
            subscriptions = [subscriptions]

        for subscription in subscriptions:
            if subscription:
                ws.subscriptions.add(subscription)

        return True

    @asyncio.coroutine
    def unsubscribe(self, ws, msg):
        if not hasattr(ws, 'subscriptions'):
            ws.subscriptions = set()

            return True

        subscriptions = msg['params']

        if type(subscriptions) is not list:
            subscriptions = [subscriptions]

        for subscription in subscriptions:
            if subscription in ws.subscriptions:
                ws.subscriptions.remove(subscription)

        return True

    @asyncio.coroutine
    def list_subscriptions(self, ws, msg):
        return list(getattr(ws, 'subscriptions', set()))

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
