# Copyright (c) 2020 6WIND S.A.
# SPDX-License-Identifier: BSD-3-Clause

from typing import Any, Callable, Optional, Tuple

from _sysrepo import ffi, lib
from .util import c2str


# ------------------------------------------------------------------------------
class SysrepoError(Exception):

    rc = None
    __slots__ = ("msg",)

    def __init__(self, msg: str):
        super().__init__()
        self.msg = msg

    def __str__(self):
        return "%s: %s" % (self.msg, c2str(lib.sr_strerror(self.rc)))

    def __repr__(self):
        return "%s(%r)" % (type(self).__name__, self.msg)

    RC_CLASSES = {}

    @staticmethod
    def register(subclass):
        SysrepoError.RC_CLASSES[subclass.rc] = subclass
        return subclass

    @staticmethod
    def new(msg: str, rc: int) -> "SysrepoError":
        err_class = SysrepoError.RC_CLASSES[rc]
        return err_class(msg)


# ------------------------------------------------------------------------------
@SysrepoError.register
class SysrepoInvalArgError(SysrepoError):
    rc = lib.SR_ERR_INVAL_ARG


@SysrepoError.register
class SysrepoNomemError(SysrepoError):
    rc = lib.SR_ERR_NOMEM


@SysrepoError.register
class SysrepoNotFoundError(SysrepoError):
    rc = lib.SR_ERR_NOT_FOUND


@SysrepoError.register
class SysrepoInternalError(SysrepoError):
    rc = lib.SR_ERR_INTERNAL


@SysrepoError.register
class SysrepoUnsupportedError(SysrepoError):
    rc = lib.SR_ERR_UNSUPPORTED


@SysrepoError.register
class SysrepoValidationFailedError(SysrepoError):
    rc = lib.SR_ERR_VALIDATION_FAILED


@SysrepoError.register
class SysrepoOperationFailedError(SysrepoError):
    rc = lib.SR_ERR_OPERATION_FAILED


@SysrepoError.register
class SysrepoUnauthorizedError(SysrepoError):
    rc = lib.SR_ERR_UNAUTHORIZED


@SysrepoError.register
class SysrepoLockedError(SysrepoError):
    rc = lib.SR_ERR_LOCKED


@SysrepoError.register
class SysrepoTimeOutError(SysrepoError):
    rc = lib.SR_ERR_TIME_OUT


@SysrepoError.register
class SysrepoLyError(SysrepoError):
    rc = lib.SR_ERR_LY


@SysrepoError.register
class SysrepoSysError(SysrepoError):
    rc = lib.SR_ERR_SYS


@SysrepoError.register
class SysrepoExistsError(SysrepoError):
    rc = lib.SR_ERR_EXISTS


@SysrepoError.register
class SysrepoCallbackFailedError(SysrepoError):
    rc = lib.SR_ERR_CALLBACK_FAILED


@SysrepoError.register
class SysrepoCallbackShelveError(SysrepoError):
    rc = lib.SR_ERR_CALLBACK_SHELVE


# ------------------------------------------------------------------------------
def _get_error_msg(session) -> Optional[str]:
    """
    Get the error message information from the given session C pointer.

    :arg "sr_session_ctx_t *" session:
        A session C pointer allocated by libsysrepo.so.
    """
    msg = None
    err_info_p = ffi.new("sr_error_info_t **")
    if lib.sr_get_error(session, err_info_p) == lib.SR_ERR_OK:
        err_info = err_info_p[0]
        error_strings = []
        if err_info != ffi.NULL:
            for i in range(err_info.err_count):
                err = err_info.err[i]
                strings = []
                if err.xpath:
                    strings.append(c2str(err.xpath))
                if err.message:
                    strings.append(c2str(err.message))
                if strings:
                    error_strings.append(": ".join(strings))
        msg = ", ".join(error_strings)
    return msg


# ------------------------------------------------------------------------------
def check_call(
    func: Callable[..., int],
    *args: Any,
    valid_codes: Tuple[int, ...] = (lib.SR_ERR_OK,)
) -> int:
    """
    Wrapper around functions of libsysrepo.so.

    :arg func:
        A function from libsysrepo.so that is expected to return an int error
        code.
    :arg args:
        Positional arguments for the function.
    :arg valid_codes:
        Error code values that are considered as a "success". If the function
        returns a value not listed here, a SysrepoError exception will be risen.

    :returns:
        An error code SR_ERR_*.
    :raises SysrepoError:
        If the function returned an error code not listed in valid_codes. If
        the first argument in args is a sr_session_ctx_t object, use it to call
        sr_get_error() to get a detailed error message for the risen exception.
    """
    ret = func(*args)
    if ret not in valid_codes:
        msg = None
        if (
            args
            and isinstance(args[0], ffi.CData)
            and ffi.typeof(args[0]) == ffi.typeof("sr_session_ctx_t *")
        ):
            msg = _get_error_msg(args[0])
        if not msg:
            msg = "%s failed" % func.__name__
        raise SysrepoError.new(msg, ret)
    return ret
