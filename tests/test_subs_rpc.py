# Copyright (c) 2020 6WIND S.A.
# SPDX-License-Identifier: BSD-3-Clause

import getpass
import logging
import os
import unittest

import libyang

import sysrepo


YANG_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "examples/sysrepo-example.yang"
)
sysrepo.configure_logging(stderr_level=logging.ERROR)


# ------------------------------------------------------------------------------
class RpcSubscriptionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conn = sysrepo.SysrepoConnection()
        cls.conn.install_module(YANG_FILE, enabled_features=["turbo"])

    @classmethod
    def tearDownClass(cls):
        # we have to disconnect first to release all resources
        cls.conn.disconnect()
        with sysrepo.SysrepoConnection() as c:
            c.remove_module("sysrepo-example")

    def test_rpc_sub(self):
        priv = object()
        calls = []
        rpc_xpath = "/sysrepo-example:poweroff"

        def rpc_cb(xpath, input_params, event, private_data):
            calls.append((xpath, input_params, event, private_data))
            behaviour = input_params.get("behaviour")
            if behaviour == "failure":
                raise sysrepo.SysrepoCallbackFailedError("poweroff failed")
            if behaviour == "bad-output":
                return {"unkown-leaf": False}
            return {"message": "bye bye"}

        with self.conn.start_session() as sess:
            sess.subscribe_rpc_call(rpc_xpath, rpc_cb, private_data=priv, strict=True)

            with self.conn.start_session() as rpc_sess:
                input_params = {"behaviour": "failure"}
                with self.assertRaises(sysrepo.SysrepoCallbackFailedError):
                    rpc_sess.rpc_send(rpc_xpath, input_params)
                self.assertEqual(len(calls), 1)
                self.assertEqual(calls[0], (rpc_xpath, input_params, "rpc", priv))
                del calls[:]

                input_params = {"behaviour": "bad-output"}
                with self.assertRaises(sysrepo.SysrepoCallbackFailedError):
                    rpc_sess.rpc_send(rpc_xpath, input_params)
                self.assertEqual(len(calls), 1)
                self.assertEqual(calls[0], (rpc_xpath, input_params, "rpc", priv))
                del calls[:]

                input_params = {"behaviour": "success"}
                output = rpc_sess.rpc_send(rpc_xpath, input_params)
                self.assertEqual(output, {"message": "bye bye"})
                self.assertEqual(len(calls), 1)
                self.assertEqual(calls[0], (rpc_xpath, input_params, "rpc", priv))
                del calls[:]

    def test_action_sub(self):
        priv = object()
        calls = []
        subs_xpath = "/sysrepo-example:conf/security/alarm/trigger"

        def action_cb(xpath, input_params, event, private_data):
            calls.append((xpath, input_params, event, private_data))
            _, _, keys = list(libyang.xpath_split(xpath))[2]
            _, name = keys[0]
            duration = input_params["duration"]
            return {
                "message": "%s alarm triggered for %s seconds"
                % (
                    name,
                    duration,
                )
            }

        def module_change_cb(event, req_id, changes, private_data):
            # unused
            pass

        with self.conn.start_session() as sess:
            sess.subscribe_rpc_call(
                subs_xpath, action_cb, private_data=priv, strict=True
            )
            sess.replace_config(
                {
                    "conf": {
                        "security": {
                            "alarm": [
                                {"name": "lab1"},
                                {"name": "lab2"},
                                {"name": "office1"},
                            ],
                        },
                    },
                },
                "sysrepo-example",
            )
            # Subscribe to data changes so that config is present in operational
            # datastore. This is required for action input validation.
            sess.subscribe_module_change("sysrepo-example", None, module_change_cb)

            with self.conn.start_session() as rpc_sess:
                xpath = "/sysrepo-example:conf/security/alarm[name='lab2']/trigger"
                output = rpc_sess.rpc_send(xpath, {"duration": 30})
                self.assertEqual(
                    output, {"message": "lab2 alarm triggered for 30 seconds"}
                )
                self.assertEqual(len(calls), 1)
                self.assertEqual(calls[0], (xpath, {"duration": 30}, "rpc", priv))
                del calls[:]

                # no value for duration, check default value is set
                xpath = "/sysrepo-example:conf/security/alarm[name='office1']/trigger"
                output = rpc_sess.rpc_send(xpath, {})
                self.assertEqual(
                    output, {"message": "office1 alarm triggered for 1 seconds"}
                )
                self.assertEqual(len(calls), 1)
                self.assertEqual(calls[0], (xpath, {"duration": 1}, "rpc", priv))
                del calls[:]

    def test_rpc_sub_with_extra_info(self):
        priv = object()
        calls = []
        rpc_xpath = "/sysrepo-example:poweroff"

        def rpc_cb(xpath, input_params, event, private_data, **kwargs):
            self.assertEqual(rpc_xpath, xpath)
            self.assertEqual(input_params, {"behaviour": "success"})
            self.assertEqual(event, "rpc")
            self.assertIs(private_data, priv)
            self.assertIn("user", kwargs)
            self.assertEqual(getpass.getuser(), kwargs["user"])
            self.assertIn("netconf_id", kwargs)
            self.assertEqual(kwargs["netconf_id"], 12)
            calls.append((xpath, input_params, event, private_data))
            return {"message": "bye bye"}

        with self.conn.start_session() as sess:
            sess.subscribe_rpc_call(
                rpc_xpath, rpc_cb, private_data=priv, strict=True, extra_info=True
            )

            with self.conn.start_session() as rpc_sess:
                rpc_sess.set_extra_info("netopeer2", 12, getpass.getuser())
                output = rpc_sess.rpc_send(rpc_xpath, {"behaviour": "success"})
                self.assertEqual(len(calls), 1)
                self.assertEqual(output, {"message": "bye bye"})
