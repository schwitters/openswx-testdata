# SPDX-License-Identifier: MIT
# Copyright (c) 2026 openswx contributors
"""Native saved-state regression, built without any imported private CAD."""
import hashlib
import json
from pathlib import Path
import unittest

DATA = Path(__file__).resolve().parents[1] / "verification/saved-state-002"


class SavedStateEvidenceTest(unittest.TestCase):
    def test_artifacts_are_original_synthetic_and_hash_verified(self):
        manifest = json.loads((DATA / "manifest.json").read_text())
        self.assertEqual(manifest["origin"], "original_synthetic")
        self.assertEqual(manifest["license"], "MIT")
        for artifact in manifest["artifacts"]:
            path = DATA / artifact["path"]
            self.assertEqual(path.parent, DATA)
            data = path.read_bytes()
            self.assertEqual(len(data), artifact["bytes"])
            self.assertEqual(hashlib.sha256(data).hexdigest(), artifact["sha256"])

    def test_reopened_native_sets_remain_independent_of_kernel_identifiers(self):
        expected = json.loads((DATA / "expected.json").read_text())
        snapshots = {s["file"]: s for s in expected["snapshots"]}
        self.assertEqual(len(snapshots), 6)
        capture = json.loads((DATA / "capture.json").read_text())
        self.assertTrue(capture["documents_closed"])
        self.assertFalse(capture["authentication_headers_recorded"])
        events = {e["label"]: e for e in capture["events"]}
        native_kinds = {}
        for name, snapshot in snapshots.items():
            config = snapshot["configurations"][0]
            event = events[config["native_brep_capture_label"]]
            brep = event["response"]["result"]["structuredContent"]["result"]
            self.assertIsNone(brep["next_offset"])
            native_kinds[name] = sorted(e["body_kind"] for e in brep["entities"] if e["kind"] == "body")
            self.assertEqual(config["native_body_kinds"], native_kinds[name])
            self.assertEqual(snapshot["reopened_native_measurement"]["topology_counts"]["bodies"], len(native_kinds[name]))
            evidence = config["expected_state_evidence"]
            self.assertEqual(evidence["baseline_current_id"], evidence["target_identifier"])
            self.assertEqual(evidence["relation"], "matching_identifiers")
            self.assertEqual(len(evidence["mark_path"]), 1)
        active = snapshots["auxiliary-active.sldprt"]["configurations"][0]
        suppressed = snapshots["auxiliary-suppressed.sldprt"]["configurations"][0]
        self.assertEqual(active["expected_state_evidence"], suppressed["expected_state_evidence"])
        for key in ("expected_candidate_kinds", "expected_internal_candidate_kinds"):
            self.assertEqual(active[key], suppressed[key])
        self.assertEqual(native_kinds["auxiliary-active.sldprt"], ["sheet", "solid"])
        self.assertEqual(native_kinds["auxiliary-suppressed.sldprt"], ["solid"])
        self.assertEqual(expected["expected_state_status"], "unsupported")
        self.assertEqual(expected["expected_body_membership_status"], "unresolved")

    def test_fillet_suppression_changes_geometry_without_body_duplication(self):
        expected = json.loads((DATA / "expected.json").read_text())
        counts = {s["file"]: s["reopened_native_measurement"]["topology_counts"] for s in expected["snapshots"]}
        for name, faces in (("turned", 4), ("rounded", 5), ("suppressed", 4), ("restored", 5)):
            self.assertEqual(counts[name + ".sldprt"]["bodies"], 1)
            self.assertEqual(counts[name + ".sldprt"]["faces"], faces)
        capture = json.loads((DATA / "capture.json").read_text())
        updates = {e["label"]: e["request"]["params"]["arguments"]["params"] for e in capture["events"]
                   if e["label"] in ("suppress-round", "restore-round", "suppress-auxiliary")}
        self.assertTrue(updates["suppress-round"]["suppressed"])
        self.assertFalse(updates["restore-round"]["suppressed"])
        self.assertTrue(updates["suppress-auxiliary"]["suppressed"])
