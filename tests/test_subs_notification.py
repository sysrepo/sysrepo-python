# Copyright (c) 2020 6WIND S.A.
# SPDX-License-Identifier: BSD-3-Clause

import getpass
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
        cls.conn = sysrepo.SysrepoConnection()
        cls.conn.install_module(YANG_FILE, enabled_features=["turbo"])

    @classmethod
    def tearDownClass(cls):
        # we have to disconnect first to release all resources
        cls.conn.disconnect()
        with sysrepo.SysrepoConnection() as c:
            c.remove_module("sysrepo-example")

    def _test_notification_sub(
        self,
        notif_xpath: str,
        notif_dict: typing.Dict,
        request_extra_info: bool = False,
    ):
        priv = object()
        callback_called = threading.Event()

        def notif_cb(
            xpath, notification_type, notification, timestamp, private_data, **kwargs
        ):
            self.assertEqual(xpath, notif_xpath)
            self.assertEqual(notification_type, "realtime")
            self.assertEqual(notification, notif_dict)
            self.assertIsInstance(timestamp, int)
            self.assertAlmostEqual(timestamp, int(time.time()), delta=5)
            self.assertEqual(private_data, priv)
            if request_extra_info:
                self.assertIn("user", kwargs)
                self.assertEqual(getpass.getuser(), kwargs["user"])
                self.assertIn("netconf_id", kwargs)
                self.assertEqual(kwargs["netconf_id"], 12)
            else:
                self.assertEqual(0, len(kwargs))

            callback_called.set()

        with self.conn.start_session() as listening_session:
            if request_extra_info:
                kwargs = {"extra_info": True}
            else:
                kwargs = {}
            listening_session.subscribe_notification(
                "sysrepo-example", notif_xpath, notif_cb, private_data=priv, **kwargs
            )

            with self.conn.start_session() as sending_session:
                if request_extra_info:
                    sending_session.set_extra_info("netopeer2", 12, getpass.getuser())

                sending_session.notification_send(notif_xpath, notif_dict)
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

    def test_notification_sub_with_extra_info(self):
        self._test_notification_sub(
            notif_xpath="/sysrepo-example:state/state-changed",
            notif_dict={"message": "Some state changed"},
            request_extra_info=True,
        )
