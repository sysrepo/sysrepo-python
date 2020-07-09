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
           out = sess.rpc_send({"my-rpc": {"input-param": 42}}, "my-module")

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

Contributing
============

This is an open source project and all contributions are welcome.

Issues
------

Please create new issues for any bug you discover at
https://github.com/sysrepo/sysrepo-python/issues/new. It is not necessary to
file a bug if you are preparing a patch.

Pull Requests
-------------

Here are the steps for submitting a change in the code base:

#. Fork the repository: https://github.com/sysrepo/sysrepo-python/fork

#. Clone your own fork into your development machine::

      git clone https://github.com/<you>/libyang-python

#. Create a new branch named after what your are working on::

      git checkout -b my-topic

#. Edit the code and call ``make format`` to ensure your modifications comply
   with the `coding style`__.

   __ https://black.readthedocs.io/en/stable/the_black_code_style.html

   Your contribution must be licensed under the `BSD 3-Clause "New" or "Revised"
   License`__ . At least one copyright notice is expected in new files.

   __ https://spdx.org/licenses/BSD-3-Clause.html

#. If you are adding a new feature or fixing a bug, please consider adding or
   updating unit tests.

#. Before creating commits, run ``make lint`` and ``make tests`` to check if
   your changes do not break anything. You can also run ``make`` which will run
   both.

#. Create commits by following these simple guidelines:

   -  Solve only one problem per commit.
   -  Use a short (less than 72 characters) title on the first line followed by
      an blank line and a more thorough description body.
   -  Wrap the body of the commit message should be wrapped at 72 characters too
      unless it breaks long URLs or code examples.
   -  If the commit fixes a Github issue, include the following line::

        Fixes: #NNNN

   Inspirations:

   https://chris.beams.io/posts/git-commit/
   https://wiki.openstack.org/wiki/GitCommitMessages

#. Push your topic branch in your forked repository::

      git push origin my-topic

   You should get a message from Github explaining how to create a new pull
   request.

#. Wait for a reviewer to merge your work. If minor adjustments are requested,
   use ``git commit --fixup $sha1`` to make it obvious what commit you are
   adjusting. If bigger changes are needed, make them in new separate commits.
   Once the reviewer is happy, please use ``git rebase --autosquash`` to amend
   the commits with their small fixups (if any), and ``git push --force`` on
   your topic branch.

Thank you in advance for your contributions!
