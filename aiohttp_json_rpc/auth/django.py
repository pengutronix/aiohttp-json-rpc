from django.contrib.auth.models import User, AnonymousUser
from django.contrib.sessions.models import Session
from . import AuthBackend


class DjangoAuthBackend(AuthBackend):
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
        if hasattr(method, 'permissions_required') and\
           not request.user.is_superuser and\
           not request.user.has_perms(method.permissions_required):
            return False

        # user tests
        if hasattr(method, 'tests') and not request.user.is_superuser:
            for test in method.tests:
                if not test(request.user):
                    return False

        return True

    def prepare_request(self, request):
        request.user = self.get_user(request)

        # methods
        request.methods = {}

        for name, method in request.rpc.methods.items():
            if self._is_authorized(request, method):
                request.methods[name] = method

        # topics
        request.topics = set()

        for name, method in request.rpc.topics.items():
            if self._is_authorized(request, method):
                request.topics.add(name)

        if not hasattr(request, 'subscriptions'):
            request.subscriptions = set()

        request.subscriptions = request.topics & request.subscriptions
