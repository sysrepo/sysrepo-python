# Copyright (c) 2026 6WIND S.A.
# SPDX-License-Identifier: BSD-3-Clause

import unittest

from sysrepo.change import ChangeCreated, ChangeDeleted, update_config_cache


class UpdateConfigCacheTest(unittest.TestCase):
    def test_created_after_missing_entry(self):
        """
        When a ChangeCreated references an 'after' entry that was deleted by a
        previous ChangeDeleted in the same batch, the entry should still be
        created (appended at the end) instead of raising ValueError.
        """
        conf = {
            "coredump": [
                {"name": "core.A"},
                {"name": "core.B"},
            ],
        }
        changes = [
            ChangeDeleted("/coredump[name='core.A']", {"name": "core.A"}),
            ChangeCreated(
                "/coredump[name='core.C']",
                {"name": "core.C"},
                after="[name='core.A']",
            ),
        ]
        update_config_cache(conf, changes)
        # core.A deleted, core.C added (appended since 'after' ref is gone)
        self.assertEqual(
            conf["coredump"],
            [{"name": "core.B"}, {"name": "core.C"}],
        )

    def test_created_after_existing_entry(self):
        """Normal case: 'after' entry exists, insertion at correct position."""
        conf = {
            "coredump": [
                {"name": "core.A"},
                {"name": "core.B"},
            ],
        }
        changes = [
            ChangeCreated(
                "/coredump[name='core.C']",
                {"name": "core.C"},
                after="[name='core.A']",
            ),
        ]
        update_config_cache(conf, changes)
        self.assertEqual(
            conf["coredump"],
            [{"name": "core.A"}, {"name": "core.C"}, {"name": "core.B"}],
        )
