class JsonRpcRequest:
    def __init__(self, http_request, rpc, ws, msg):
        self.http_request = http_request
        self.rpc = rpc
        self.ws = ws
        self.msg = msg

    @property
    def params(self):
        if 'params' not in self.msg:
            self.msg['params'] = None

        return self.msg['params']

    @params.setter
    def params(self, value):
        self.msg['params'] = value

    @property
    def methods(self):
        return self.http_request.methods

    @methods.setter
    def methods(self, value):
        self.http_request.methods = value

    @property
    def topics(self):
        if not hasattr(self.ws, 'topics'):
            self.ws.topics = set()

        return self.ws.topics

    @topics.setter
    def topics(self, value):
        self.ws.topics = value
