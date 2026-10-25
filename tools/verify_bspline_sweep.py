#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 openswx contributors
"""Reproduce the native B_CURVE/SWEPT_SURF binding limitation offline."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile


MESSAGE = "Swept inversion requires a typed analytic section"


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def audit(dataset):
    manifest = json.loads((dataset / "manifest.json").read_text())
    require(manifest["origin"] == "original_synthetic" and manifest["license"] == "MIT", "Expected original MIT fixtures")
    seen = set()
    for artifact in manifest["artifacts"]:
        path = dataset / artifact["path"]
        require(path.parent == dataset and path.is_file() and not path.is_symlink()
                and path.name not in seen, "Invalid artifact path")
        seen.add(path.name)
        data = path.read_bytes()
        require(len(data) == artifact["bytes"] and hashlib.sha256(data).hexdigest() == artifact["sha256"],
                "Artifact hash mismatch: " + path.name)
    expected = json.loads((dataset / "expected.json").read_text())
    require(len(expected["cases"]) == 2 and {c["name"] for c in expected["cases"]} == {"cubic", "multispan"}, "Wrong sweep fixtures")
    for case in expected["cases"]:
        require(case["source"] in seen and case["step"] in seen, "Unhashed CAD fixture")
    return expected


def swept_pattern(topology, model):
    geometry = {g["source"]: g for g in model["geometry"]}
    nodes = {n["id"]: n for n in model["nodes"]}
    faces = {f["face"]: f for r in topology["regions"] for s in r["shells"] for f in s["faces"]}
    sweeps = [f for f in faces.values() if geometry[f["surface"]]["kind"] == "swept_surface"]
    require(len(sweeps) == 1, "Expected one swept boundary")
    face = sweeps[0]
    sweep = geometry[face["surface"]]
    section = geometry[sweep["section"]]
    require(nodes[sweep["section"]]["node_type"] == 134 and section["kind"] == "nurbs_curve", "Expected a typed B_CURVE section")
    require(section["axis"]["degree"] == 3 and not section["axis"]["closed"] and not section["axis"]["periodic"]
            and not section["controls"]["rational"] and section["controls"]["dimension"] == 3, "Wrong cubic section")
    require(len(face["loops"]) == 1 and not face["loops"][0]["isolated_vertex"]
            and len(face["loops"][0]["fins"]) == 4, "Expected a four-edge swept patch")
    types = sorted(geometry[f["edge_curve"]]["kind"] for f in face["loops"][0]["fins"])
    require(types == ["line", "line", "nurbs_curve", "nurbs_curve"], "Wrong swept-patch edge families")
    controls = section["controls"]["values"]
    require(max(controls[::3]) - min(controls[::3]) < 1e-12, "Section is not in the expected transverse plane")
    return {"face_id": face["face"], "surface_id": face["surface"], "section_id": sweep["section"],
            "degree": 3, "control_count": section["axis"]["control_count"],
            "knots": section["axis"]["knots"], "multiplicities": section["axis"]["multiplicities"],
            "sweep": sweep["sweep"], "loop_count": 1, "fin_count": 4, "edge_families": types}


def verify(dataset, build, exporter, occt_python, output):
    expected = audit(dataset)
    require(not output.resolve().is_relative_to(dataset.resolve()), "Reports cannot overwrite admitted fixtures")
    output.mkdir(parents=True, exist_ok=False)
    report = {"scope": "explicit native-verified checkpoints; binding/export remain unsupported", "cases": []}

    def run(label, command, success=True):
        r = subprocess.run([str(v) for v in command], capture_output=True, text=True, timeout=60)
        (output / (label + ".stdout")).write_text(r.stdout)
        (output / (label + ".stderr")).write_text(r.stderr)
        if success:
            require(r.returncode == 0, label + " failed: " + r.stderr[:500])
        return r

    def query(label, command):
        return json.loads(run(label, command).stdout)

    for case in expected["cases"]:
        name = case["name"]
        source = dataset / case["source"]
        metadata = query(name + "-metadata", [build / "asmbox/swx_dump", source])
        require(metadata["doc_type"] == "part", "Wrong document kind")
        config = next(c for c in metadata["configurations"] if c["name"] == case["configuration"])
        for saved, native in (("volume", "volume"), ("surface_area", "area")):
            require(math.isclose(config["mass_properties"][saved], case["native_measurement"]["mass_properties"][native], rel_tol=1e-9),
                    "Saved properties differ from native observations")
        extracted = output / (name + "-payloads")
        inventory = query(name + "-extraction", [build / "asmbox/swx_dump", "--extract-parasolid", extracted, source])
        require(not inventory["issues"], "Extraction has issues")
        require([{k: p[k] for k in ("index", "kind", "source_stream", "bytes")} for p in inventory["payloads"]]
                == case["payload_inventory"], "Changed payload inventory")
        inspect = build / "libopenparasolid/parasolid_inspect"
        for p in inventory["payloads"]:
            path = extracted / p["file"]
            require(hashlib.sha256(path.read_bytes()).hexdigest() == case["payload_hashes"][str(p["index"])], "Changed payload bytes")
            decoded = query(name + "-decode-" + str(p["index"]), [inspect, "--nodes", "--summary", path])
            require(decoded["complete"] and not decoded["diagnostics"] and not decoded["uninterpreted_size"], "Incomplete decoding")
        selection = case["selection"]
        p = next(p for p in inventory["payloads"] if p["index"] == selection["payload_index"])
        require(p["kind"] == "partition" and not p["ghost_partition"], "Wrong explicit checkpoint")
        path = extracted / p["file"]
        topology = query(name + "-topology", [inspect, "--body-topology", selection["body_id"], path])
        require({k: topology["body_topology"]["counts"][k] for k in case["source_topology"]} == case["source_topology"], "Wrong source topology")
        model = query(name + "-geometry", [inspect, "--geometry", path])["model"]
        pattern = swept_pattern(topology["body_topology"], model)
        require(pattern == case["swept_pattern"], "Changed B_CURVE sweep representation")
        bound = run(name + "-binding", [inspect, "--body-geometry", selection["body_id"], "--binding-tolerance", "1e-8", path], success=False)
        parsed = json.loads(bound.stdout)
        error = parsed.get("body_geometry_error") or {}
        require(bound.returncode == 2 and parsed["body_geometry"] is None and error.get("code") == "unsupported_format"
                and MESSAGE in error.get("message", ""), "Binding limitation changed; review the expectation")
        target = output / (name + ".step")
        exported = run(name + "-export", [exporter, source, selection["payload_index"], selection["body_id"], target], success=False)
        export_error = json.loads(exported.stdout)
        require(exported.returncode == 2 and export_error.get("error_code") == "unsupported_format"
                and MESSAGE in export_error.get("message", "") and not target.exists() and not target.is_symlink(),
                "Exporter limitation changed or a partial STEP was published")
        oracle = query(name + "-native-occt", [occt_python, Path(__file__).with_name("check_bspline_sweep_step.py"), name, dataset / case["step"]])
        report["cases"].append({"name": name, "stages": {"metadata": "pass", "extraction": "pass", "decode": "pass",
                                "topology": "pass", "binding": "expected_unsupported", "step": "expected_unsupported"},
                                "swept_pattern": pattern, "binding_error": error, "export_error": export_error,
                                "native_reference": oracle, "partial_output_created": False})
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option, env in (("openswx-build", "BUILD"), ("exporter", "EXPORTER"), ("occt-python", "OCCT_PYTHON"), ("output", "OUTPUT")):
        parser.add_argument("--" + option, type=Path, default=os.environ.get("OPENSWX_CORPUS_" + env))
    parser.add_argument("--dataset", type=Path, default=os.environ.get("OPENSWX_CORPUS_BSPLINE_SWEEP_DATASET",
                        str(Path(__file__).resolve().parents[1] / "verification/bspline-sweep-001")))
    args = parser.parse_args()
    if not all((args.openswx_build, args.exporter, args.occt_python)):
        parser.error("provide --openswx-build, --exporter and --occt-python or their OPENSWX_CORPUS variables")
    paths = (args.dataset.resolve(), args.openswx_build.resolve(), args.exporter.resolve(), args.occt_python.absolute())
    if args.output:
        report = verify(*paths, args.output.resolve())
    else:
        with tempfile.TemporaryDirectory(prefix="bspline-sweep-") as tmp:
            report = verify(*paths, Path(tmp) / "verification")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
