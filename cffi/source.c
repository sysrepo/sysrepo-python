/*
 * Copyright (c) 2022 Robin Jarry
 * SPDX-License-Identifier: BSD-3-Clause
 */

#include <sysrepo.h>
#include <sysrepo/version.h>

#if (SR_VERSION_MAJOR != 7)
#error "This version of sysrepo bindings only works with libsysrepo.so.7"
#endif
#if (SR_VERSION_MINOR < 10)
#error "Need at least libsysrepo.so.7.10"
#endif
