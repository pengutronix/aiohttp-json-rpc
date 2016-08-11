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

    def prepare_request(self, request):
        request.methods = {}
        request.user = self.get_user(request)

        def run_tests(tests, user):
            for test in tests:
                if not test(user):
                    return False

            return True

        # add methods to request
        request.methods = {}

        for name, method in request.rpc.methods.items():
            # login check
            if hasattr(method, 'login_required') and (
               not request.user.is_active or
               not request.user.is_authenticated()):
                continue

            # permission check
            if hasattr(method, 'permissions_required') and\
               not request.user.is_superuser and\
               not request.user.has_perms(method.permissions_required):
                continue

            # user tests
            if hasattr(method, 'tests') and\
               not request.user.is_superuser and\
               not run_tests(method.tests, request.user):
                continue

            request.methods[name] = method

        return request
