# Copyright (c) 2020 6WIND S.A.
# SPDX-License-Identifier: BSD-3-Clause

import functools
import inspect
import logging
from typing import Any, Optional

from _sysrepo import ffi, lib


# ------------------------------------------------------------------------------
def str2c(s: Optional[str]):
    if s is None:
        return ffi.NULL
    if hasattr(s, "encode"):
        s = s.encode("utf-8")
    return ffi.new("char []", s)


# ------------------------------------------------------------------------------
def c2str(c) -> Optional[str]:
    if c == ffi.NULL:
        return None
    s = ffi.string(c)
    if hasattr(s, "decode"):
        s = s.decode("utf-8")
    return s


# ------------------------------------------------------------------------------
def is_async_func(func: Any) -> bool:
    if inspect.iscoroutinefunction(func):
        return True
    if isinstance(func, functools.partial):
        return is_async_func(func.func)
    return False


# ------------------------------------------------------------------------------
LOG = logging.getLogger("sysrepo")
LOG.addHandler(logging.NullHandler())
LOG_LEVELS_SR2PY = {
    lib.SR_LL_ERR: logging.ERROR,
    lib.SR_LL_WRN: logging.WARNING,
    lib.SR_LL_INF: logging.INFO,
    lib.SR_LL_DBG: logging.DEBUG,
}
LOG_LEVELS_PY2SR = {v: k for k, v in LOG_LEVELS_SR2PY.items()}
LOG_LEVELS_PY2SR[logging.CRITICAL] = lib.SR_LL_ERR


@ffi.def_extern(name="srpy_log_cb")
def log_callback(level, msg):
    py_level = LOG_LEVELS_SR2PY.get(level, logging.NOTSET)
    LOG.log(py_level, "%s", c2str(msg))


# ------------------------------------------------------------------------------
def configure_logging(
    *,
    stderr_level: int = logging.NOTSET,
    syslog_level: int = logging.NOTSET,
    syslog_app_name: str = "sysrepo",
    py_logging: bool = False
):
    """
    Configure logging for sysrepo. By default, all logging is disabled.

    All *_level arguments take standard python logging levels.

    :arg stderr_level:
        The level for standard error logging. If set to logging.NOTSET, standard error
        logging is disabled (the default).
    :arg syslog_level:
        The level for syslog logging. If set to logging.NOTSET, syslog logging is
        disabled (the default).
    :arg syslog_app_name:
        The name of the application sent in syslog messages.
    :arg py_logging:
        If True, enable logging via the python logging system. Logging level is
        controlled by python logging system.
    """
    sr_stderr_level = LOG_LEVELS_PY2SR.get(stderr_level, lib.SR_LL_NONE)
    lib.sr_log_stderr(sr_stderr_level)
    sr_syslog_level = LOG_LEVELS_PY2SR.get(syslog_level, lib.SR_LL_NONE)
    lib.sr_log_syslog(str2c(syslog_app_name), sr_syslog_level)
    if py_logging:
        lib.sr_log_set_cb(lib.srpy_log_cb)
    else:
        lib.sr_log_set_cb(ffi.NULL)


# ------------------------------------------------------------------------------
def get_syslog_level() -> int:
    """
    Return current syslog log level.

    :returns int:
        The log level.
    """
    return LOG_LEVELS_SR2PY.get(lib.sr_log_get_syslog(), logging.NOTSET)


# ------------------------------------------------------------------------------
def get_stderr_level() -> int:
    """
    Return current stderr log level.

    :returns int:
        The log level.
    """
    return LOG_LEVELS_SR2PY.get(lib.sr_log_get_stderr(), logging.NOTSET)
