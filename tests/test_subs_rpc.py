# Copyright (c) 2020 6WIND S.A.
# SPDX-License-Identifier: BSD-3-Clause

import copy
import os
import unittest

import libyang

import sysrepo


YANG_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "examples/sysrepo-example.yang"
)


# ------------------------------------------------------------------------------
class RpcSubscriptionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with sysrepo.SysrepoConnection() as conn:
            conn.install_module(YANG_FILE, enabled_features=["turbo"])
        cls.conn = sysrepo.SysrepoConnection(err_on_sched_fail=True)

    @classmethod
    def tearDownClass(cls):
        cls.conn.remove_module("sysrepo-example")
        cls.conn.disconnect()
        # reconnect to make sure module is removed
        with sysrepo.SysrepoConnection(err_on_sched_fail=True):
            pass

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
                rpc = {"poweroff": {"behaviour": "failure"}}
                with self.assertRaises(sysrepo.SysrepoCallbackFailedError):
                    rpc_sess.rpc_send(rpc, "sysrepo-example")
                self.assertEqual(len(calls), 1)
                self.assertEqual(calls[0], (rpc_xpath, rpc["poweroff"], "rpc", priv))
                del calls[:]

                rpc = {"poweroff": {"behaviour": "bad-output"}}
                with self.assertRaises(sysrepo.SysrepoCallbackFailedError):
                    rpc_sess.rpc_send(rpc, "sysrepo-example")
                self.assertEqual(len(calls), 1)
                self.assertEqual(calls[0], (rpc_xpath, rpc["poweroff"], "rpc", priv))
                del calls[:]

                rpc = {"poweroff": {"behaviour": "success"}}
                output = rpc_sess.rpc_send(rpc, "sysrepo-example")
                self.assertEqual(output, {"poweroff": {"message": "bye bye"}})
                self.assertEqual(len(calls), 1)
                self.assertEqual(calls[0], (rpc_xpath, rpc["poweroff"], "rpc", priv))
                del calls[:]

    def test_action_sub(self):
        priv = object()
        calls = []
        subs_xpath = "/sysrepo-example:conf/security/alarm/trigger"

        def action_cb(xpath, input_params, event, private_data):
            calls.append((xpath, input_params, event, private_data))
            duration = input_params["duration"]
            return {"message": "triggered for %r seconds" % (duration,)}

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
                action = {
                    "conf": {
                        "security": {
                            "alarm": [{"name": "lab2", "trigger": {"duration": 30}}],
                        },
                    },
                }
                output = rpc_sess.rpc_send(action, "sysrepo-example")
                call_xpath = "/sysrepo-example:conf/security/alarm[name='lab2']/trigger"
                expected_output = copy.deepcopy(action)
                libyang.xpath_set(
                    expected_output, call_xpath, {"message": "triggered for 30 seconds"}
                )
                self.assertEqual(output, expected_output)
                self.assertEqual(len(calls), 1)
                self.assertEqual(calls[0], (call_xpath, {"duration": 30}, "rpc", priv))
                del calls[:]

                # no value for duration, check default value is set
                libyang.xpath_set(action, call_xpath, {})
                output = rpc_sess.rpc_send(action, "sysrepo-example")
                libyang.xpath_set(
                    expected_output, call_xpath, {"message": "triggered for 1 seconds"}
                )
                self.assertEqual(len(calls), 1)
                self.assertEqual(calls[0], (call_xpath, {"duration": 1}, "rpc", priv))
                del calls[:]
