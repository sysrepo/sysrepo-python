#!/usr/bin/env python3
# Copyright (c) 2020 6WIND S.A.
# SPDX-License-Identifier: BSD-3-Clause

"""
Minimalist example with sysrepoctl-like options.
"""

import argparse
import logging
import sys

import sysrepo


# ------------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "-l", "--list", action="store_true", help="List installed YANG modules."
    )
    group.add_argument("-i", "--install", help="Install YANG module.")
    group.add_argument("-u", "--uninstall", help="Uninstall YANG module.")
    parser.add_argument(
        "-v", "--verbose", action="count", default=0, help="Increase verbosity."
    )
    args = parser.parse_args()

    if args.verbose >= 3:
        level = logging.DEBUG
    elif args.verbose >= 2:
        level = logging.INFO
    elif args.verbose >= 1:
        level = logging.WARNING
    else:
        level = logging.ERROR
    logging.basicConfig(
        level=level, format="[%(levelname)s] sysrepoctl.py: %(message)s"
    )

    try:
        with sysrepo.SysrepoConnection() as conn:
            if args.list:
                for module in conn.get_ly_ctx():
                    if module.implemented():
                        print(module.name())
            elif args.install:
                conn.install_module(args.install)
            elif args.uninstall:
                conn.remove_module(args.uninstall)
        return 0
    except sysrepo.SysrepoError as e:
        logging.error("%s", e)
        return 1


# ------------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(main())
