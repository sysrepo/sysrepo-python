# Copyright (c) 2020 6WIND S.A.
# SPDX-License-Identifier: BSD-3-Clause

from contextlib import contextmanager
import logging
import signal
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

    def __init__(self, cache_running: bool = False):
        """
        :arg cache_running:
            Always cache running datastore data which makes mainly repeated retrieval of
            data much faster. Affects all sessions created on this connection.
        """
        flags = 0
        if cache_running:
            flags |= lib.SR_CONN_CACHE_RUNNING

        # mandatory flag to work with libyang-python
        flags |= lib.SR_CONN_CTX_SET_PRIV_PARSED

        conn_p = ffi.new("sr_conn_ctx_t **")
        # valid_signals() is only available since python 3.8
        valid_signals = getattr(signal, "valid_signals", lambda: range(1, signal.NSIG))
        sigmask = signal.pthread_sigmask(signal.SIG_BLOCK, valid_signals())
        try:
            check_call(lib.sr_connect, flags, conn_p)
            self.cdata = ffi.gc(conn_p[0], lib.sr_disconnect)
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, sigmask)

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
        if self.cdata is not None:
            if hasattr(ffi, "release"):
                ffi.release(self.cdata)  # causes sr_disconnect to be called
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

    def acquire_context(self) -> libyang.Context:
        """
        :returns:
            The `libyang.Context` object associated with this connection.
        """
        ctx = lib.sr_acquire_context(self.cdata)
        if not ctx:
            raise SysrepoInternalError("sr_get_context failed")
        return libyang.Context(cdata=ctx)

    def release_context(self):
        lib.sr_release_context(self.cdata)

    @contextmanager
    def get_ly_ctx(self) -> libyang.Context:
        """
        :returns:
            The `libyang.Context` object associated with this connection.
        """
        try:
            yield self.acquire_context()
        finally:
            self.release_context()

    def install_module(
        self,
        filepath: str,
        searchdirs: Optional[str] = None,
        enabled_features: Sequence[str] = (),
        ignore_already_exists=True,
    ) -> None:
        """
        Install a new schema (module) into sysrepo.

        :arg filepath:
            Path to the new schema. Can have either YANG or YIN extension/format.
        :arg searchdirs:
            Optional search directories for import schemas, supports the format
            `<dir>[:<dir>]*`.
        :arg enabled_features:
            Array of enabled features.
        :arg ignore_already_exists:
            Ignore error if module already exists in sysrepo.
        """
        if enabled_features:
            # convert to C strings array
            features = tuple([str2c(f) for f in enabled_features] + [ffi.NULL])
        else:
            features = ffi.NULL

        if ignore_already_exists:
            valid_codes = (lib.SR_ERR_OK, lib.SR_ERR_EXISTS)
        else:
            valid_codes = (lib.SR_ERR_OK,)
        check_call(
            lib.sr_install_module,
            self.cdata,
            str2c(filepath),
            str2c(searchdirs),
            features,
            valid_codes=valid_codes,
        )

    def remove_module(self, name: str, force: bool = False) -> None:
        """
        Remove an installed module from sysrepo. Deferred until there are no
        connections!

        :arg str name:
            Name of the module to remove.
        """
        check_call(lib.sr_remove_module, self.cdata, str2c(name), force)

    def enable_module_feature(self, name: str, feature_name: str) -> None:
        """
        Enable a module feature.

        :arg str name:
            Name of the module.
        :arg str feature_name:
            Name of the feature.
        """
        check_call(
            lib.sr_enable_module_feature, self.cdata, str2c(name), str2c(feature_name)
        )
