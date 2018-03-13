def raw_response(function=None):
    def decorator(function):
        function.raw_response = True

        return function

    if function:
        return decorator(function)

    return decorator
