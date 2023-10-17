# Copyright (c) 2020 6WIND S.A.
# SPDX-License-Identifier: BSD-3-Clause

import getpass
import logging
import os
import unittest

import sysrepo


YANG_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "examples/sysrepo-example.yang"
)
sysrepo.configure_logging(stderr_level=logging.ERROR)


# ------------------------------------------------------------------------------
class OperSubscriptionTest(unittest.TestCase):
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

    def setUp(self):
        self.sess = self.conn.start_session()

    def tearDown(self):
        self.sess.stop()

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

    def test_oper_sub_with_extra_info(self):
        priv = object()
        calls = []

        def oper_data_cb(xpath, private_data, **kwargs):
            self.assertEqual(xpath, "/sysrepo-example:state")
            self.assertEqual(private_data, priv)
            self.assertIn("user", kwargs)
            self.assertEqual(getpass.getuser(), kwargs["user"])
            self.assertIn("netconf_id", kwargs)
            self.assertEqual(kwargs["netconf_id"], 12)
            calls.append((xpath, private_data, kwargs))
            return {"state": {}}

        self.sess.subscribe_oper_data_request(
            "sysrepo-example",
            "/sysrepo-example:state",
            oper_data_cb,
            private_data=priv,
            strict=True,
            extra_info=True,
        )

        with self.conn.start_session("operational") as op_sess:
            op_sess.set_extra_info("netopeer2", 12, getpass.getuser())
            oper_data = op_sess.get_data(
                "/sysrepo-example:state", keep_empty_containers=False
            )
            self.assertEqual(len(calls), 1)
            self.assertEqual(oper_data, {})
