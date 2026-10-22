# Copyright (c) 2020 6WIND S.A.
# SPDX-License-Identifier: BSD-3-Clause

import grp
import logging
import os
import pwd
import unittest

import libyang

import sysrepo


YANG_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "examples/sysrepo-example.yang"
)
sysrepo.configure_logging(stderr_level=logging.ERROR)


# ------------------------------------------------------------------------------
class ConnectionTest(unittest.TestCase):
    def test_yang_module_dir(self):
        original = sysrepo.yang_module_dir()
        self.assertIsInstance(original, str)
        self.assertTrue(original)
        try:
            sysrepo.set_yang_module_dir(None)
            default = sysrepo.yang_module_dir()
            self.assertIsInstance(default, str)
            self.assertTrue(default)

            path = "/tmp/sysrepo-\u00e9/modules"
            sysrepo.set_yang_module_dir(path)
            self.assertEqual(sysrepo.yang_module_dir(), path)

            sysrepo.set_yang_module_dir(None)
            self.assertEqual(sysrepo.yang_module_dir(), default)
        finally:
            sysrepo.set_yang_module_dir(original)

    def test_ly_yang_module_dir(self):
        original = sysrepo.ly_yang_module_dir()
        self.assertIsInstance(original, str)
        self.assertTrue(original)
        try:
            sysrepo.set_ly_yang_module_dir(None)
            default = sysrepo.ly_yang_module_dir()
            self.assertIsInstance(default, str)
            self.assertTrue(default)

            path = "/tmp/libyang-\u00e9/modules"
            sysrepo.set_ly_yang_module_dir(path)
            self.assertEqual(sysrepo.ly_yang_module_dir(), path)

            sysrepo.set_ly_yang_module_dir(None)
            self.assertEqual(sysrepo.ly_yang_module_dir(), default)
        finally:
            sysrepo.set_ly_yang_module_dir(original)

    def test_conn_connect(self):
        conn = sysrepo.SysrepoConnection()
        conn.disconnect()

    def test_conn_connect_ctxmgr(self):
        with sysrepo.SysrepoConnection():
            pass

    def test_conn_start_session(self):
        with sysrepo.SysrepoConnection() as conn:
            sess = conn.start_session()
            self.assertEqual(sess.get_datastore(), "running")
            sess.stop()

    def test_conn_start_session_ctxmgr(self):
        with sysrepo.SysrepoConnection() as conn:
            with conn.start_session() as sess:
                self.assertEqual(sess.get_datastore(), "running")

    def test_conn_start_session_operational(self):
        with sysrepo.SysrepoConnection() as conn:
            with conn.start_session("operational") as sess:
                self.assertEqual(sess.get_datastore(), "operational")

    def test_conn_install_remove_modules(self):
        YANG_FILE2 = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "examples/sysrepo-example2.yang"
        )
        with sysrepo.SysrepoConnection() as conn:
            filepaths = {YANG_FILE: ["turbo"], YANG_FILE2: ["turbo2"]}
            # filepaths = {YANG_FILE2: ["turbo2"]}
            conn.install_modules(filepaths)

        with sysrepo.SysrepoConnection() as conn:
            modules = ["sysrepo-example", "sysrepo-example2"]
            conn.remove_modules(modules)

    def test_conn_install_remove_module(self):
        with sysrepo.SysrepoConnection() as conn:
            conn.install_module(YANG_FILE, enabled_features=["turbo"])
        with sysrepo.SysrepoConnection() as conn:
            conn.remove_module("sysrepo-example")
        with sysrepo.SysrepoConnection() as conn:
            with conn.get_ly_ctx() as ctx:
                with self.assertRaises(libyang.LibyangError):
                    ctx.get_module("sysrepo-example")

    def test_conn_enable_module_feature(self):
        with sysrepo.SysrepoConnection() as conn:
            conn.install_module(YANG_FILE)
            conn.enable_module_feature("sysrepo-example", "turbo")
            with conn.start_session("operational") as sess:
                data = sess.get_data("/ietf-yang-library:*")
                data = data["yang-library"]["module-set"]
                data = next(iter(data))
                data = data["module"]
                data = [x for x in data if x["name"] == "sysrepo-example"][0]
                self.assertIn("feature", data)
            conn.remove_module("sysrepo-example")

    def test_conn_get_module_infos(self):
        with sysrepo.SysrepoConnection() as conn:
            conn.install_module(YANG_FILE)
            owner, group, perm = conn.get_module_ds_access("sysrepo-example")
            self.assertEqual(pwd.getpwnam(owner).pw_uid, os.geteuid())
            self.assertEqual(grp.getgrnam(group).gr_gid, os.getegid())
            self.assertEqual(perm, 0o600)

    def test_conn_start_session_with_printed_context(self):
        with sysrepo.SysrepoConnection(not_printed=False) as conn:
            sess = conn.start_session()
            self.assertEqual(sess.get_datastore(), "running")
            sess.stop()
