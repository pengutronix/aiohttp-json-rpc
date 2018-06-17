from django.db.models.signals import post_migrate
from django.apps import AppConfig

from . import generate_view_permissions


class AiohttpJsonRpcConfig(AppConfig):
    name = 'aiohttp_json_rpc.django'
    verbose_name = 'aiohttp-json-rpc config'

    def ready(self):
        post_migrate.connect(
            lambda sender, **kwargs: generate_view_permissions(),
            sender=self,
            weak=False,
        )
