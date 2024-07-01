# Copyright (c) 2020 6WIND S.A.
# SPDX-License-Identifier: BSD-3-Clause

import logging
import os
import threading
import time
import types
import unittest
from unittest.mock import ANY

import sysrepo


YANG_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "examples/sysrepo-example.yang"
)
sysrepo.configure_logging(stderr_level=logging.ERROR)


# ------------------------------------------------------------------------------
class SessionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conn = sysrepo.SysrepoConnection()
        cls.conn.install_module(YANG_FILE, enabled_features=["turbo"])

    @classmethod
    def tearDownClass(cls):
        cls.conn.remove_module("sysrepo-example")
        cls.conn.disconnect()

    def test_session_switch_ds(self):
        with self.conn.start_session("running") as sess:
            self.assertEqual(sess.get_datastore(), "running")
            sess.switch_datastore("startup")
            self.assertEqual(sess.get_datastore(), "startup")
            sess.switch_datastore("operational")
            self.assertEqual(sess.get_datastore(), "operational")

    def test_session_bad_datastore(self):
        with self.assertRaises(ValueError):
            self.conn.start_session("invalid")

    def test_session_get_ly_ctx(self):
        with self.conn.start_session() as sess:
            with sess.get_ly_ctx() as ctx:
                mod = ctx.get_module("sysrepo-example")
            self.assertTrue(mod.implemented)

    def test_session_get_data(self):
        with self.conn.start_session("operational") as sess:
            data = sess.get_data("/ietf-yang-library:*")
            self.assertIn("yang-library", data)
            data = data["yang-library"]
            self.assertIn("module-set", data)
            data = data["module-set"]
            self.assertIsInstance(data, list)
            data = next(iter(data))
            self.assertIn("module", data)
            data = data["module"]
            self.assertIsInstance(data, list)
            modinfo = {
                "name": "sysrepo-example",
                "namespace": "n",
                "feature": ["turbo"],
                "location": ANY,
            }
            self.assertIn(modinfo, data)

    MOD_XPATH = "/ietf-yang-library:yang-library/module-set/module[name=%r]/name"
    MODS_XPATH = "/ietf-yang-library:yang-library/module-set/module/name"

    def test_session_get_item_not_found(self):
        with self.conn.start_session("operational") as sess:
            with self.assertRaises(sysrepo.SysrepoNotFoundError):
                sess.get_item(self.MOD_XPATH % "not-installed")

    def test_session_get_item(self):
        with self.conn.start_session("operational") as sess:
            value = sess.get_item(self.MOD_XPATH % "sysrepo-example")
            self.assertIsInstance(value, sysrepo.String)
            self.assertIsInstance(value.value, str)
            self.assertEqual(value.value, "sysrepo-example")

    def test_session_get_items(self):
        with self.conn.start_session("operational") as sess:
            values = sess.get_items(self.MODS_XPATH)
            self.assertIsInstance(values, types.GeneratorType)
            values = list(values)
            self.assertGreater(len(values), 0)

    def test_session_replace_config(self):
        with self.conn.start_session("running") as sess:
            config = {"conf": {"system": {"hostname": "foobar"}}}
            sess.replace_config(config, "sysrepo-example")

    def test_session_copy_config(self):
        with self.conn.start_session("candidate") as sess:
            config = {"conf": {"system": {"hostname": "foobar"}}}
            sess.replace_config(config, "sysrepo-example")
        with self.conn.start_session("running") as sess:
            sess.copy_config("candidate", module_name="sysrepo-example")
            data = sess.get_data("/sysrepo-example:conf")
            self.assertEqual(data, {"conf": {"system": {"hostname": "foobar"}}})

    def test_session_copy_config_errors(self):
        with self.conn.start_session("candidate") as sess:
            config = {"conf": {"system": {"hostname": "foobar"}}}
            sess.replace_config(config, "sysrepo-example")
        with self.conn.start_session("running") as sess:
            with self.assertRaises(ValueError):
                sess.copy_config("invalid")
        with self.conn.start_session("running") as sess:
            with self.assertRaises(sysrepo.SysrepoNotFoundError):
                sess.copy_config("candidate", module_name="not-found")

    def test_session_set_item(self):
        def iface(name, field):
            return "/sysrepo-example:conf/network/interface[name=%r]/%s" % (name, field)

        def assert_data():
            with self.conn.start_session("running") as new_sess:
                data = new_sess.get_data("/sysrepo-example:conf")
                self.assertEqual(
                    data,
                    {
                        "conf": {
                            "network": {
                                "interface": [
                                    {
                                        "name": "eth0",
                                        "address": "1.2.3.4/24",
                                        "up": True,
                                    },
                                    {
                                        "name": "eth1",
                                        "address": "4.3.2.1/24",
                                        "up": False,
                                    },
                                ]
                            }
                        }
                    },
                )

        with self.conn.start_session("running") as sess:
            sess.replace_config({}, "sysrepo-example")
            sess.set_item(iface("eth0", "address"), "1.2.3.4/24")
            sess.set_item(iface("eth0", "up"), True)
            sess.set_item(iface("eth1", "address"), "4.3.2.1/24")
            sess.set_item(iface("eth1", "up"), False)
            sess.apply_changes()
            sess.set_item(iface("eth2", "address"), "8.8.8.8/24")
            sess.set_item(iface("eth2", "up"), True)
            sess.validate()
            assert_data()
            sess.discard_changes()

        assert_data()

    def test_get_netconf_id_and_get_user_are_only_available_in_implicit_session(self):
        with self.conn.start_session("running") as sess:
            with self.assertRaises(sysrepo.SysrepoUnsupportedError):
                sess.get_netconf_id()

            with self.assertRaises(sysrepo.SysrepoUnsupportedError):
                sess.get_user()

    def test_basic_session_lock(self):
        # lock whole datastore
        with self.conn.start_session("running") as sess:
            with sess.locked():
                config = {"conf": {"system": {"hostname": "foobar1"}}}
                sess.replace_config(config, "sysrepo-example")
                sess.apply_changes()

        # lock specific module name with a timeout
        with self.conn.start_session("running") as sess:
            with sess.locked("sysrepo-example", 1000):
                config = {"conf": {"system": {"hostname": "foobar2"}}}
                sess.replace_config(config, "sysrepo-example")
                sess.apply_changes()

    def test_concurrent_session_lock(self):
        def function_thread_one():
            with self.conn.start_session("running") as sess:
                with sess.locked():
                    config = {"conf": {"system": {"hostname": "foobar1"}}}
                    sess.replace_config(config, "sysrepo-example")
                    sess.apply_changes()
                    time.sleep(3)  # keep the lock active

        def function_thread_two():
            time.sleep(1)
            with self.conn.start_session("running") as sess:
                with self.assertRaises(sysrepo.SysrepoLockedError):
                    with sess.locked():
                        pass

        thread_one = threading.Thread(target=function_thread_one)
        thread_two = threading.Thread(target=function_thread_two)

        thread_one.start()
        thread_two.start()

        thread_one.join()
        thread_two.join()
