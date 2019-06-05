.. image:: https://img.shields.io/pypi/v/aiohttp-json-rpc.svg
   :target: https://pypi.org/project/aiohttp-json-rpc

.. image:: https://img.shields.io/travis/com/pengutronix/aiohttp-json-rpc/master.svg?label=Linux%20build%20%40%20Travis%20CI
   :target: http://travis-ci.com/pengutronix/aiohttp-json-rpc

.. image:: https://img.shields.io/pypi/pyversions/aiohttp-json-rpc.svg

aiohttp-json-rpc
================

Implements `JSON-RPC 2.0 Specification <http://www.jsonrpc.org/specification>`_ using `aiohttp <http://aiohttp.readthedocs.org/en/stable/>`_

+---------------+---------------+
| Protocol      | Support       |
+===============+===============+
| Websocket     | since v0.1    |
+---------------+---------------+
| POST          | TODO          |
+---------------+---------------+
| GET           | TODO          |
+---------------+---------------+


Installation
------------

.. code-block:: shell

  pip install aiohttp-json-rpc


Usage
-----

RPC methods can be added by using ``rpc.add_method()``.

All RPC methods are getting passed a ``aiohttp_json_rpc.communicaton.JsonRpcRequest``.


Server
~~~~~~

The following code implements a simple RPC server that serves the method ``ping`` on ``localhost:8080``.

.. code-block:: python

  from aiohttp.web import Application, run_app
  from aiohttp_json_rpc import JsonRpc
  import asyncio


  async def ping(request):
      return 'pong'


  if __name__ == '__main__':
      loop = asyncio.get_event_loop()

      rpc = JsonRpc()
      rpc.add_methods(
          ('', ping),
      )

      app = Application(loop=loop)
      app.router.add_route('*', '/', rpc.handle_request)

      run_app(app, host='0.0.0.0', port=8080)


Client (JS)
~~~~~~~~~~~

The following code implements a simple RPC client that connects to the server above
and prints all incoming messages to the console.

.. code-block:: html

  <script src="//code.jquery.com/jquery-2.2.1.js"></script>
  <script>
    var ws = new WebSocket("ws://localhost:8080");
    var message_id = 0;

    ws.onmessage = function(event) {
      console.log(JSON.parse(event.data));
    }

    function ws_call_method(method, params) {
      var request = {
        jsonrpc: "2.0",
        id: message_id,
        method: method,
        params: params
      }

      ws.send(JSON.stringify(request));
      message_id++;
    }
  </script>

These are example responses the server would give if you call ``ws_call_method``.

.. code-block:: html

  --> ws_call_method("get_methods")
  <-- {"jsonrpc": "2.0", "result": ["get_methods", "ping"], "id": 1}

  --> ws_call_method("ping")
  <-- {"jsonrpc": "2.0", "method": "ping", "params": "pong", "id": 2}

Client (Python)
~~~~~~~~~~~~~~~

There's also Python client, which can be used as follows:

.. code-block:: python

  from aiohttp_json_rpc import JsonRpcClient


  async def ping_json_rpc():
      """Connect to ws://localhost:8080/, call ping() and disconnect."""
      rpc_client = JsonRpcClient()
      try:
          await rpc_client.connect('localhost', 8080)
          call_result = await rpc_client.call('ping')
          print(call_result)  # prints 'pong' (if that's return val of ping)
      finally:
          await rpc_client.disconnect()


  asyncio.get_event_loop().run_until_complete(ping_json_rpc())

Or use asynchronous context manager interface:

.. code-block:: python

  from aiohttp_json_rpc import JsonRpcClientContext
  
  
  async def jrpc_coro():
      async with JsonRpcClientContext('ws://localhost:8000/rpc') as jrpc:
          # `some_other_method` will get request.params filled with `args` and
          # `kwargs` keys:
          method_res = await jrpc.some_other_method('arg1', key='arg2')
  
      return method_res
  
  asyncio.get_event_loop().run_until_complete(jrpc_coro())


Features
--------

Error Handling
~~~~~~~~~~~~~~

All errors specified in the `error specification <http://www.jsonrpc.org/specification#error_object>`_ but the InvalidParamsError are handled internally.

