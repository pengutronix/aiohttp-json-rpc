from django.apps import AppConfig


class AiohttpJsonRpcConfig(AppConfig):
    name = 'aiohttp_json_rpc.django'
    verbose_name = 'aiohttp-json-rpc config'

    def ready(self):
        from django.contrib.contenttypes.models import ContentType
        from django.contrib.auth.models import Permission
        from django.apps import apps

        for model in apps.get_models():
            Permission.objects.get_or_create(
                codename='view_{}'.format(model._meta.model_name),
                name='Can view {}'.format(model._meta.verbose_name),
                content_type=ContentType.objects.get_for_model(model),
            )
