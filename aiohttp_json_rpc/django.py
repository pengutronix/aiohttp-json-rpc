from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from .base import JsonRpc
from .publish_subscribe import PublishSubscribeJsonRpc


class DjangoAuthJsonRpc(JsonRpc):
    def _get_django_user(session_key):
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

        return None

    def _request_is_valid(self, request):
        sessionid = request.cookies.get('sessionid', '')

        if sessionid:
            user = self._get_django_user(sessionid)

            if user.is_active and user.is_authenticated():
                return True

        return False


class DjangoAuthPublishSubscribeJsonRpc(PublishSubscribeJsonRpc,
                                        DjangoAuthJsonRpc):
    pass
