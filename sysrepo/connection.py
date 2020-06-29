# Copyright (c) 2020 6WIND S.A.
# SPDX-License-Identifier: BSD-3-Clause

import logging
from typing import Optional, Sequence

import libyang

from _sysrepo import ffi, lib
from .errors import SysrepoInternalError, check_call
from .session import SysrepoSession, datastore_value
from .util import str2c


LOG = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
class SysrepoConnection:
    """
    Create a connection to the sysrepo datastore. If possible (no other connections
    exist), also apply any scheduled changes.

    Do not use `os.fork` after creating a connection. Sysrepo internally stores PID of
    every created connection and this way a mismatch of PID and connection is created.

    The created object can be used as a context manager and will be automatically
    "closed" on exit::

        with sysrepo.SysrepoConnection() as conn:
            # to stuff with conn
        # conn.disconnect() has been called whatever happens
    """

    __slots__ = ("cdata",)

    def __init__(
        self,
        cache_running: bool = False,
        no_sched_changes: bool = False,
        err_on_sched_fail: bool = False,
    ):
        """
        :arg cache_running:
            Always cache running datastore data which makes mainly repeated retrieval of
            data much faster. Affects all sessions created on this connection.
        :arg no_sched_changes:
            Do not parse internal modules data and apply any scheduled changes. Makes
            creating the connection faster but, obviously, scheduled changes are not
            applied.
        :arg err_on_sched_fail:
            If applying any of the scheduled changes fails, do not create a connection
            and return an error.
        """
        flags = 0
        if cache_running:
            flags |= lib.SR_CONN_CACHE_RUNNING
        if no_sched_changes:
            flags |= lib.SR_CONN_NO_SCHED_CHANGES
        if err_on_sched_fail:
            flags |= lib.SR_CONN_ERR_ON_SCHED_FAIL
        conn_p = ffi.new("sr_conn_ctx_t **")
        check_call(lib.sr_connect, flags, conn_p)
        self.cdata = conn_p[0]

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        self.disconnect()

    def disconnect(self) -> None:
        """
        Disconnect from the sysrepo datastore.

        Cleans up and frees connection context allocated when instantiating the object.
        All sessions and subscriptions started within the connection will be
        automatically stopped and cleaned up too.

        Connection and all its associated sessions and subscriptions can no longer be
        used even on error.
        """
        try:
            check_call(lib.sr_disconnect, self.cdata)
        finally:
            self.cdata = None

    def start_session(self, datastore: str = "running") -> SysrepoSession:
        """
        Start a new session.

        :arg datastore:
            Datastore on which all sysrepo functions within this session will operate.
            Later on, datastore can be later changed using
            `SysrepoSession.switch_datastore`.

        :returns:
            A `SysrepoSession` object that can be used as a context manager. It will be
            automatically stopped when the manager exits::

                with conn.start_session() as sess:
                    # to stuff with sess
                # sess.stop() has been called whatever happens
        """
        ds = datastore_value(datastore)
        sess_p = ffi.new("sr_session_ctx_t **")
        check_call(lib.sr_session_start, self.cdata, ds, sess_p)
        return SysrepoSession(sess_p[0])

    def get_ly_ctx(self) -> libyang.Context:
        """
        :returns:
            The `libyang.Context` object associated with this connection.
        """
        ctx = lib.sr_get_context(self.cdata)
        if not ctx:
            raise SysrepoInternalError("sr_get_context failed")
        return libyang.Context(cdata=ctx)

    def install_module(
        self,
        filepath: str,
        searchdirs: Optional[str] = None,
        enabled_features: Sequence[str] = (),
    ) -> None:
        """
        Install a new schema (module) into sysrepo. Deferred until there are no
        connections!

        :arg filepath:
            Path to the new schema. Can have either YANG or YIN extension/format.
        :arg searchdirs:
            Optional search directories for import schemas, supports the format
            `<dir>[:<dir>]*`.
        :arg enabled_features:
            Array of enabled features.
        """
        if enabled_features:
            # convert to C strings array
            features = tuple(str2c(f) for f in enabled_features)
        else:
            features = ffi.NULL
        check_call(
            lib.sr_install_module,
            self.cdata,
            str2c(filepath),
            str2c(searchdirs),
            features,
            len(enabled_features),
        )

    def remove_module(self, name: str) -> None:
        """
        Remove an installed module from sysrepo. Deferred until there are no
        connections!

        :arg str name:
            Name of the module to remove.
        """
        check_call(lib.sr_remove_module, self.cdata, str2c(name))
