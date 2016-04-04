from .base import JsonRpc
import asyncio


class PublishSubscribeJsonRpc(JsonRpc):
    @asyncio.coroutine
    def subscribe(self, params, **kwargs):
        if not hasattr(kwargs['ws'], 'topics'):
            kwargs['ws'].topics = set()

        if type(params) is not list:
            params = [params]

        for topic in params:
            if topic:
                kwargs['ws'].topics.add(topic)

        return True

    @asyncio.coroutine
    def unsubscribe(self, params, **kwargs):
        if not hasattr(kwargs['ws'], 'topics'):
            kwargs['ws'].topics = set()

            return True

        if type(params) is not list:
            params = [params]

        for topic in params:
            if topic in kwargs['ws'].topics:
                kwargs['ws'].topics.remove(topic)

        return True

    @asyncio.coroutine
    def get_topics(self, params, **kwargs):
        return list(getattr(kwargs['ws'], 'topics', set()))

    def filter(self, topics):
        if type(topics) is not list:
            topics = [topics]

        topics = set(topics)

        for client in self.clients:
            if not hasattr(client, 'topics'):
                continue

            if len(topics & client.topics) > 0:
                yield client

    def notify(self, topic, data=None):
        if type(topic) is not str:
            raise ValueError

        for client in self.filter(topic):
            client.send_notification(topic, data)
