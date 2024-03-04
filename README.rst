==============
sysrepo-python
==============

Python CFFI bindings to sysrepo_.

.. _libyang: https://github.com/CESNET/libyang
.. _sysrepo: https://github.com/sysrepo/sysrepo

|pypi-project|__ |python-versions|__ |build-status|__ |license|__ |code-style|__

__ https://pypi.org/project/sysrepo
__ https://github.com/sysrepo/sysrepo-python/actions
__ https://github.com/sysrepo/sysrepo-python/actions
__ https://github.com/sysrepo/sysrepo-python/blob/master/LICENSE
__ https://github.com/psf/black

.. |pypi-project| image:: https://img.shields.io/pypi/v/sysrepo.svg
.. |python-versions| image:: https://img.shields.io/pypi/pyversions/sysrepo.svg
.. |build-status| image:: https://github.com/sysrepo/sysrepo-python/workflows/CI/badge.svg
.. |license| image:: https://img.shields.io/github/license/sysrepo/sysrepo-python.svg
.. |code-style| image:: https://img.shields.io/badge/code%20style-black-000000.svg

Installation
============

.. code-block:: bash

   pip install sysrepo

This assumes that ``libsysrepo.so`` is installed on the system and that
``sysrepo.h`` is available in the system include dirs.

Since sysrepo_ depends on libyang_, the latter needs to be installed on the
system as well.

You need the following system dependencies installed:

- Python development headers
- GCC
- Python CFFI module

On a Debian/Ubuntu system:

.. code-block:: bash

   apt-get install python3-dev gcc python3-cffi

Compatibility
-------------

The current version requires at least C `sysrepo 2.2.0`__.

The last version of the bindings that works with C `sysrepo 1.x`__ is v0.7.0__.

__ https://github.com/sysrepo/sysrepo/commit/8c48a7a50eb2
__ https://github.com/sysrepo/sysrepo/tree/libyang1
__ https://pypi.org/project/sysrepo/0.7.0/

Compilation Flags
-----------------

If sysrepo_ headers and libraries are installed in a non-standard location, you
can export the ``SYSREPO_HEADERS`` and ``SYSREPO_LIBRARIES`` variables.
Additionally, for finer control, you may use ``SYSREPO_EXTRA_CFLAGS`` and
``SYSREPO_EXTRA_LDFLAGS``:

.. code-block:: bash

   SYSREPO_HEADERS=/home/build/opt/sr/include \
   SYSREPO_LIBRARIES=/home/build/opt/sr/lib \
   SYSREPO_EXTRA_CFLAGS="-O3" \
   SYSREPO_EXTRA_LDFLAGS="-Wl,-rpath=/opt/sr/lib" \
           pip install sysrepo

.. note::

   This Python package depends on libyang_ CFFI bindings, if it is not installed
   yet and libyang_ headers and libraries are also installed in a non-standard
   location, you must export additional variables. See the "Compilation Flags"
   section here: https://pypi.org/project/libyang/.

Examples
========

Module Config Replacement
-------------------------

.. code-block:: python

   with sysrepo.SysrepoConnection() as conn:
       with conn.start_session() as sess:
           sess.replace_config({"system": {"hostname": "foobar"}}, "my-module")

Operational Data Request
------------------------

.. code-block:: python

   with sysrepo.SysrepoConnection() as conn:
       with conn.start_session("operational") as sess:
           data = sess.get_data("/my-module:status")

RPC Call
--------

.. code-block:: python

   with sysrepo.SysrepoConnection() as conn:
       with conn.start_session() as sess:
           out = sess.rpc_send("/my-module:my-rpc", {"input-param": 42})

Subscription
------------

.. code-block:: python

   with sysrepo.SysrepoConnection() as conn:
       with conn.start_session() as sess:
           sess.subscribe_module_change("my-module", None, module_change_cb)
           sess.subscribe_oper_data_request(
               "my-module", "/my-module:status", oper_data_cb)
           sess.subscribe_rpc_call("/my-module:my-rpc", my_rpc_cb)

See the ``examples/`` folder for more details.

Differences With ``libsysrepo.so`` C API
========================================

This project has been created with Python users in mind. In order to get a more
pythonic API there are significant divergences with the C API.

Supported Features
------------------

-  Connection handling (``sr_connect()``, ``sr_disconnect()``)
-  YANG modules management (``sr_install_module()``, ``sr_remove_module()``)
-  libyang context retrieval (``sr_get_context()`` wrapped using the `libyang
   CFFI bindings`__).
-  Session management (``sr_session_start()``, ``sr_session_stop()``,
   ``sr_session_switch_ds()``, ``sr_session_get_ds()``, ``sr_unsubscribe()``)
-  Module change subscriptions (``sr_module_change_subscribe()`` also with
   async_ callbacks, ``sr_get_changes_iter()``).
-  Operational data subscriptions (``sr_oper_get_items_subscribe()`` also with
   async_ callbacks).
-  RPC/action call subscriptions (``sr_rpc_subscribe_tree()`` also with async_
   callbacks).
-  Notifications subscriptions (``sr_event_notif_subscribe_tree()`` also with
   async_ callbacks).
-  Notification dispatch (``sr_event_notif_send_tree()``).
-  RPC/action calling (``sr_rpc_send_tree()``)
-  Datastore edition (``sr_set_item_str()``, ``sr_delete_item()``,
   ``sr_edit_batch()``, ``sr_validate()``, ``sr_apply_changes()``,
   ``sr_discard_changes()``, ``sr_replace_config()``)
-  Get data (``sr_get_data()``, ``sr_get_item()``, ``sr_get_items()``)
-  Module locking (``sr_*lock*``)

__ https://pypi.org/project/libyang/
.. _async: https://docs.python.org/3/library/asyncio-task.html#coroutine

Partially Supported Features
----------------------------

All other features are not yet or only partially supported by sysrepo-python. The most notable
are:

-  Module management (``sr_*_module_*``)

Contributing
============

This is an open source project and all contributions are welcome.

See the `CONTRIBUTING.rst`__ file for more details.

__ https://github.com/sysrepo/sysrepo-python/blob/master/CONTRIBUTING.rst
