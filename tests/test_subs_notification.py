# Copyright (c) 2020 6WIND S.A.
# SPDX-License-Identifier: BSD-3-Clause

import logging
import os
import threading
import time
import typing
import unittest

import sysrepo


YANG_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "examples/sysrepo-example.yang"
)
sysrepo.configure_logging(stderr_level=logging.ERROR)


class NotificationSubscriptionTest(unittest.TestCase):
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

    def _test_notification_sub(self, notif_xpath: str, notif_dict: typing.Dict):
        priv = object()
        callback_called = threading.Event()

        def notif_cb(xpath, notification_type, notification, timestamp, private_data):
            self.assertEqual(xpath, notif_xpath)
            self.assertEqual(notification_type, "realtime")
            self.assertEqual(notification, notif_dict)
            self.assertIsInstance(timestamp, int)
            self.assertAlmostEqual(timestamp, int(time.time()), delta=5)
            self.assertEqual(private_data, priv)

            callback_called.set()

        with self.conn.start_session() as sess:
            sess.subscribe_notification(
                "sysrepo-example", notif_xpath, notif_cb, private_data=priv
            )

            sess.notification_send(notif_xpath, notif_dict)
            self.assertTrue(
                callback_called.wait(timeout=1),
                "Timed-out while waiting for the notification callback to be called",
            )

    def test_notification_top_level(self):
        self._test_notification_sub(
            notif_xpath="/sysrepo-example:alarm-triggered",
            notif_dict={"description": "An error occurred", "severity": 3},
        )

    def test_notification_nested_in_data_node(self):
        self._test_notification_sub(
            notif_xpath="/sysrepo-example:state/state-changed",
            notif_dict={"message": "Some state changed"},
        )
