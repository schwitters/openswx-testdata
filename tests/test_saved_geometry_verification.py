# SPDX-License-Identifier: MIT
# Copyright (c) 2026 openswx contributors
"""Frozen native saved-state identity evidence, independent of CLI heuristics."""
import hashlib
import json
from pathlib import Path
import unittest

DATA = Path(__file__).resolve().parents[1] / "verification/saved-geometry-001"


class SavedGeometryEvidenceTest(unittest.TestCase):
    def test_original_synthetic_artifacts_have_reviewed_hashes(self):
        manifest = json.loads((DATA / "manifest.json").read_text())
        self.assertEqual(manifest["origin"], "original_synthetic")
        self.assertEqual(manifest["license"], "MIT")
        self.assertEqual(manifest["command_schema"], "1.12")
        for artifact in manifest["artifacts"]:
            raw = (DATA / artifact["path"]).read_bytes()
            self.assertEqual(len(raw), artifact["bytes"])
            self.assertEqual(hashlib.sha256(raw).hexdigest(), artifact["sha256"])

    def test_configuration_body_counts_and_reopened_active_state_are_native(self):
        expected = json.loads((DATA / "expected.json").read_text())
        self.assertEqual(len(expected["snapshots"]), 4)
        for snapshot in expected["snapshots"]:
            reopened = snapshot["reopened_native_measurement"]
            self.assertEqual(reopened["configuration"], snapshot["active_configuration"])
            for configuration in snapshot["configurations"]:
                if "native_measurement" not in configuration:
                    continue
                native = configuration["native_measurement"]
                self.assertEqual(native["configuration"], configuration["name"])
                self.assertEqual(native["topology_counts"]["bodies"], configuration["native_solid_body_count"])
                self.assertTrue(all(b["body_kind"] == "solid" for b in native["body_measurements"]))
        capture = json.loads((DATA / "capture.json").read_text())
        self.assertTrue(capture["documents_closed"])
        self.assertFalse(capture["authentication_headers_recorded"])
        update = next(e for e in capture["events"] if e["label"] == "suppress-default-second")
        params = update["request"]["params"]["arguments"]["params"]
        self.assertEqual(params["configuration"], "Default")
        self.assertEqual(params["features"], [{"feature": {"ref": "feature:second"}, "suppressed": True}])

    def test_native_sheet_is_not_in_the_selected_partition_baseline(self):
        expected = json.loads((DATA / "expected.json").read_text())
        sheet = next(s for s in expected["snapshots"] if s["file"] == "sheet.sldprt")
        configuration = sheet["configurations"][0]
        bodies = [e for e in configuration["native_brep"]["entities"] if e["kind"] == "body"]
        self.assertEqual([b["body_kind"] for b in bodies], ["sheet"])
        inspection = json.loads((DATA / "sheet-base-inspection.json").read_text())
        self.assertTrue(inspection["complete"])
        self.assertEqual(inspection["model"]["node_type_counts"], {"101": 1})
        self.assertEqual(configuration["expected_candidate_kinds"], [])
        self.assertEqual(expected["expected_state_status"], "unsupported")
        self.assertEqual(expected["expected_body_membership_status"], "unresolved")
