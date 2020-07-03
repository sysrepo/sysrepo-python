# Copyright (c) 2020 6WIND S.A.
# SPDX-License-Identifier: BSD-3-Clause

import os
import unittest

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

        def rpc_cb(rpc_input, event, private_data):
            calls.append((rpc_input, event, private_data))
            behaviour = rpc_input.get("poweroff", {}).get("behaviour")
            if behaviour == "failure":
                raise sysrepo.SysrepoCallbackFailedError("poweroff failed")
            if behaviour == "bad-output":
                return {"poweroff": {"unkown-leaf": False}}
            return {"poweroff": {"message": "bye bye"}}

        with self.conn.start_session() as sess:
            sess.subscribe_rpc_call(
                "/sysrepo-example:poweroff", rpc_cb, private_data=priv, strict=True
            )

            with self.conn.start_session() as rpc_sess:
                rpc = {"poweroff": {"behaviour": "failure"}}
                with self.assertRaises(sysrepo.SysrepoCallbackFailedError):
                    rpc_sess.rpc_send(rpc, "sysrepo-example")
                self.assertEqual(len(calls), 1)
                self.assertEqual(calls[0], (rpc, "rpc", priv))
                del calls[:]

                rpc = {"poweroff": {"behaviour": "bad-output"}}
                with self.assertRaises(sysrepo.SysrepoCallbackFailedError):
                    rpc_sess.rpc_send(rpc, "sysrepo-example")
                self.assertEqual(len(calls), 1)
                self.assertEqual(calls[0], (rpc, "rpc", priv))
                del calls[:]

                rpc = {"poweroff": {"behaviour": "success"}}
                output = rpc_sess.rpc_send(rpc, "sysrepo-example")
                self.assertEqual(output, {"poweroff": {"message": "bye bye"}})
                self.assertEqual(len(calls), 1)
                self.assertEqual(calls[0], (rpc, "rpc", priv))
                del calls[:]
