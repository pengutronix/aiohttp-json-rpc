class AuthBackend:
    pass


class DummyAuthBackend(AuthBackend):
    def prepare_request(self, request):
        request.methods = request.rpc.methods
        request.topics = set(request.rpc.topics.keys())
        request.subscriptions = set()


def login_required(function=None):
    def decorator(function):
        function.login_required = True

        return function

    if function:
        return decorator(function)

    return decorator


def permission_required(permission):
    def decorator(function):
        if not type(permission) == str:
            raise ValueError('permission has to be a string')

        if not hasattr(function, 'permissions_required'):
            function.permissions_required = set()

        function.permissions_required.add(permission)

        return function

    return decorator


def user_passes_test(test_func):
    def decorator(function):
        if not callable(test_func):
            raise ValueError('test has to be callable')

        if not hasattr(function, 'tests'):
            function.tests = set()

        function.tests.add(test_func)

        return function

    return decorator
