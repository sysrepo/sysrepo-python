#!/usr/bin/env python3
# Copyright (c) 2020 6WIND S.A.
# SPDX-License-Identifier: BSD-3-Clause

"""
Minimalist example with sysrepocfg-like options.
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
        "-I",
        "--import",
        metavar="MODULE",
        dest="import_",
        help="""
        Replace the configuration of MODULE. Data is read from stdin.
        """,
    )
    group.add_argument(
        "-X",
        "--export",
        metavar="XPATH",
        help="""
        Export data pointed by XPATH. Printed to stdout.
        """,
    )
    group.add_argument(
        "-R",
        "--rpc",
        action="store_true",
        help="""
        Send a RPC/action. Read the input parameters from stdin. RPC/action
        output is printed to stdout.
        """,
    )
    group.add_argument(
        "-C",
        "--copy-from",
        metavar="DATASTORE",
        choices=("running", "startup", "operational", "candidate"),
        help="""
        Perform a copy-config from a datastore.
        """,
    )
    parser.add_argument(
        "-v", "--verbose", action="count", default=0, help="Increase verbosity."
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=("xml", "json", "lyb"),
        default="xml",
        help="""
        Data format to be used. By default based on file extension.
        """,
    )
    parser.add_argument(
        "-d",
        "--datastore",
        choices=("running", "startup", "operational", "candidate"),
        default="running",
        help="""
        Datastore to be operated on.
        """,
    )
    parser.add_argument(
        "-n",
        "--not-strict",
        action="store_true",
        default=False,
        help="""
        Silently ignore any unknown data.
        """,
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
        level=level, format="[%(levelname)s] sysrepocfg.py: %(message)s"
    )
    sysrepo.configure_logging(py_logging=True)

    try:
        with sysrepo.SysrepoConnection() as conn:
            with conn.start_session(args.datastore) as sess:
                if args.import_:
                    with conn.get_ly_ctx() as ctx:
                        data = ctx.parse_data_mem(
                            sys.stdin.read(),
                            args.format,
                            no_state=True,
                            strict=not args.not_strict,
                        )
                        sess.replace_config_ly(data, args.import_)

                elif args.export:
                    with sess.get_data_ly(args.export) as data:
                        data.print_file(
                            sys.stdout, args.format, pretty=True, with_siblings=True
                        )

                elif args.copy_from:
                    sess.copy_config(args.copy_from)

                elif args.rpc:
                    with conn.get_ly_ctx() as ctx:
                        rpc_input = ctx.parse_data_mem(
                            sys.stdin.read(),
                            args.format,
                            strict=not args.not_strict,
                        )
                        with sess.rpc_send_ly(rpc_input) as rpc_output:
                            try:
                                rpc_output.print_file(
                                    sys.stdout, args.format, pretty=True
                                )
                            finally:
                                rpc_input.free()

        return 0
    except sysrepo.SysrepoError as e:
        logging.error("%s", e)
        return 1


# ------------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(main())
