#!/usr/bin/env python3
# Copyright (c) 2020 6WIND S.A.
# SPDX-License-Identifier: BSD-3-Clause

"""
Minimalist application that subscribes to module changes, operational data
requests and RPC calls for the sysrepo-example.yang module.
"""

import argparse
import logging
import signal
import sys
import time

import libyang

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
    sysrepo.configure_logging(py_logging=True)

    try:
        with sysrepo.SysrepoConnection() as conn:
            with conn.start_session() as sess:
                logging.info("subscribing to module changes: sysrepo-example")
                sess.subscribe_module_change("sysrepo-example", None, module_change_cb)
                sess.subscribe_module_change_unsafe(
                    "sysrepo-example",
                    None,
                    module_change_unsafe_cb,
                    priority=1,
                )
                logging.info(
                    "subscribing to operational data requests: /sysrepo-example:state"
                )
                sess.subscribe_oper_data_request(
                    "sysrepo-example", "/sysrepo-example:state", oper_data_cb
                )
                logging.info("subscribing to rpc calls: /sysrepo-example:poweroff")
                sess.subscribe_rpc_call("/sysrepo-example:poweroff", poweroff)
                logging.info(
                    "subscribing to action calls: /sysrepo-example:conf/security/alarm/trigger"
                )
                sess.subscribe_rpc_call(
                    "/sysrepo-example:conf/security/alarm/trigger", trigger_alarm
                )
                signal.sigwait({signal.SIGINT, signal.SIGTERM})
        return 0
    except sysrepo.SysrepoError as e:
        logging.error("%s", e)
        return 1


# ------------------------------------------------------------------------------
def module_change_cb(event, req_id, changes, private_data):
    print()
    print("========================")
    print("Module changed event: %s (request ID %s)" % (event, req_id))
    print("----- changes -----")
    for c in changes:
        print(repr(c))
    print("----- end of changes -----")
    print()


# ------------------------------------------------------------------------------
def module_change_unsafe_cb(session, event, req_id, private_data):
    print()
    print("========================")
    print("(unsafe) Module changed event: %s (request ID %s)" % (event, req_id))
    print("----- changes -----")
    changes = list(session.get_changes("/sysrepo-example:conf//."))
    for c in changes:
        print(repr(c))
    print("----- end of changes -----")
    print()


# ------------------------------------------------------------------------------
def oper_data_cb(xpath, private_data):
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
    return data


# ------------------------------------------------------------------------------
def poweroff(xpath, input_params, event, private_data):
    print()
    print("========================")
    print("RPC call: %s" % xpath)
    print("params: %s" % input_params)
    out = {"message": "bye bye"}
    print("returning %s" % out)
    print("---------------")
    print()
    return out


# ------------------------------------------------------------------------------
def trigger_alarm(xpath, input_params, event, private_data):
    print()
    print("========================")
    print("Action call: %s" % xpath)
    print("params: %s" % input_params)
    _, _, keys = list(libyang.xpath_split(xpath))[2]
    _, alarm_name = keys[0]
    seconds = input_params["duration"]
    out = {"message": "%s alarm triggered for %s seconds" % (alarm_name, seconds)}
    print("returning %s" % out)
    print("---------------")
    print()
    time.sleep(seconds)
    return out


# ------------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(main())
