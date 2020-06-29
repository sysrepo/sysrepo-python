# Copyright (c) 2020 6WIND S.A.
# SPDX-License-Identifier: BSD-3-Clause

import os
import shlex

import cffi


HERE = os.path.dirname(__file__)

BUILDER = cffi.FFI()
with open(os.path.join(HERE, "cdefs.h")) as f:
    BUILDER.cdef(f.read())

HEADERS = os.environ.get("SYSREPO_HEADERS", "").strip().split(":")
LIBRARIES = os.environ.get("SYSREPO_LIBRARIES", "").strip().split(":")
EXTRA_CFLAGS = ["-Werror", "-std=c99"]
EXTRA_CFLAGS += shlex.split(os.environ.get("SYSREPO_EXTRA_CFLAGS", ""))
EXTRA_LDFLAGS = shlex.split(os.environ.get("SYSREPO_EXTRA_LDFLAGS", ""))

BUILDER.set_source(
    "_sysrepo",
    "#include <sysrepo.h>",
    libraries=["sysrepo", "yang"],
    extra_compile_args=EXTRA_CFLAGS,
    extra_link_args=EXTRA_LDFLAGS,
    include_dirs=HEADERS,
    library_dirs=LIBRARIES,
    py_limited_api=False,
)

if __name__ == "__main__":
    BUILDER.compile()
