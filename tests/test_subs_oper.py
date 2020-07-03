# Copyright (c) 2020 6WIND S.A.
# SPDX-License-Identifier: BSD-3-Clause

import os
import unittest

import sysrepo


YANG_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "examples/sysrepo-example.yang"
)


# ------------------------------------------------------------------------------
class OperSubscriptionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with sysrepo.SysrepoConnection() as conn:
            conn.install_module(YANG_FILE, enabled_features=["turbo"])
        cls.conn = sysrepo.SysrepoConnection(err_on_sched_fail=True)
        cls.sess = cls.conn.start_session()

    @classmethod
    def tearDownClass(cls):
        cls.sess.stop()
        cls.conn.remove_module("sysrepo-example")
        cls.conn.disconnect()
        # reconnect to make sure module is removed
        with sysrepo.SysrepoConnection(err_on_sched_fail=True):
            pass

    def test_oper_sub(self):
        priv = object()
        state = None

        def oper_data_cb(xpath, private_data):
            self.assertEqual(xpath, "/sysrepo-example:state")
            self.assertEqual(private_data, priv)
            return state

        self.sess.subscribe_oper_data_request(
            "sysrepo-example",
            "/sysrepo-example:state",
            oper_data_cb,
            private_data=priv,
            strict=True,
        )

        with self.conn.start_session("operational") as op_sess:
            state = {}
            self.assertEqual(op_sess.get_data("/sysrepo-example:state"), state)
            state = {
                "state": {
                    "system": {"hostname": "foo"},
                    "network": {
                        "interface": [
                            {
                                "name": "eth0",
                                "address": "1.2.3.4/24",
                                "up": True,
                                "stats": {"rx": 42, "tx": 42},
                            }
                        ]
                    },
                }
            }
            self.assertEqual(op_sess.get_data("/sysrepo-example:state"), state)
            state = {"state": {"invalid": True}}
            with self.assertRaises(sysrepo.SysrepoCallbackFailedError):
                op_sess.get_data("/sysrepo-example:state")
