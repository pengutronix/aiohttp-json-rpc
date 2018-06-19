from importlib import import_module

from django.contrib.auth import authenticate, login as django_login
from django.contrib.auth.models import User, AnonymousUser
from django.contrib.sessions.models import Session
from django.forms.models import model_to_dict
from django.conf import settings
from django.http import HttpRequest
from django.apps import apps

from .. import RpcInvalidParamsError
from ..rpc import JsonRpcMethod
from . import AuthBackend


class DjangoAuthBackend(AuthBackend):
    def __init__(self, generic_orm_methods=False):
        self.generic_orm_methods = generic_orm_methods
        self.session_engine = import_module(settings.SESSION_ENGINE)

    # Helper methods
    def get_user(self, request):
        session_key = request.cookies.get('sessionid', '')

        if session_key:
            try:
                session = Session.objects.get(session_key=session_key)
                uid = session.get_decoded().get('_auth_user_id')

                try:
                    return User.objects.get(pk=uid)

                except User.DoesNotExist:
                    pass

            except Session.DoesNotExist:
                pass

        return AnonymousUser()

    def _is_authorized(self, request, method):
        if hasattr(method, 'login_required') and (
           not request.user.is_active or
           not request.user.is_authenticated()):
            return False

        # permission check
        if(hasattr(method, 'permissions_required') and
           not request.user.is_superuser and
           not request.user.has_perms(method.permissions_required)):
            return False

        # user tests
        if hasattr(method, 'tests') and not request.user.is_superuser:
            for test in method.tests:
                if not test(request.user):
                    return False

        return True

    # generic ORM methods
    def dump_model_object(self, obj):
        d = model_to_dict(obj)
        d['pk'] = obj.pk

        return d

    async def _model_view(self, request, model):
        lookups = request.msg.data['params'] or {}

        if not isinstance(lookups, dict):
            raise RpcInvalidParamsError

        try:
            objects = model.objects.filter(**lookups)

            return [self.dump_model_object(i) for i in objects]

        except Exception:
            raise RpcInvalidParamsError

    async def _model_delete(self, request, model):
        lookups = request.msg.data['params'] or {}

        if not isinstance(lookups, dict):
            raise RpcInvalidParamsError

        try:
            model.objects.filter(**lookups).delete()

        except Exception:
            raise RpcInvalidParamsError

        return True

    async def _model_add(self, request, model):
        values = request.msg.data['params'] or {}

        if not isinstance(values, dict) or not values:
            raise RpcInvalidParamsError

        try:
            new_object = model.objects.create(**values)

            return self.dump_model_object(new_object)

        except Exception:
            raise RpcInvalidParamsError

    async def _model_change(self, request, model):
        try:
            params = request.msg.data['params']
            pk = params.pop('pk')

            model_object = model.objects.get(pk=pk)

            for field_name, value in params.items():
                setattr(model_object, field_name, value)

            model_object.save()

            return True

        except KeyError:
            raise RpcInvalidParamsError

    async def handle_orm_call(self, request):
        method_name = request.msg.data['method'].split('__')[1]
        app_label, _ = method_name.split('.')
        action, model_name = _.split('_')
        model = apps.get_model('{}.{}'.format(app_label, model_name))

        if action == 'view':
            return await self._model_view(request, model)

        elif action == 'add':
            return await self._model_add(request, model)

        elif action == 'change':
            return await self._model_change(request, model)

        elif action == 'delete':
            return await self._model_delete(request, model)

    # login / logout
    async def login(self, request):
        try:
            username = str(request.params['username'])
            password = str(request.params['password'])

        except(KeyError, TypeError, ValueError):
            raise RpcInvalidParamsError

        user = authenticate(username=username, password=password)

        if not user:
            return False

        # to use the standard django login mechanism, which is build on the
        # request-, response-system, we have to fake a django http request
        fake_request = HttpRequest()
        fake_request.session = self.session_engine.SessionStore()
        django_login(fake_request, user)
        fake_request.session.save()

        # set session cookie
        request.http_request.ws.set_cookie(
            name=settings.SESSION_COOKIE_NAME,
            value=fake_request.session.session_key,
            path='/',
            max_age=None,
            domain=settings.SESSION_COOKIE_DOMAIN,
            secure=settings.SESSION_COOKIE_SECURE or None,
            expires=None,
        )

        # rediscover methods and topics
        self.prepare_request(request.http_request, user=user)

        return True

    # request processing
    def prepare_request(self, request, user=None):
        request.user = user or self.get_user(request)
        request.methods = {}

        # django auth methods
        if isinstance(request.user, AnonymousUser):
            request.methods['login'] = JsonRpcMethod(self.login)

        # generic django model methods
        if self.generic_orm_methods:
            for permission_name in request.user.get_all_permissions():
                action = permission_name.split('.')[1].split('_')[0]
                method_name = 'db__{}'.format(permission_name)

                if action in ('view', 'add', 'change', 'delete', ):
                    request.methods[method_name] = JsonRpcMethod(
                        self.handle_orm_call)

        # rpc defined methods
        for name, method in request.rpc.methods.items():
            if self._is_authorized(request, method.method):
                request.methods[name] = method

        # topics
        request.topics = set()

        for name, method in request.rpc.topics.items():
            if self._is_authorized(request, method):
                request.topics.add(name)

        if not hasattr(request, 'subscriptions'):
            request.subscriptions = set()

        request.subscriptions = request.topics & request.subscriptions
