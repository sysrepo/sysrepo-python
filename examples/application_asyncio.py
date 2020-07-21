#!/usr/bin/env python3
# Copyright (c) 2020 6WIND S.A.
# SPDX-License-Identifier: BSD-3-Clause

"""
Minimalist application that subscribes to module changes, operational data
requests and RPC calls for the sysrepo-example.yang module using an asyncio
event loop and coroutines.
"""

import argparse
import asyncio
import logging
import signal
import sys

import sysrepo


# ------------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description=__doc__)
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
    logging.basicConfig(level=level, format="[%(levelname)s] application: %(message)s")

    loop = asyncio.get_event_loop()
    stop_event = asyncio.Event()
    loop.add_signal_handler(signal.SIGINT, stop_event.set)
    loop.add_signal_handler(signal.SIGTERM, stop_event.set)

    try:
        with sysrepo.SysrepoConnection() as conn:
            with conn.start_session() as sess:
                logging.info("subscribing to module changes: sysrepo-example")
                sess.subscribe_module_change(
                    "sysrepo-example", None, module_change_cb, asyncio_register=True
                )
                logging.info(
                    "subscribing to operational data requests: /sysrepo-example:state"
                )
                sess.subscribe_oper_data_request(
                    "sysrepo-example",
                    "/sysrepo-example:state",
                    oper_data_cb,
                    asyncio_register=True,
                )
                logging.info("subscribing to rpc calls: /sysrepo-example:poweroff")
                sess.subscribe_rpc_call(
                    "/sysrepo-example:poweroff", poweroff, asyncio_register=True
                )
                loop.run_until_complete(stop_event.wait())
        return 0
    except sysrepo.SysrepoError as e:
        logging.error("%s", e)
        return 1


# ------------------------------------------------------------------------------
async def module_change_cb(event, req_id, changes, private_data):
    print()
    print("========================")
    print("Module changed event: %s (request ID %s)" % (event, req_id))
    print("----- changes -----")
    for c in changes:
        print(repr(c))
    print("----- end of changes -----")
    print()
    await asyncio.sleep(0)


# ------------------------------------------------------------------------------
async def oper_data_cb(xpath, private_data):
    print()
    print("========================")
    print("Operational data request for %s" % xpath)
    data = {
        "state": {
            "system": {"hostname": "foobar"},
            "network": {
                "interface": [
                    {
                        "name": "eth0",
                        "address": "1.2.3.4/24",
                        "stats": {"rx": 123456789, "tx": 987654321},
                    },
                    {
                        "name": "vlan12",
                        "address": "4.3.2.1/24",
                        "stats": {"rx": 0, "tx": 42},
                    },
                ]
            },
        }
    }
    print("returning %s" % data)
    print("---------------")
    print()
    await asyncio.sleep(0)
    return data


# ------------------------------------------------------------------------------
async def poweroff(xpath, input_params, event, private_data):
    print()
    print("========================")
    print("RPC call: %s" % xpath)
    print("params: %s" % input_params)
    out = {"poweroff": {"message": "bye bye"}}
    print("returning %s" % out)
    print("---------------")
    print()
    await asyncio.sleep(0)
    return out


# ------------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(main())
