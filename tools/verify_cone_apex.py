#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 openswx contributors
"""Offline native isolated-cone-apex regression across all three libraries."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import tempfile


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def audit(dataset):
    manifest = json.loads((dataset / "manifest.json").read_text())
    require(manifest["origin"] == "original_synthetic" and manifest["license"] == "MIT",
            "Expected original MIT fixtures")
    seen = set()
    for artifact in manifest["artifacts"]:
        path = dataset / artifact["path"]
        require(path.parent == dataset and not path.is_symlink() and path.is_file(), "Invalid artifact path")
        require(path.name not in seen, "Duplicate artifact path")
        seen.add(path.name)
        data = path.read_bytes()
        require(len(data) == artifact["bytes"] and hashlib.sha256(data).hexdigest() == artifact["sha256"],
                "Artifact hash mismatch: " + path.name)
    expected = json.loads((dataset / "expected.json").read_text())
    require(len(expected["cases"]) == 2 and {c["name"] for c in expected["cases"]} == {"cone", "blind-drill"},
            "Expected the cone and blind-drill fixtures")
    for case in expected["cases"]:
        require(all(case[key] in seen for key in ("source", "step")), "Unhashed fixture")
    return expected


def apex_pattern(topology, model):
    geometry = {g["source"]: g for g in model["geometry"]}
    nodes = {n["id"]: n for n in model["nodes"]}
    faces = {f["face"]: f for region in topology["regions"] for shell in region["shells"] for f in shell["faces"]}
    found = []
    for face in faces.values():
        isolated = [loop for loop in face["loops"] if loop["isolated_vertex"]]
        if not isolated:
            continue
        rings = [loop for loop in face["loops"] if not loop["isolated_vertex"]]
        require(len(face["loops"]) == 2 and len(isolated) == len(rings) == 1,
                "Expected one isolated apex and one regular loop")
        require(geometry[face["surface"]]["kind"] == "cone", "Isolated point is not on a cone")
        require(len(rings[0]["fins"]) == 1, "Expected one circular ring edge")
        fin = rings[0]["fins"][0]
        require(not fin["fin_curve"] and fin["start_vertex"] == fin["end_vertex"], "Unexpected apex cut topology")
        circle = geometry[fin["edge_curve"]]
        require(circle["kind"] == "circle", "Apex cut is not circular")
        vertex = isolated[0]["isolated_vertex"]["vertex"]
        points = [ref["target"] for ref in nodes[vertex]["references"] if ref["field"] == "point"]
        require(len(points) == 1 and geometry[points[0]]["kind"] == "point", "Missing apex point")
        found.append({"face_id": face["face"], "surface_id": face["surface"], "apex_vertex": vertex,
                      "apex_position_m": geometry[points[0]]["position"], "circle_curve_id": fin["edge_curve"],
                      "circle_radius_m": circle["radius"], "circle_center_m": circle["center"],
                      "loop_count": 2, "isolated_loop_count": 1, "circle_loop_count": 1})
    require(len(found) == 1, "Expected exactly one cone with an isolated apex")
    return found[0]


def step_cone_bound(path):
    text = path.read_text()
    entities = {int(key): re.sub(r"\s+", " ", value).strip()
                for key, value in re.findall(r"#(\d+)\s*=\s*(.*?);", text, re.S)}
    refs = lambda value: [int(key) for key in re.findall(r"#(\d+)", value)]
    cones = [key for key, value in entities.items() if value.startswith("CONICAL_SURFACE")]
    require(len(cones) == 1, "Expected exactly one STEP cone")
    faces = [value for value in entities.values() if value.startswith("ADVANCED_FACE")
             and refs(value)[-1] == cones[0]]
    require(len(faces) == 1 and len(refs(faces[0])) == 2, "Cone must have exactly one STEP bound")
    bound = entities[refs(faces[0])[0]]
    require(bound.startswith("FACE_OUTER_BOUND"), "Cone needs a circular outer bound")
    loop = entities[refs(bound)[0]]
    require(loop.startswith("EDGE_LOOP") and len(refs(loop)) == 1, "Unexpected cone STEP loop")
    use = entities[refs(loop)[0]]
    require(use.startswith("ORIENTED_EDGE"), "Cone bound lost its edge use")
    edge = entities[refs(use)[0]]
    require(edge.startswith("EDGE_CURVE") and entities[refs(edge)[-1]].startswith("CIRCLE"),
            "Cone bound lost its exact circle")
    return {"conical_faces": 1, "bounds": 1, "circular_edges": 1, "implicit_apex": True}


def verify(dataset, build, exporter, occt_python, output, baseline_exporter=None):
    expected = audit(dataset)
    require(not output.resolve().is_relative_to(dataset.resolve()), "Reports cannot overwrite fixtures")
    output.mkdir(parents=True, exist_ok=False)
    report = {"scope": "explicit_native_verified_checkpoint; no automatic history reconstruction", "cases": []}

    def run(label, command, check=True):
        process = subprocess.run([str(c) for c in command], capture_output=True, text=True, timeout=60)
        (output / (label + ".stdout")).write_text(process.stdout)
        (output / (label + ".stderr")).write_text(process.stderr)
        if check:
            require(process.returncode == 0, label + " failed: " + process.stderr[:500])
        return process

    def query(label, command):
        return json.loads(run(label, command).stdout)

    for case in expected["cases"]:
        name = case["name"]
        stages = {}
        source = dataset / case["source"]
        metadata = query(name + "-metadata", [build / "asmbox/swx_dump", source])
        require(metadata["doc_type"] == "part", "Wrong document type")
        config = next(c for c in metadata["configurations"] if c["name"] == case["configuration"])
        props = config["mass_properties"]
        for saved, native in (("volume", "volume"), ("surface_area", "area")):
            require(math.isclose(props[saved], case["native_measurement"]["mass_properties"][native], rel_tol=1e-9),
                    "Saved/native mass properties differ")
        stages["metadata"] = "pass"
        extracted = output / (name + "-payloads")
        inventory = query(name + "-extraction", [build / "asmbox/swx_dump", "--extract-parasolid", extracted, source])
        require(not inventory["issues"], "Extraction has issues")
        require([{k: p[k] for k in ("index", "kind", "source_stream", "bytes")} for p in inventory["payloads"]]
                == case["payload_inventory"], "Payload inventory changed")
        stages["extraction"] = "pass"
        inspect = build / "libopenparasolid/parasolid_inspect"
        for p in inventory["payloads"]:
            data = (extracted / p["file"]).read_bytes()
            require(hashlib.sha256(data).hexdigest() == case["payload_hashes"][str(p["index"])], "Payload bytes changed")
            decoded = query(name + "-decode-" + str(p["index"]), [inspect, "--nodes", "--summary", extracted / p["file"]])
            require(decoded["complete"] and not decoded["diagnostics"] and not decoded["uninterpreted_size"],
                    "Incomplete payload decoding")
        stages["decode"] = "pass"
        selection = case["selection"]
        selected = next(p for p in inventory["payloads"] if p["index"] == selection["payload_index"])
        require(selected["kind"] == "partition" and not selected["ghost_partition"], "Wrong selected checkpoint")
        path = extracted / selected["file"]
        topology = query(name + "-topology", [inspect, "--body-topology", selection["body_id"], path])
        counts = {k: topology["body_topology"]["counts"][k] for k in ("faces", "edges", "vertices")}
        require(counts == case["source_topology"], "Source topology changed")
        model = query(name + "-geometry", [inspect, "--geometry", path])["model"]
        pattern = apex_pattern(topology["body_topology"], model)
        require(pattern == case["apex_pattern"], "Isolated-apex representation changed")
        stages["topology"] = "pass"
        binding = query(name + "-binding", [inspect, "--body-geometry", selection["body_id"], "--binding-tolerance", "1e-8", path])
        require({k: binding["body_geometry"]["counts"][k] for k in counts} == counts, "Binding lost source topology")
        stages["binding"] = "pass"
        exported = output / (name + ".step")
        statistics = query(name + "-export", [exporter, source, selection["payload_index"], selection["body_id"], exported])
        require(statistics["faces"] == counts["faces"] and statistics["edges"] == counts["edges"]
                and statistics["solids"] == 1, "Export lost faces/edges or the complete solid")
        native_bound, exported_bound = step_cone_bound(dataset / case["step"]), step_cone_bound(exported)
        geometry = query(name + "-occt", [occt_python, Path(__file__).with_name("check_cone_apex_step.py"),
                                         name, dataset / case["step"], exported])
        stages["step"] = "pass"
        row = {"name": name, "stages": stages, "apex_pattern": pattern, "export_statistics": statistics,
               "native_step": native_bound, "library_step": exported_bound, "occt": geometry}
        if baseline_exporter:
            rejected_file = output / (name + "-before.step")
            before = run(name + "-baseline", [baseline_exporter, source, selection["payload_index"],
                                               selection["body_id"], rejected_file], check=False)
            diagnostic = json.loads(before.stdout)
            require(before.returncode == 2 and not rejected_file.exists()
                    and diagnostic["error_code"] == "unsupported_format"
                    and "Ruled patches require one non-isolated loop" in diagnostic["message"],
                    "Pre-fix control no longer reproduces the intended failure")
            row["baseline_failure_reproduced"] = True
        report["cases"].append(row)
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option, variable in (("openswx-build", "BUILD"), ("exporter", "EXPORTER"), ("occt-python", "OCCT_PYTHON"),
                             ("baseline-exporter", "BASELINE_EXPORTER"), ("output", "OUTPUT")):
        parser.add_argument("--" + option, type=Path, default=os.environ.get("OPENSWX_CORPUS_" + variable))
    parser.add_argument("--dataset", type=Path, default=os.environ.get("OPENSWX_CORPUS_CONE_APEX_DATASET",
                        str(Path(__file__).resolve().parents[1] / "verification/cone-apex-001")))
    args = parser.parse_args()
    if not all((args.openswx_build, args.exporter, args.occt_python)):
        parser.error("provide --openswx-build, --exporter and --occt-python or corresponding OPENSWX_CORPUS variables")
    paths = (args.dataset.resolve(), args.openswx_build.resolve(), args.exporter.resolve(), args.occt_python.absolute())
    baseline = args.baseline_exporter.resolve() if args.baseline_exporter else None
    if args.output:
        report = verify(*paths, args.output.resolve(), baseline)
    else:
        with tempfile.TemporaryDirectory(prefix="openswx-cone-apex-") as tmp:
            report = verify(*paths, Path(tmp) / "verification", baseline)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
