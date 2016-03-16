from django.contrib.auth.models import User, AnonymousUser
from django.contrib.sessions.models import Session


def get_user(request):
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
