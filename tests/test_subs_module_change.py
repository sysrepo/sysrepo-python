# Copyright (c) 2020 6WIND S.A.
# SPDX-License-Identifier: BSD-3-Clause

import getpass
import logging
import os
import unittest

import sysrepo
from sysrepo.session import SysrepoSession


YANG_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "examples/sysrepo-example.yang"
)
sysrepo.configure_logging(stderr_level=logging.ERROR)


# ------------------------------------------------------------------------------
class ModuleChangeSubscriptionTest(unittest.TestCase):
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
        with self.conn.start_session("running") as sess:
            sess.delete_item("/sysrepo-example:conf")
            sess.apply_changes()
        self.sess = self.conn.start_session()

    def tearDown(self):
        self.sess.stop()

    def test_module_change_sub(self):
        priv = object()
        current_config = {}
        expected_changes = []

        def module_change_cb(event, req_id, changes, private_data):
            self.assertIn(event, ("change", "done", "abort", "update"))
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
            update=True,
        )

        with self.conn.start_session("running") as ch_sess:
            # 1.
            sent_config = {"conf": {"system": {"hostname": "bar"}}}
            expected_changes = [
                sysrepo.ChangeCreated("/sysrepo-example:conf/system/hostname", "bar")
            ]
            ch_sess.replace_config(sent_config, "sysrepo-example", strict=True)
            self.assertEqual(current_config, sent_config)
            # 2.
            sent_config = {"conf": {"system": {"hostname": "INVALID"}}}
            expected_changes = []
            with self.assertRaises(sysrepo.SysrepoValidationFailedError):
                ch_sess.replace_config(sent_config, "sysrepo-example", strict=True)
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
            ch_sess.replace_config(sent_config, "sysrepo-example", strict=True)
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
                    "/sysrepo-example:conf/network/interface[name='eth0']",
                    None,
                ),
                sysrepo.ChangeDeleted(
                    "/sysrepo-example:conf/network/interface[name='eth0']/name",
                    None,
                ),
                sysrepo.ChangeDeleted(
                    "/sysrepo-example:conf/network/interface[name='eth0']/up",
                    None,
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
            ch_sess.replace_config(sent_config, "sysrepo-example", strict=True)
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
            ch_sess.replace_config(sent_config, "sysrepo-example", strict=True)
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
            ch_sess.replace_config(sent_config, "sysrepo-example", strict=True)
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
                    "/sysrepo-example:conf/network/interface[name='eth0']", after=""
                ),
            ]
            ch_sess.replace_config(sent_config, "sysrepo-example", strict=True)
            self.assertEqual(current_config, sent_config)

    def test_module_change_sub_with_deleted_values(self):
        priv = object()
        current_config = {}
        expected_changes = []

        def module_change_cb(event, req_id, changes, private_data):
            self.assertIn(event, ("change", "done", "abort"))
            self.assertIs(private_data, priv)
            if event in ("change", "done"):
                self.assertEqual(changes, expected_changes)
            if event == "done":
                sysrepo.update_config_cache(current_config, changes)

        self.sess.subscribe_module_change(
            "sysrepo-example",
            "/sysrepo-example:conf",
            module_change_cb,
            private_data=priv,
            include_deleted_values=True,
        )

        with self.conn.start_session("running") as ch_sess:
            # 1.
            sent_config = {
                "conf": {
                    "system": {"hostname": "bar"},
                    "network": {"interface": [{"name": "eth0", "up": True}]},
                }
            }
            expected_changes = [
                sysrepo.ChangeCreated("/sysrepo-example:conf/system/hostname", "bar"),
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
            ch_sess.replace_config(sent_config, "sysrepo-example", strict=True)
            self.assertEqual(current_config, sent_config)
            # 2.
            sent_config = {
                "conf": {
                    "system": {"hostname": "bar"},
                    "network": {"interface": [{"name": "eth2", "up": False}]},
                }
            }
            expected_changes = [
                sysrepo.ChangeDeleted(
                    "/sysrepo-example:conf/network/interface[name='eth0']",
                    {"name": "eth0", "up": True},
                ),
                sysrepo.ChangeDeleted(
                    "/sysrepo-example:conf/network/interface[name='eth0']/name",
                    "eth0",
                ),
                sysrepo.ChangeDeleted(
                    "/sysrepo-example:conf/network/interface[name='eth0']/up",
                    True,
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
            ch_sess.replace_config(sent_config, "sysrepo-example", strict=True)
            self.assertEqual(current_config, sent_config)

    def test_module_change_sub_with_extra_info(self):
        priv = object()
        calls = []

        def module_change_cb(event, req_id, changes, private_data, **kwargs):
            self.assertIn(event, ("change", "done", "abort"))
            self.assertIsInstance(req_id, int)
            self.assertIsInstance(changes, list)
            self.assertIs(private_data, priv)
            self.assertIn("user", kwargs)
            self.assertEqual(getpass.getuser(), kwargs["user"])
            self.assertIn("netconf_id", kwargs)
            self.assertEqual(12, kwargs["netconf_id"])
            calls.append((event, req_id, changes, private_data, kwargs))

        self.sess.subscribe_module_change(
            "sysrepo-example",
            "/sysrepo-example:conf",
            module_change_cb,
            private_data=priv,
            extra_info=True,
        )

        with self.conn.start_session("running") as ch_sess:
            ch_sess.set_extra_info("netopeer2", 12, getpass.getuser())

            sent_config = {"conf": {"system": {"hostname": "bar"}}}
            ch_sess.replace_config(sent_config, "sysrepo-example", strict=True)
            # Successful change callbacks are called twice:
            #   * once with event "change"
            #   * once with event "done"
            self.assertEqual(2, len(calls))

    def test_module_change_sub_unsafe(self):
        priv = object()
        current_config = {}
        expected_changes = []

        def module_change_cb(session, event, req_id, private_data):
            self.assertIsInstance(session, SysrepoSession)
            self.assertIn(event, ("change", "done", "abort", "update"))
            self.assertIsInstance(req_id, int)
            self.assertIs(private_data, priv)
            changes = list(session.get_changes("/sysrepo-example:conf//."))
            for c in changes:
                if c.xpath == "/sysrepo-example:conf/system/hostname":
                    if event == "change" and c.value == "INVALID":
                        raise sysrepo.SysrepoValidationFailedError("invalid hostname")
            if event in ("change", "done"):
                self.assertEqual(changes, expected_changes)
            if event == "done":
                sysrepo.update_config_cache(current_config, changes)

        self.sess.subscribe_module_change_unsafe(
            "sysrepo-example",
            "/sysrepo-example:conf",
            module_change_cb,
            private_data=priv,
            update=True,
        )

        with self.conn.start_session("running") as ch_sess:
            # 1.
            sent_config = {"conf": {"system": {"hostname": "bar"}}}
            expected_changes = [
                sysrepo.ChangeCreated("/sysrepo-example:conf/system/hostname", "bar")
            ]
            ch_sess.replace_config(sent_config, "sysrepo-example", strict=True)
            self.assertEqual(current_config, sent_config)
            # 2.
            sent_config = {"conf": {"system": {"hostname": "INVALID"}}}
            expected_changes = []
            with self.assertRaises(sysrepo.SysrepoValidationFailedError):
                ch_sess.replace_config(sent_config, "sysrepo-example", strict=True)
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
            ch_sess.replace_config(sent_config, "sysrepo-example", strict=True)
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
                    "/sysrepo-example:conf/network/interface[name='eth0']",
                    None,
                ),
                sysrepo.ChangeDeleted(
                    "/sysrepo-example:conf/network/interface[name='eth0']/name",
                    None,
                ),
                sysrepo.ChangeDeleted(
                    "/sysrepo-example:conf/network/interface[name='eth0']/up",
                    None,
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
            ch_sess.replace_config(sent_config, "sysrepo-example", strict=True)
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
            ch_sess.replace_config(sent_config, "sysrepo-example", strict=True)
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
            ch_sess.replace_config(sent_config, "sysrepo-example", strict=True)
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
                    "/sysrepo-example:conf/network/interface[name='eth0']", after=""
                ),
            ]
            ch_sess.replace_config(sent_config, "sysrepo-example", strict=True)
            self.assertEqual(current_config, sent_config)
