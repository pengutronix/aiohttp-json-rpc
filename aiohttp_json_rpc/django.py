import asyncio

__already_patched = False


def local(original):
    # we keep the original _connections in scope to keep the thread safety of
    # Django for non-asyncio code.

    class Storage(object):
        pass

    class TaskLocal(object):
        def _get_storage(self):
            try:
                task = asyncio.Task.current_task()

                if task is None:
                    return original

            except RuntimeError:
                return original

            storage = getattr(task, 'local', None)

            if storage is None:
                storage = Storage()
                setattr(task, 'local', storage)

            return storage

        def __getattr__(self, key):
            return getattr(self._get_storage(), key)

        def __setattr__(self, key, item):
            return setattr(self._get_storage(), key, item)

    return TaskLocal()


def patch_db_connections():
    """
    This wraps django.db.connections._connections with a TaskLocal object.

    The Django transactions are only thread-safe, using threading.local,
    and don't know about coroutines.
    """

    global __already_patched

    if not __already_patched:
        from django.db import connections

        connections._connections = local(connections._connections)
        __already_patched = True
