# Copyright (c) 2020 6WIND S.A.
# SPDX-License-Identifier: BSD-3-Clause

import functools
import inspect
from typing import Any, Optional

from _sysrepo import ffi


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
