# Copyright (c) 2020 6WIND S.A.
# SPDX-License-Identifier: BSD-3-Clause

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
class ConnectionTest(unittest.TestCase):
    def test_conn_connect(self):
        conn = sysrepo.SysrepoConnection()
        conn.disconnect()

    def test_conn_connect_ctxmgr(self):
        with sysrepo.SysrepoConnection():
            pass

    def test_conn_start_session(self):
        with sysrepo.SysrepoConnection(no_sched_changes=True) as conn:
            sess = conn.start_session()
            self.assertEqual(sess.get_datastore(), "running")
            sess.stop()

    def test_conn_start_session_ctxmgr(self):
        with sysrepo.SysrepoConnection(err_on_sched_fail=True) as conn:
            with conn.start_session() as sess:
                self.assertEqual(sess.get_datastore(), "running")

    def test_conn_start_session_operational(self):
        with sysrepo.SysrepoConnection() as conn:
            with conn.start_session("operational") as sess:
                self.assertEqual(sess.get_datastore(), "operational")

    def test_conn_install_module(self):
        with sysrepo.SysrepoConnection() as conn:
            conn.install_module(YANG_FILE, enabled_features=["turbo"])
        # reconnect to make sure it is installed
        with sysrepo.SysrepoConnection(err_on_sched_fail=True) as conn:
            ctx = conn.get_ly_ctx()
            mod = ctx.get_module("sysrepo-example")
            self.assertTrue(mod.implemented())
            self.assertTrue(mod.feature_state("turbo"))

    def test_conn_remove_module(self):
        with sysrepo.SysrepoConnection() as conn:
            conn.remove_module("sysrepo-example")
        # reconnect to make sure it is removed
        with sysrepo.SysrepoConnection(err_on_sched_fail=True) as conn:
            ctx = conn.get_ly_ctx()
            with self.assertRaises(libyang.LibyangError):
                ctx.get_module("sysrepo-example")