If your coroutine got called with wrong params you can raise an ``aiohttp_json_rpc.RpcInvalidParamsError`` instead of sending an error by yourself.

The JSONRPC protocol defines a range for server defined errors.
``aiohttp_json_rpc.RpcGenericServerDefinedError`` implements this feature.

.. code-block:: python

  from aiohttp_json_rpc import RpcInvalidParamsError


  async def add(request):
      try:
          a = params.get('a')
          b = params.get('b')

          return a + b

      except KeyError:
          raise RpcInvalidParamsError


    async def add(request):
        raise RpcGenericServerDefinedError(
            error_code=-32050,
            message='Computer says no.',
        )


Error Logging
~~~~~~~~~~~~~

Every traceback caused by an RPC method will be caught and logged.

The RPC will send an RPC ServerError and proceed as if nothing happened.

.. code-block:: python

  async def divide(request):
      return 1 / 0  # will raise a ZeroDivisionError

.. code-block::

  ERROR:JsonRpc: Traceback (most recent call last):
  ERROR:JsonRpc:   File "aiohttp_json_rpc/base.py", line 289, in handle_websocket_request
  ERROR:JsonRpc:     rsp = yield from methods[msg['method']](ws, msg)
  ERROR:JsonRpc:   File "./example.py", line 12, in divide
  ERROR:JsonRpc:     return 1 / 0
  ERROR:JsonRpc: ZeroDivisionError: division by zero


Publish Subscribe
~~~~~~~~~~~~~~~~~

Any client of an RPC object can subscribe to a topic using the built-in RPC method ``subscribe()``.

Topics can be added using ``rpc.add_topics``.


Authentication
~~~~~~~~~~~~~~

The auth system works like in Django with decorators.
For details see the corresponding Django documentation.

+--------------------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Decorator                                        | Django Equivalent                                                                                                                                                     |
+==================================================+=======================================================================================================================================================================+
| aiohttp_json_rpc.django.auth.login_required      | `django.contrib.auth.decorators.login_required <https://docs.djangoproject.com/en/1.8/topics/auth/default/#django.contrib.auth.decorators.login_required>`_           |
+--------------------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| aiohttp_json_rpc.django.auth.permission_required | `django.contrib.auth.decorators.permission_required <https://docs.djangoproject.com/en/1.8/topics/auth/default/#django.contrib.auth.decorators.permission_required>`_ |
+--------------------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| aiohttp_json_rpc.django.auth.user_passes_test    | `django.contrib.auth.decorators.user_passes_test <https://docs.djangoproject.com/en/1.8/topics/auth/default/#django.contrib.auth.decorators.user_passes_test>`_       |
+--------------------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------+

.. code-block:: python

  from aiohttp_json_rpc.auth import (
      permission_required,
      user_passes_test,
      login_required,
  )

  from aiohttp_json_rpc.auth.django import DjangoAuthBackend
  from aiohttp_json_rpc import JsonRpc

  @login_required
  @permission_required('ping')
  @user_passes_test(lambda user: user.is_superuser)
  async def ping(request):
      return 'pong'

  if __name__ == '__main__':
      rpc = JsonRpc(auth_backend=DjangoAuthBackend())

      rpc.add_methods(
          ('', ping),
      )

      rpc.add_topics(
          ('foo', [login_required, permission_required('foo')])
      )


Class References
----------------

class aiohttp_json_rpc.JsonRpc(object)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Methods
'''''''

``def add_methods(self, *args, prefix='')``
  Args have to be tuple containing a prefix as string (may be empty) and a module,
  object, coroutine or import string.

  If second arg is module or object all coroutines in it are getting added.

``async def get_methods()``
  Returns list of all available RPC methods.

``def filter(self, topics)``
  Returns generator over all clients that have subscribed for given topic.

  Topics can be string or a list of strings.

``async def notify(self, topic, data)``
  Send RPC notification to all connected clients subscribed to given topic.

  Data has to be JSON serializable.

  Uses ``filter()``.

``async def subscribe(topics)``
  Subscribe to a topic.

  Topics can be string or a list of strings.

``async def unsubscribe(topics)``
  Unsubscribe from a topic.

  Topics can be string or a list of strings.

``async def get_topics()``
  Get subscribable  topics as list of strings.
