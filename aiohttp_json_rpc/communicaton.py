class JsonRpcRequest:
    def __init__(self, http_request, rpc, msg):
        self.http_request = http_request
        self.rpc = rpc
        self.msg = msg

    @property
    def ws(self):
        return getattr(self.http_request, 'ws', None)

    @property
    def params(self):
        if 'params' not in self.msg.data:
            self.msg.data['params'] = None

        return self.msg.data['params']

    @params.setter
    def params(self, value):
        self.msg.data['params'] = value

    @property
    def methods(self):
        return self.http_request.methods

    @methods.setter
    def methods(self, value):
        self.http_request.methods = value

    @property
    def topics(self):
        if not hasattr(self.http_request, 'topics'):
            self.http_request.topics = set()

        return self.http_request.topics

    @topics.setter
    def topics(self, value):
        self.http_request.topics = value

    @property
    def subscriptions(self):
        if not hasattr(self.http_request, 'subscriptions'):
            self.http_request.subscriptions = set()

        return self.http_request.subscriptions

    @subscriptions.setter
    def subscriptions(self, value):
        self.http_request.subscriptions = value
