import asyncio

default_app_config = 'aiohttp_json_rpc.django.apps.AiohttpJsonRpcConfig'
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


def generate_view_permissions():
    from django.contrib.contenttypes.models import ContentType
    from django.contrib.auth.models import Permission
    from django.apps import apps

    for model in apps.get_models():
        Permission.objects.get_or_create(
            codename='view_{}'.format(model._meta.model_name),
            name='Can view {}'.format(model._meta.verbose_name),
            content_type=ContentType.objects.get_for_model(model),
        )
