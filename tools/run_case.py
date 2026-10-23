#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 openswx contributors
"""Replay a frozen starter fixture without SolidWorks or a network."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys

from corpus import CorpusError, audit, load_json, selected_bodies


def require(condition, message):
    if not condition:
        raise CorpusError(message)


def main(fixed_case=None, legacy_exporter=False):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(os.environ.get(
        "OPENSWX_CORPUS_ROOT", Path(__file__).resolve().parents[1])))
    parser.add_argument("--openswx-build", type=Path,
                        default=os.environ.get("OPENSWX_CORPUS_BUILD"))
    parser.add_argument("--exporter", type=Path,
                        default=os.environ.get("OPENSWX_CORPUS_EXPORTER"))
    parser.add_argument("--occt-python", type=Path,
                        default=os.environ.get("OPENSWX_CORPUS_OCCT_PYTHON"))
    parser.add_argument("--output", type=Path, default=Path(os.environ.get(
        "OPENSWX_CORPUS_OUTPUT", "results/cylinder" if fixed_case else "results/fixture")))
    if fixed_case is None:
        parser.add_argument("--case", choices=("part-cylinder-001", "part-block-001", "part-tube-001", "part-blind-hole-001", "part-through-hole-001", "part-stepped-bore-001", "part-two-holes-001", "part-concave-profile-001", "part-multiple-solids-001"),
                            default=os.environ.get("OPENSWX_CORPUS_CASE"))
    args = parser.parse_args()
    case_id = fixed_case if fixed_case is not None else args.case
    if not case_id:
        parser.error("provide --case (or OPENSWX_CORPUS_CASE)")
    if not all((args.openswx_build, args.exporter, args.occt_python)):
        parser.error("provide --openswx-build, --exporter and --occt-python (or corresponding env vars)")
    root, output = args.root.resolve(), args.output.resolve()
    if output.is_relative_to(root / "cases"):
        parser.error("reports cannot overwrite admitted cases")
    try:
        output.mkdir(parents=True, exist_ok=False)
    except OSError as error:
        parser.error(str(error))
    report = {"case": case_id, "library_tests_executed": True,
              "stages": {s: "blocked" for s in ("metadata", "extraction", "decode", "topology", "binding", "step")}}

    def run(label, command):
        result = subprocess.run([str(c) for c in command], capture_output=True, text=True, timeout=60)
        (output / (label+".stdout")).write_text(result.stdout)
        (output / (label+".stderr")).write_text(result.stderr)
        return result

    def checked_json(label, command):
        result = run(label, command)
        require(result.returncode == 0, f"{label} failed: {result.stderr[:400]}")
        return json.loads(result.stdout)

    try:
        audit(root, require_ready=True)
        case = root / "cases" / case_id
        manifest, native = load_json(case / "case.json"), load_json(case / "reference/native.json")
        selection = manifest["selection"]
        payload_index = selection["payload_index"]
        selections = selected_bodies(selection,native)
        multiple = len(selections)>1
        report["selection"] = selection
        report["source_coordinate_unit"] = native["length_unit"]
        report["binding_tolerance_m"] = 1e-8
        require(manifest["tolerances"]["length_absolute_m"] == report["binding_tolerance_m"],
                "fixture tolerance differs from the starter export driver")
        if legacy_exporter:
            require(case_id == "part-cylinder-001" and payload_index == 0 and selection.get("body_id") == 2,
                    "legacy cylinder export driver selection differs from case")
        source = case / "source/model.sldprt"
        build = args.openswx_build.resolve()
        dump = build / "asmbox/swx_dump"
        inspect = build / "libopenparasolid/parasolid_inspect"
        report["corpus_commit"] = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
        report["corpus_worktree_dirty"] = bool(subprocess.check_output(
            ["git", "-C", str(root), "status", "--porcelain"], text=True).strip())
        report["executables"] = {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                                 for path in (dump, inspect, args.exporter.resolve())}
        document_measures = native.get("document_measurements_si",native["bodies"][0]["measurements_si"])
        metadata = checked_json("metadata", [dump, source])
        require(metadata["doc_type"] == "part", "wrong document type")
        require([c["name"] for c in metadata["configurations"]] == [manifest["configuration"]],
                "wrong saved configuration inventory")
        props = metadata["configurations"][0]["mass_properties"]
        for actual_key, expected_key in (("volume", "volume_m3"), ("surface_area", "area_m2")):
            require(math.isclose(props[actual_key], document_measures[expected_key],
                                 rel_tol=manifest["tolerances"]["measure_relative"]), "saved measure mismatch")
        if "centroid_m" in document_measures:
            center = props.get("center_of_gravity")
            require(isinstance(center,dict) and all(axis in center for axis in ("x","y","z")),
                    "missing saved centroid")
            require(math.dist([center[axis] for axis in ("x","y","z")],
                              document_measures["centroid_m"]) <=
                    manifest["tolerances"]["length_absolute_m"], "saved centroid mismatch")
        report["stages"]["metadata"] = "pass"
        extracted = output / "extracted"
        inventory = checked_json("extraction", [dump, "--extract-parasolid", extracted, source])
        frozen = load_json(case / "provenance/extraction.json")
        require(not inventory["issues"] and inventory["payload_count"] == frozen["payload_count"],
                "payload extraction mismatch")
        for payload, captured in zip(inventory["payloads"], frozen["payloads"]):
            require(all(payload[k] == captured[k] for k in ("index", "kind", "configuration_name", "bytes", "source_stream")),
                    "payload identity mismatch")
            require(hashlib.sha256((extracted / payload["file"]).read_bytes()).hexdigest() == captured["sha256"],
                    "extracted payload bytes changed")
        report["stages"]["extraction"] = "pass"
        selected_payload = next((p for p in inventory["payloads"] if p["index"] == payload_index), None)
        require(selected_payload is not None and selected_payload["kind"] == "partition",
                "explicit selection must identify a partition")
        require(hashlib.sha256((extracted / selected_payload["file"]).read_bytes()).hexdigest() ==
                hashlib.sha256((case / selection["payload_path"]).read_bytes()).hexdigest(),
                "selected checkpoint differs from frozen selection")
        partition = extracted / selected_payload["file"]
        for payload in inventory["payloads"]:
            decoded = checked_json("decode-"+str(payload["index"]),
                                   [inspect, "--nodes", "--summary", extracted / payload["file"]])
            require(decoded["complete"] and not decoded["diagnostics"] and decoded["uninterpreted_size"] == 0,
                    "incomplete embedded payload decode")
        report["stages"]["decode"] = "pass"
        # A separate file envelope is a known unsupported input, not a decode pass.
        raw = run("native-binary-envelope", [inspect, "--nodes", "--summary", case / "reference/model.x_b"])
        require(raw.returncode != 0 and "unsupported_format at byte 0" in raw.stderr,
                "native binary-envelope expectation changed; review known limit")
        report["native_binary_envelope"] = "expected unsupported_format at byte 0"
        for entry,expected in selections:
            body_id = str(entry["body_id"])
            label = "topology-"+body_id if multiple else "topology"
            topology = checked_json(label,[inspect,"--body-topology",body_id,"--summary",partition])
            require(topology.get("body_topology",{}).get("body")==entry["body_id"],
                    "topology result belongs to another body")
            for key in ("faces","edges","vertices"):
                require(topology["body_topology"]["counts"][key]==expected["counts"][key],
                        "recorded topology differs from native capture")
        report["stages"]["topology"] = "pass"
        for entry,expected in selections:
            body_id = str(entry["body_id"])
            label = "binding-"+body_id if multiple else "binding"
            binding = checked_json(label,[inspect,"--body-geometry",body_id,"--binding-tolerance","1e-8",partition])
            require(binding["body_geometry"].get("body")==entry["body_id"],
                    "binding result belongs to another body")
            for key in ("faces","edges","vertices"):
                require(binding["body_geometry"]["counts"][key]==expected["counts"][key],
                        "bound topology differs from native capture")
            require(binding["model"]["geometry_counts"]==
                    load_json(case / "validation/partition-decode.json")["model"]["geometry_counts"],
                    "support geometry inventory changed")
        report["stages"]["binding"] = "pass"
        exports,statistics = {},[]
        for entry,expected in selections:
            body_id = str(entry["body_id"])
            exported = output / ("body-"+body_id+".step" if multiple else "library.step")
            export_command = [args.exporter.resolve(),source]
            if not legacy_exporter:
                export_command.extend((str(payload_index),body_id))
            export_command.append(exported)
            label = "export-"+body_id if multiple else "export"
            counts = checked_json(label,export_command)
            for key in ("faces","edges"):
                require(counts[key]==expected["counts"][key],"export lost source topology")
            require(counts["solids"]==1,"expected one complete selected solid")
            exports[entry["native_body_key"]] = exported
            statistics.append({**entry,"statistics":counts})
        report["export_statistics"] = statistics if multiple else statistics[0]["statistics"]
        if multiple:
            invalid = output / "invalid-body.step"
            rejected = run("invalid-body-selection",[args.exporter.resolve(),source,
                           str(payload_index),"1",invalid])
            require(rejected.returncode==2 and "Target has the wrong node type" in rejected.stderr and not invalid.exists(),
                    "non-body selection was not rejected explicitly")
            report["invalid_body_selection"] = "node 1 rejected; no STEP written"
        checker = {"part-cylinder-001": "check_cylinder_step.py",
                   "part-block-001": "check_block_step.py",
                   "part-tube-001": "check_tube_step.py",
                   "part-blind-hole-001": "check_blind_hole_step.py",
                   "part-through-hole-001": "check_through_hole_step.py",
                   "part-stepped-bore-001": "check_stepped_bore_step.py",
                   "part-two-holes-001": "check_two_holes_step.py",
                   "part-concave-profile-001": "check_concave_profile_step.py",
                   "part-multiple-solids-001": "check_multiple_solids_step.py"}[case_id]
        export_paths = [exports[key] for key in ("large-block","small-block")] if multiple else list(exports.values())
        report["occt"] = checked_json("occt", [args.occt_python.absolute(),root / "tools" / checker,
                                               case / "reference/model.step",*export_paths])
        report["stages"]["step"] = "pass"
        report["state_scope"] = manifest["selection"]["state_scope"]
        print(json.dumps(report, indent=2))
        return 0
    except (CorpusError, OSError, ValueError, subprocess.SubprocessError) as error:
        report["failure"] = str(error)
        print(f"fixture regression: {error}", file=sys.stderr)
        return 2
    finally:
        (output / "report.json").write_text(json.dumps(report, indent=2)+"\n")


if __name__ == "__main__":
    sys.exit(main())
