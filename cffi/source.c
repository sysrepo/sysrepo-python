/*
 * Copyright (c) 2022 Robin Jarry
 * SPDX-License-Identifier: BSD-3-Clause
 */

#include <sysrepo.h>
#include <sysrepo/version.h>

#if (SR_VERSION_MAJOR != 7)
#error "This version of sysrepo bindings only works with sysrepo 7.x"
#endif
#if (SR_VERSION_MINOR < 6)
#error "Need at least sysrepo 7.6"
#endif
