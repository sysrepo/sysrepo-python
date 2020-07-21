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
        current_config = {}
        expected_changes = []

        def module_change_cb(event, req_id, changes, private_data):
            self.assertIn(event, ("change", "done", "abort"))
            self.assertIs(private_data, priv)
            for c in changes:
                if c.xpath == "/sysrepo-example:conf/system/hostname":
                    if event == "change" and c.value == "INVALID":
                        raise sysrepo.SysrepoValidationFailedError("invalid hostname")
            if event in ("change", "done"):
                self.assertEqual(changes, expected_changes)
            if event == "done":
                sysrepo.update_config_cache(current_config, changes)

        self.sess.subscribe_module_change(
            "sysrepo-example",
            "/sysrepo-example:conf",
            module_change_cb,
            private_data=priv,
        )

        with self.conn.start_session("running") as ch_sess:
            # 1.
            sent_config = {"conf": {"system": {"hostname": "bar"}}}
            expected_changes = [
                sysrepo.ChangeCreated("/sysrepo-example:conf/system/hostname", "bar")
            ]
            ch_sess.replace_config(
                sent_config, "sysrepo-example", strict=True, wait=True
            )
            self.assertEqual(current_config, sent_config)
            # 2.
            sent_config = {"conf": {"system": {"hostname": "INVALID"}}}
            expected_changes = []
            with self.assertRaises(sysrepo.SysrepoCallbackFailedError):
                ch_sess.replace_config(
                    sent_config, "sysrepo-example", strict=True, wait=True
                )
            # 3.
            sent_config = {
                "conf": {
                    "system": {"hostname": "bar"},
                    "network": {"interface": [{"name": "eth0", "up": True}]},
                }
            }
            expected_changes = [
                sysrepo.ChangeCreated(
                    "/sysrepo-example:conf/network/interface[name='eth0']",
                    {"name": "eth0", "up": True},
                    after="",
                ),
                sysrepo.ChangeCreated(
                    "/sysrepo-example:conf/network/interface[name='eth0']/name", "eth0"
                ),
                sysrepo.ChangeCreated(
                    "/sysrepo-example:conf/network/interface[name='eth0']/up", True
                ),
            ]
            ch_sess.replace_config(
                sent_config, "sysrepo-example", strict=True, wait=True
            )
            self.assertEqual(current_config, sent_config)
            # 4.
            sent_config = {
                "conf": {
                    "system": {"hostname": "bar"},
                    "network": {"interface": [{"name": "eth2", "up": False}]},
                }
            }
            expected_changes = [
                sysrepo.ChangeDeleted(
                    "/sysrepo-example:conf/network/interface[name='eth0']"
                ),
                sysrepo.ChangeDeleted(
                    "/sysrepo-example:conf/network/interface[name='eth0']/name"
                ),
                sysrepo.ChangeDeleted(
                    "/sysrepo-example:conf/network/interface[name='eth0']/up"
                ),
                sysrepo.ChangeCreated(
                    "/sysrepo-example:conf/network/interface[name='eth2']",
                    {"name": "eth2", "up": False},
                    after="",
                ),
                sysrepo.ChangeCreated(
                    "/sysrepo-example:conf/network/interface[name='eth2']/name", "eth2"
                ),
                sysrepo.ChangeCreated(
                    "/sysrepo-example:conf/network/interface[name='eth2']/up", False
                ),
            ]
            ch_sess.replace_config(
                sent_config, "sysrepo-example", strict=True, wait=True
            )
            self.assertEqual(current_config, sent_config)
            # 5.
            sent_config = {
                "conf": {
                    "system": {"hostname": "bar"},
                    "network": {"interface": [{"name": "eth2", "up": True}]},
                }
            }
            expected_changes = [
                sysrepo.ChangeModified(
                    "/sysrepo-example:conf/network/interface[name='eth2']/up",
                    True,
                    "false",
                    False,
                ),
            ]
            ch_sess.replace_config(
                sent_config, "sysrepo-example", strict=True, wait=True
            )
            self.assertEqual(current_config, sent_config)
            # 6.
            sent_config = {
                "conf": {
                    "system": {"hostname": "bar"},
                    "network": {
                        "interface": [
                            {"name": "eth2", "up": True},
                            {"name": "eth0", "up": False},
                        ]
                    },
                }
            }
            expected_changes = [
                sysrepo.ChangeCreated(
                    "/sysrepo-example:conf/network/interface[name='eth0']",
                    {"name": "eth0", "up": False},
                    after="[name='eth2']",
                ),
                sysrepo.ChangeCreated(
                    "/sysrepo-example:conf/network/interface[name='eth0']/name", "eth0"
                ),
                sysrepo.ChangeCreated(
                    "/sysrepo-example:conf/network/interface[name='eth0']/up", False
                ),
            ]
            ch_sess.replace_config(
                sent_config, "sysrepo-example", strict=True, wait=True
            )
            self.assertEqual(current_config, sent_config)
            # 7.
            sent_config = {
                "conf": {
                    "system": {"hostname": "bar"},
                    "network": {
                        "interface": [
                            {"name": "eth0", "up": False},
                            {"name": "eth2", "up": True},
                        ]
                    },
                }
            }
            expected_changes = [
                sysrepo.ChangeMoved(
                    "/sysrepo-example:conf/network/interface[name='eth2']",
                    after="[name='eth0']",
                ),
            ]
            ch_sess.replace_config(
                sent_config, "sysrepo-example", strict=True, wait=True
            )
            self.assertEqual(current_config, sent_config)
