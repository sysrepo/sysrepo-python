# Copyright (c) 2020 6WIND S.A.
# SPDX-License-Identifier: BSD-3-Clause

import functools
import inspect
import re
from typing import Any, Iterator, List, Optional, Tuple

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


# ------------------------------------------------------------------------------
def xpath_split(
    xpath: str,
) -> Iterator[Tuple[Optional[str], str, List[Tuple[str, str]]]]:
    """
    Return an iterator that yields xpath components:

        (prefix, name, keys)

    :var str prefix:
        The YANG prefix where ``name`` is defined. May be empty if no
        prefix is specified.
    :var str name:
        The name of the YANG element (container, list, leaf, leaf-list).
    :var list(tuple(str, str)) keys:
        A list of tuples (key_name, key_value). Only defined if ``name``
        is a list element.
    """
    xpath = xpath.strip()
    total_len = len(xpath)
    i = 0
    xpath_re = re.compile(r"/(?:([-\w]+):)?([-\w\*]+)")

    while i < total_len:
        match = xpath_re.search(xpath, i)
        if not match:
            break
        prefix, name = match.groups("")

        keys = []
        i = match.end()
        while i < total_len and xpath[i] == "[":
            i += 1  # skip opening '['
            j = xpath.index("=", i)  # find key name end
            key_name = xpath[i:j]
            quote = xpath[j + 1]  # record opening quote character
            j = i = j + 2  # skip '=' and opening quote
            while True:
                if xpath[j] == "\\":
                    j += 1  # skip escaped character
                elif xpath[j] == quote:
                    break  # end of key value
                j += 1
            # replace escaped chars by their non-escape version
            key_value = re.sub(r"\\(.)", r"\1", xpath[i:j])
            keys.append((key_name, key_value))
            i = j + 2  # skip closing quote and ']'

        yield prefix, name, keys
