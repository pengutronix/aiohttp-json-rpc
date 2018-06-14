import binascii
import asyncio
import hashlib
import os

from .. import RpcInvalidParamsError
from . import login_required


class PasswdAuthBackend:
    def __init__(self, passwd_file):
        self.passwd_file = passwd_file
        self.read()

    def read(self):
        self.user = {}

        try:
            with open(self.passwd_file, 'r') as f:
                for line in f:
                    if line.endswith('\n'):
                        line = line[:-1]

                    data = line.split(':')

                    if len(data) < 5:
                        continue

                    self.user[data[0]] = {
                        'password_hash': binascii.unhexlify(data[1]),
                        'salt': binascii.unhexlify(data[2]),
                        'rounds': int(data[3]),
                        'permissions': set(data[4].split(',')),
                    }

        except FileNotFoundError:
            pass

    def write(self):
        with open(self.passwd_file, 'w') as f:
            for username, data in self.user.items():
                f.write('{username}:{password_hash}:{salt}:{rounds}:{permissions}\n'.format(  # NOQA
                    username=username,
                    password_hash=binascii.hexlify(
                        data['password_hash']).decode(),
                    salt=binascii.hexlify(data['salt']).decode(),
                    rounds=str(data['rounds']),
                    permissions=','.join(data['permissions']),
                ))

    def _create_user(self, username, password, salt=None, rounds=100000,
                     permissions=None):

        if username in self.user:
            return False

        salt = salt or os.urandom(16)

        if not type(password) == bytes:
            password = password.encode()

        password_hash = hashlib.pbkdf2_hmac('sha256', password, salt, rounds)

        self.user[username] = {
            'password_hash': password_hash,
            'salt': salt,
            'rounds': rounds,
            'permissions': permissions or []
        }

        self.write()

        return True

    def _delete_user(self, username):
        if username not in self.user:
            return False

        self.user.pop(username)
        self.write()

        return True

    def _set_password(self, username, password, salt=None, rounds=100000,
                      old_password=''):

        if old_password:
            if not self._login(username, old_password)[0]:
                return False

        salt = salt or os.urandom(16)

        if not type(password) == bytes:
            password = password.encode()

        password_hash = hashlib.pbkdf2_hmac('sha256', password, salt, rounds)

        self.user[username]['password_hash'] = password_hash
        self.user[username]['salt'] = salt
        self.user[username]['rounds'] = rounds

        return True

    def _login(self, username, password):
        if not type(password) == bytes:
            password = password.encode()

        if username in self.user:
            password_hash = hashlib.pbkdf2_hmac('sha256', password,
                                                self.user[username]['salt'],
                                                self.user[username]['rounds'])

            if password_hash == self.user[username]['password_hash']:
                return username, self.user[username]['permissions']

        return None, set()

    def _is_authorized(self, request, method):
        if hasattr(method, 'login_required') and not request.user:
            return False

        if hasattr(method, 'permissions_required') and not (
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

        method_pool = dict(
            login=self.login,
            logout=self.logout,
            create_user=self.create_user,
            delete_user=self.delete_user,
            set_password=self.set_password,
            **request.rpc.methods
        )

        for name, method in method_pool.items():
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

    async def login(self, request):
        loop = asyncio.get_event_loop()

        try:
            username = request.params['username']
            password = request.params['password']

        except(KeyError, TypeError):
            raise RpcInvalidParamsError

        request.http_request.user, request.http_request.permissions = (
            await loop.run_in_executor(None, self._login, username, password))

        # rediscover methods
        self.prepare_request(request.http_request)

        return bool(request.http_request.user)

    @login_required
    async def logout(self, request):
        request.http_request.user = None
        request.http_request.permissions = set()

        self.prepare_request(request.http_request)

        return True

    @login_required
    async def create_user(self, request):
        loop = asyncio.get_event_loop()

        try:
            username = request.params['username']
            password = request.params['password']

        except (KeyError, TypeError):
            raise RpcInvalidParamsError

        return (await loop.run_in_executor(None, self._create_user,
                                           username, password))

    @login_required
    async def delete_user(self, request):
        loop = asyncio.get_event_loop()

        try:
            username = request.params['username']

        except (KeyError, TypeError):
            raise RpcInvalidParamsError

        return (await loop.run_in_executor(None, self._delete_user, username))

    @login_required
    async def set_password(self, request):
        loop = asyncio.get_event_loop()

        try:
            username = request.params.get('username',
                                          request.http_request.user)

            password = request.params['password']
            old_password = request.params.get('old_password', '')

        except (KeyError, TypeError):
            raise RpcInvalidParamsError

        return (await loop.run_in_executor(None, lambda: self._set_password(
                    username, password,
                    old_password=old_password)))
