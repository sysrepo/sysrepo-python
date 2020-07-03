# Copyright (c) 2020 6WIND S.A.
# SPDX-License-Identifier: BSD-3-Clause

import os
import unittest

import sysrepo


YANG_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "examples/sysrepo-example.yang"
)


# ------------------------------------------------------------------------------
class ModuleChangeSubscriptionTest(unittest.TestCase):
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

    def test_module_change_sub(self):
        priv = object()
        sent_config = None
        applied_config = None

        def module_change_cb(event, req_id, config, changes, private_data):
            nonlocal applied_config
            self.assertIn(event, ("change", "done", "abort"))
            self.assertEqual(config, sent_config)
            self.assertIs(private_data, priv)
            if event in ("change", "done"):
                self.assertGreater(len(changes), 0)
            hostname = config.get("conf", {}).get("system", {}).get("hostname")
            if event == "change" and hostname == "INVALID":
                raise sysrepo.SysrepoValidationFailedError("invalid hostname")
            if event == "done":
                applied_config = config

        self.sess.subscribe_module_change(
            "sysrepo-example",
            "/sysrepo-example:conf",
            module_change_cb,
            private_data=priv,
        )

        with self.conn.start_session("running") as ch_sess:
            sent_config = {"conf": {"system": {"hostname": "bar"}}}
            ch_sess.replace_config(
                sent_config, "sysrepo-example", strict=True, wait=True
            )
            self.assertEqual(applied_config, sent_config)
            sent_config = {"conf": {"system": {"hostname": "INVALID"}}}
            with self.assertRaises(sysrepo.SysrepoCallbackFailedError):
                ch_sess.replace_config(
                    sent_config, "sysrepo-example", strict=True, wait=True
                )
            self.assertNotEqual(applied_config, sent_config)
