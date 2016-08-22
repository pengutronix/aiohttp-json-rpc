import binascii
import asyncio
import hashlib
import os

from .. import RpcInvalidParamsError
from . import login_required, permission_required


class PasswdAuthBackend:
    def __init__(self, passwd_file):
        self.passwd_file = passwd_file

    def _is_authorized(self, request, method):
        if hasattr(method, 'login_required') and not request.user:
            return False

        if hasattr(method, 'permission_required') and not (
              len(request.permissions & method.permissions_required) ==
              len(method.permissions_required)):
            return False

        return True

    def prepare_request(self, request):
        if not hasattr(request, 'user'):
            request.user = None

        if not hasattr(request, 'permissions'):
            request.permissions = set()

        # methods
        request.methods = {}

        for name, method in {'create_user': self.create_user,
                             'logout': self.logout,
                             **request.rpc.methods}.items():

            if self._is_authorized(request, method):
                request.methods[name] = method

        if not request.user:
            request.methods['login'] = self.login

        # topics
        request.topics = set()

        for name, method in request.rpc.topics.items():
            if self._is_authorized(request, method):
                request.topics.add(name)

        if not request.subscriptions:
            request.subscriptions = set()

        request.subscriptions = request.topics & request.subscriptions

    def _create_user(self, username, password, salt=None, rounds=100000,
                     permissions=()):

        salt = salt or os.urandom(16)

        if not type(password) == bytes:
            password = password.encode()

        password_hash = hashlib.pbkdf2_hmac('sha256', password, salt, rounds)

        password_hash = binascii.hexlify(password_hash)
        salt = binascii.hexlify(salt)

        line = '{username}:{password_hash}:{salt}:{rounds}:{permissions}\n'.format(  # NOQA
            username=username,
            password_hash=password_hash.decode(),
            salt=salt.decode(),
            rounds=str(rounds),
            permissions=','.join(permissions),
        )

        with open(self.passwd_file, 'a+') as f:
            f.write(line)

    def _login(self, username, password):
        if not type(password) == bytes:
            password = password.encode()

        with open(self.passwd_file, 'r') as f:
            for line in f:
                data = line.split(':')

                if username == data[0]:
                    try:
                        password_hash = binascii.unhexlify(data[1])
                        salt = binascii.unhexlify(data[2])
                        rounds = int(data[3])

                        new_password_hash = hashlib.pbkdf2_hmac(
                            'sha256', password, salt, rounds)

                    except:
                        continue

                    if password_hash == new_password_hash:
                        return username, set(data[4].split(','))

        return None, ()

    @asyncio.coroutine
    def login(self, request):
        loop = asyncio.get_event_loop()

        try:
            username = request.params['username']
            password = request.params['password']

        except KeyError:
            raise RpcInvalidParamsError

        username, permissions = (yield from loop.run_in_executor(
            None, self._login, username, password))

        request.http_request.user = username
        request.http_request.permissions = permissions

        # rediscover methods
        self.prepare_request(request.http_request)

        return bool(username)

    @permission_required('create-user')
    @asyncio.coroutine
    def create_user(self, request):
        loop = asyncio.get_event_loop()

        try:
            username = request.params['username']
            password = request.params['password']

        except (KeyError, TypeError):
            raise RpcInvalidParamsError

        return (yield from loop.run_in_executor(None, self._create_user,
                                                username, password))

    @login_required
    @asyncio.coroutine
    def logout(self, request):
        request.http_request.user = None
        request.http_request.permissions = set()

        return True
