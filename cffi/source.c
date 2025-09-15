/*
 * Copyright (c) 2022 Robin Jarry
 * SPDX-License-Identifier: BSD-3-Clause
 */

#include <sysrepo.h>
#include <sysrepo/version.h>
#include <sysrepo/netconf_acm.h>

#if (SR_VERSION_MAJOR != 8)
#error "This version of sysrepo bindings only works with libsysrepo.so.8"
#endif
