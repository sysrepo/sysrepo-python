# Copyright (c) 2020 6WIND S.A.
# SPDX-License-Identifier: BSD-3-Clause

import logging

from _sysrepo import ffi, lib
from .change import Change, ChangeCreated, ChangeDeleted, ChangeModified, ChangeMoved
from .connection import SysrepoConnection
from .errors import (
    SysrepoCallbackFailedError,
    SysrepoCallbackShelveError,
    SysrepoError,
    SysrepoExistsError,
    SysrepoInternalError,
    SysrepoInvalArgError,
    SysrepoLockedError,
    SysrepoLyError,
    SysrepoNomemError,
    SysrepoNotFoundError,
    SysrepoOperationFailedError,
    SysrepoSysError,
    SysrepoTimeOutError,
    SysrepoUnauthorizedError,
    SysrepoUnsupportedError,
    SysrepoValidationFailedError,
)
from .util import c2str, xpath_split
from .value import (
    AnyData,
    AnyXML,
    Binary,
    Bits,
    Bool,
    Container,
    ContainerPresence,
    Decimal64,
    Enum,
    IdentityRef,
    InstanceId,
    Int8,
    Int16,
    Int32,
    Int64,
    LeafEmpty,
    List,
    String,
    UInt8,
    UInt16,
    UInt32,
    UInt64,
    Value,
)


__all__ = [
    "SysrepoConnection",
    "Change",
    "ChangeCreated",
    "ChangeDeleted",
    "ChangeModified",
    "ChangeMoved",
    "SysrepoError",
    "SysrepoCallbackFailedError",
    "SysrepoCallbackShelveError",
    "SysrepoExistsError",
    "SysrepoInternalError",
    "SysrepoInvalArgError",
    "SysrepoLockedError",
    "SysrepoLyError",
    "SysrepoNomemError",
    "SysrepoNotFoundError",
    "SysrepoOperationFailedError",
    "SysrepoSysError",
    "SysrepoTimeOutError",
    "SysrepoUnauthorizedError",
    "SysrepoUnsupportedError",
    "SysrepoValidationFailedError",
    "xpath_split",
    "AnyData",
    "AnyXML",
    "Binary",
    "Bits",
    "Bool",
    "Container",
    "ContainerPresence",
    "Decimal64",
    "Enum",
    "IdentityRef",
    "InstanceId",
    "Int16",
    "Int32",
    "Int64",
    "Int8",
    "LeafEmpty",
    "List",
    "String",
    "UInt16",
    "UInt32",
    "UInt64",
    "UInt8",
    "Value",
]

LOG = logging.getLogger(__name__)
LOG.addHandler(logging.NullHandler())
lib.sr_log_set_cb(lib.srpy_log_cb)


@ffi.def_extern(name="srpy_log_cb")
def log_callback(level, msg):
    py_level = {
        lib.SR_LL_ERR: logging.ERROR,
        lib.SR_LL_WRN: logging.WARNING,
        lib.SR_LL_INF: logging.INFO,
        lib.SR_LL_DBG: logging.DEBUG,
    }.get(level, logging.NOTSET)
    LOG.log(py_level, "%s", c2str(msg))
