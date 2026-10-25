#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 openswx contributors
"""Verify saved-geometry identity reports against native synthetic snapshots."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


def verify(dataset, executable):
    manifest = json.loads((dataset / "manifest.json").read_text())
    for artifact in manifest["artifacts"]:
        path = dataset / artifact["path"]
        if path.parent != dataset or not path.is_file():
            raise RuntimeError("Invalid verification artifact path")
        data = path.read_bytes()
        if len(data) != artifact["bytes"] or hashlib.sha256(data).hexdigest() != artifact["sha256"]:
            raise RuntimeError("Verification artifact hash mismatch: " + path.name)
    expected = json.loads((dataset / "expected.json").read_text())
    results = []
    for snapshot in expected["snapshots"]:
        source = dataset / snapshot["file"]
        if source.parent != dataset:
            raise RuntimeError("Invalid snapshot path")
        for configuration in snapshot["configurations"]:
            command = [str(executable), "--resolve-saved-geometry", configuration["name"], str(source)]
            process = subprocess.run(command, check=True, text=True, capture_output=True, timeout=60)
            report = json.loads(process.stdout)
            for key in ("configuration_status", "partition_status"):
                if report[key] != "resolved":
                    raise RuntimeError("Expected proven identity: " + key)
            if report["state_status"] != expected["expected_state_status"]:
                raise RuntimeError("Unresolved delta history was promoted or its expectation changed")
            if report["body_membership_status"] != expected["expected_body_membership_status"]:
                raise RuntimeError("Final-body membership was promoted without proof")
            for key in ("partition_index", "resolved_features_index"):
                if report[key] != configuration[key]:
                    raise RuntimeError("Wrong configuration namespace mapping: " + key)
            if report["was_last_active"] != (configuration["name"] == snapshot["active_configuration"]):
                raise RuntimeError("Wrong last-active configuration")
            selected = [c for c in report["candidates"] if c["selected_partition"]]
            if len(selected) != 1 or selected[0]["role"] != "configuration_partition":
                raise RuntimeError("Wrong partition selection")
            candidate = selected[0]
            if not candidate["decoded_complete"] or candidate["decode_issue"]:
                raise RuntimeError("Selected fixture partition no longer decodes completely")
            bodies = candidate["body_candidates"]
            if sorted(b["kind"] for b in bodies) != sorted(configuration["expected_candidate_kinds"]):
                raise RuntimeError("Selected baseline inventory differs from the independently reviewed fixture evidence")
            if "expected_internal_candidate_kinds" in configuration:
                internal = [b["kind"] for c in report["candidates"]
                            if c["role"] == "internal_feature_geometry" for b in c["body_candidates"]]
                if sorted(internal) != sorted(configuration["expected_internal_candidate_kinds"]):
                    raise RuntimeError("Internal feature inventory changed; review the source evidence")
            if not report["evidence"] or not report["limitations"]:
                raise RuntimeError("Missing resolution evidence or limitations")
            if "expected_state_evidence" in configuration:
                evidence = report["state_evidence"]
                for key, value in configuration["expected_state_evidence"].items():
                    if evidence[key] != value:
                        raise RuntimeError("Wrong saved-state evidence: " + key)
                if evidence["baseline_payload_index"] != candidate["payload_index"]:
                    raise RuntimeError("State evidence refers to another baseline")
                delta = next(c for c in report["candidates"]
                             if c["payload_index"] == evidence["delta_payload_index"])
                if (delta["kind"] != "deltas" or not delta["decoded_complete"]
                        or delta["body_candidates"] or delta["source"]["stream"] != candidate["source"]["stream"]
                        or delta["source"]["container_offset"] != candidate["source"]["container_offset"]):
                    raise RuntimeError("Delta framing/association was confused with a final body set")
                if candidate["world_current_id"] != evidence["baseline_current_id"]:
                    raise RuntimeError("Baseline identifier is not source evidence")
            results.append({"file": source.name, "configuration": configuration["name"],
                            "partition_index": report["partition_index"], "body_candidates": len(bodies),
                            "state_status": report["state_status"], "body_membership_status": report["body_membership_status"]})
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--swx-dump", type=Path, default=os.environ.get("OPENSWX_CORPUS_SWX_DUMP"))
    parser.add_argument("--dataset", type=Path, default=os.environ.get("OPENSWX_CORPUS_SAVED_GEOMETRY_DATASET",
        str(Path(__file__).resolve().parents[1] / "verification/saved-geometry-001")))
    args = parser.parse_args()
    if args.swx_dump is None:
        parser.error("provide --swx-dump or OPENSWX_CORPUS_SWX_DUMP")
    print(json.dumps({"verification": verify(args.dataset.resolve(), args.swx_dump.absolute())}, indent=2))


if __name__ == "__main__":
    main()
