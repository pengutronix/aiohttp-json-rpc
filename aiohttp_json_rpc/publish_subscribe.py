from .base import JsonRpc
import asyncio


class PublishSubscribeJsonRpc(JsonRpc):
    @asyncio.coroutine
    def subscribe(self, ws, msg):
        if not hasattr(ws, 'topics'):
            ws.topics = set()

        topics = msg['params']

        if type(topics) is not list:
            topics = [topics]

        for topic in topics:
            if topic:
                ws.topics.add(topic)

        return True

    @asyncio.coroutine
    def unsubscribe(self, ws, msg):
        if not hasattr(ws, 'topics'):
            ws.topics = set()

            return True

        topics = msg['params']

        if type(topics) is not list:
            topics = [topics]

        for topic in topics:
            if topic in ws.topics:
                ws.topics.remove(topic)

        return True

    @asyncio.coroutine
    def get_topics(self, ws, msg):
        return list(getattr(ws, 'topics', set()))

    def filter(self, topics):
        if type(topics) is not list:
            topics = [topics]

        topics = set(topics)

        for client in self.clients:
            if not hasattr(client, 'topics'):
                continue

            if len(topics & client.topics) > 0:
                yield client

    def notify(self, topic, data):
        if type(topic) is not str:
            raise ValueError

        for client in self.filter(topic):
            client.send_notification(topic, data)
