#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 openswx contributors
"""Validate corpus contracts and immutable artifacts; never call SolidWorks."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError

JSON_LIMIT = 16 * 1024 * 1024
STAGES = ("metadata", "extraction", "decode", "topology", "binding", "step")
REFERENCE_ROLES = {"parasolid_binary", "parasolid_text", "step_reference"}


class CorpusError(ValueError):
    """An invalid corpus contract or artifact."""


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise CorpusError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def finite_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise CorpusError(f"nonfinite JSON number: {value}")
    return number


def reject_constant(value):
    raise CorpusError(f"invalid JSON constant: {value}")


def load_json(path):
    if path.stat().st_size > JSON_LIMIT:
        raise CorpusError(f"JSON exceeds {JSON_LIMIT} bytes: {path}")
    return json.loads(path.read_text(encoding="utf-8"),
                      object_pairs_hook=unique_object, parse_float=finite_float,
                      parse_constant=reject_constant)


def local_file(root, relative):
    """Require a regular file below root, without symlink components."""
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts or "\\" in relative or ":" in relative:
        raise CorpusError(f"unsafe relative path: {relative}")
    target = root
    for component in path.parts:
        target = target / component
        if target.is_symlink():
            raise CorpusError(f"symlink is not a corpus artifact: {target}")
    if not target.is_file() or not target.resolve().is_relative_to(root.resolve()):
        raise CorpusError(f"missing or nonlocal file: {target}")
    return target


def validate(root, name, value):
    schema = load_json(local_file(root, f"schemas/{name}.schema.json"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    error = next(validator.iter_errors(value), None)
    if error:
        location = "/".join(str(part) for part in error.absolute_path)
        raise CorpusError(f"{name}/{location}: {error.message}")


def analytic_measures(recipe):
    kind = recipe["analytic"]["shape"]
    values = recipe["analytic"]["dimensions_m"]
    keys = {"block": {"width", "depth", "height"},
            "cylinder": {"radius", "height"},
            "tube": {"outer_radius", "inner_radius", "height"},
            "blind_hole": {"outer_radius", "inner_radius", "height", "hole_depth"}}[kind]
    if set(values) != keys:
        raise CorpusError(f"{kind}: expected dimensions {sorted(keys)}")
    height = values["height"]
    if kind == "block":
        width, depth = values["width"], values["depth"]
        volume = width * depth * height
        area = 2 * (width * depth + width * height + depth * height)
    elif kind == "blind_hole":
        radius, inner, depth = values["outer_radius"], values["inner_radius"], values["hole_depth"]
        if not inner < radius or not depth < height:
            raise CorpusError("blind hole requires a smaller radius and positive remaining floor")
        volume = math.pi * (radius**2 * height - inner**2 * depth)
        area = 2 * math.pi * radius**2 + 2 * math.pi * radius * height + 2 * math.pi * inner * depth
    else:
        radius = values["radius"] if kind == "cylinder" else values["outer_radius"]
        inner = 0 if kind == "cylinder" else values["inner_radius"]
        if not inner < radius:
            raise CorpusError("tube: inner radius must be smaller than outer radius")
        volume = math.pi * (radius**2 - inner**2) * height
        area = 2 * math.pi * (radius**2 - inner**2) + 2 * math.pi * (radius + inner) * height
    if not all(math.isfinite(value) and value > 0 for value in (volume, area)):
        raise CorpusError("analytic dimensions produce nonfinite or unresolved measures")
    return {"volume_m3": volume, "area_m2": area}


def read_recipe(root, relative, case_id):
    recipe = load_json(local_file(root, relative))
    validate(root, "recipe", recipe)
    if recipe["id"] != case_id:
        raise CorpusError(f"recipe ID does not match {case_id}")
    ids = [step["id"] for step in recipe["steps"]]
    if len(ids) != len(set(ids)):
        raise CorpusError(f"duplicate recipe step: {case_id}")
    if recipe["steps"][0]["operation"] != "create_part":
        raise CorpusError("starter recipe must create a fresh part first")
    profiles = set()
    has_solid = False
    for step in recipe["steps"][1:]:
        if step["operation"].startswith("sketch_"):
            profiles.add(step["id"])
        elif step["operation"] == "extrude":
            if not set(step["parameters"]["profiles"]) <= profiles:
                raise CorpusError("extrusion references an unknown or later sketch")
            if step["parameters"]["operation"] == "cut" and not has_solid:
                raise CorpusError("cut requires an earlier solid-body extrusion")
            if step["parameters"]["operation"] == "new_body":
                has_solid = True
        else:
            raise CorpusError("starter recipe must have exactly one create_part")
    if recipe["steps"][-1]["operation"] != "extrude":
        raise CorpusError("starter recipe must end with an extrusion")
    analytic_measures(recipe)
    return recipe


def check_native(manifest, native, recipe):
    for key in ("configuration", "document_revision"):
        if native[key] != manifest[key]:
            raise CorpusError(f"native {key} differs from manifest")
    keys = [body["key"] for body in native["bodies"]]
    if len(keys) != len(set(keys)):
        raise CorpusError("duplicate native body key")
    if recipe:
        if len(native["bodies"]) != 1 or native["bodies"][0]["kind"] != "solid":
            raise CorpusError("analytic starter recipes require exactly one solid body")
        measurements = native["bodies"][0]["measurements_si"]
        tolerance = manifest["tolerances"]
        for quantity, target in analytic_measures(recipe).items():
            absolute = tolerance["volume_absolute_m3" if quantity == "volume_m3" else "area_absolute_m2"]
            if quantity not in measurements or not math.isclose(
                    measurements[quantity], target,
                    rel_tol=tolerance["measure_relative"], abs_tol=absolute):
                raise CorpusError(f"native analytic mismatch: {quantity}, expected {target}")


def check_case(root, case_dir, planned):
    manifest = load_json(local_file(case_dir, "case.json"))
    validate(root, "case", manifest)
    case_id = manifest["id"]
    if case_id != case_dir.name or case_id != planned["id"]:
        raise CorpusError("case directory, manifest and plan IDs must agree")
    if manifest["document_kind"] != planned["document_kind"]:
        raise CorpusError(f"document kind differs from plan: {case_id}")
    recipe = read_recipe(root, manifest["recipe"], case_id)
    by_path, by_role = {}, {}
    for artifact in manifest["artifacts"]:
        path = artifact["path"]
        if path in by_path:
            raise CorpusError(f"duplicate artifact path: {path}")
        source = local_file(case_dir, path)
        if source.stat().st_size != artifact["bytes"]:
            raise CorpusError(f"artifact size mismatch: {source}")
        digest = hashlib.sha256()
        with source.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        if digest.hexdigest() != artifact["sha256"]:
            raise CorpusError(f"artifact hash mismatch: {source}")
        by_path[path] = artifact
        by_role.setdefault(artifact["role"], []).append(artifact)
    required = {"source", "native", "capabilities", "export_receipts"}
    if manifest["document_kind"] in ("part", "assembly"):
        required |= REFERENCE_ROLES
    if not required <= by_role.keys():
        raise CorpusError(f"missing artifact roles: {sorted(required - by_role.keys())}")
    if "selection" in manifest:
        selection = manifest["selection"]
        selected = by_path.get(selection["payload_path"])
        if not selected or selected["role"] != "derived_payload":
            raise CorpusError("selected checkpoint must be a declared derived payload")
        if selection["configuration"] != manifest["configuration"]:
            raise CorpusError("selected checkpoint configuration differs from manifest")
    for role, artifacts in by_role.items():
        if role not in {"dependency", "capture_evidence", "derived_payload", "validation_report"} and len(artifacts) != 1:
            raise CorpusError(f"expected exactly one artifact for {role}")
    listed = set(by_path) | {"case.json"}
    for path in case_dir.rglob("*"):
        if path.is_symlink() or (path.is_file() and path.relative_to(case_dir).as_posix() not in listed):
            raise CorpusError(f"unlisted or symlinked case artifact: {path}")
    capabilities = load_json(local_file(case_dir, by_role["capabilities"][0]["path"]))
    if not isinstance(capabilities, dict) or not capabilities:
        raise CorpusError("capabilities snapshot must be a nonempty JSON object")
    native = load_json(local_file(case_dir, by_role["native"][0]["path"]))
    validate(root, "native", native)
    check_native(manifest, native, recipe)
    receipts = load_json(local_file(case_dir, by_role["export_receipts"][0]["path"]))
    validate(root, "receipts", receipts)
    covered = set()
    for receipt in receipts["exports"]:
        path = receipt["artifact_path"]
        artifact = by_path.get(path)
        if not artifact or artifact["role"] != receipt["format"] or path in covered:
            raise CorpusError(f"duplicate or unmatched export receipt: {path}")
        for key in ("bytes", "sha256"):
            if receipt[key] != artifact[key]:
                raise CorpusError(f"receipt {key} mismatch: {path}")
        for key in ("configuration", "document_revision"):
            if receipt[key] != manifest[key]:
                raise CorpusError(f"receipt {key} differs from manifest: {path}")
        if receipt["format"] == "step_reference" and receipt.get("application_protocol") != "AP214":
            raise CorpusError("starter STEP reference must verify AP214")
        expected_scale = {"metre": 1.0, "millimetre": .001}[receipt["length_unit"]]
        if receipt["source_to_metre_scale"] != expected_scale:
            raise CorpusError(f"receipt unit/scale mismatch: {path}")
        covered.add(path)
    reference_paths = {a["path"] for a in by_path.values() if a["role"] in REFERENCE_ROLES}
    if covered != reference_paths:
        raise CorpusError("each reference export needs exactly one verified receipt")
    # A manifest is provenance/expectation data, never evidence of a library pass.
    return {"id": case_id, "expectations": manifest["expectations"]}


def audit(root, require_ready=False):
    root = root.resolve()
    plan = load_json(local_file(root, "plan.json"))
    validate(root, "plan", plan)
    planned = {}
    for item in plan["cases"]:
        if item["id"] in planned:
            raise CorpusError(f"duplicate plan ID: {item['id']}")
        planned[item["id"]] = item
        if "recipe" in item:
            read_recipe(root, item["recipe"], item["id"])
    ready = []
    cases_dir = root / "cases"
    if cases_dir.is_symlink() or not cases_dir.is_dir():
        raise CorpusError("cases must be a local directory")
    for path in sorted(cases_dir.iterdir()):
        if path.name.startswith("."):
            continue
        if path.is_symlink() or not path.is_dir() or path.name not in planned:
            raise CorpusError(f"unplanned case directory or file: {path}")
        ready.append(check_case(root, path, planned[path.name]))
    if require_ready and not ready:
        raise CorpusError("no captured cases; this is preparation, not corpus coverage")
    return {"planned_cases": len(planned), "captured_cases": len(ready),
            "pending_cases": sorted(set(planned) - {case["id"] for case in ready}),
            "priority_counts": {p: sum(c["priority"] == p for c in planned.values())
                                for p in ("P0", "P1", "P2")},
            "cases": ready, "library_tests_executed": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path,
                        default=Path(os.environ.get("OPENSWX_CORPUS_ROOT", Path(__file__).resolve().parents[1])))
    parser.add_argument("--require-ready", action="store_true",
                        default=os.environ.get("OPENSWX_CORPUS_REQUIRE_READY", "0") == "1",
                        help="fail if no captured case exists (env: OPENSWX_CORPUS_REQUIRE_READY=1)")
    args = parser.parse_args()
    try:
        print(json.dumps(audit(args.root, args.require_ready), indent=2))
    except (CorpusError, OSError, ValueError, OverflowError, SchemaError) as error:
        print(f"corpus: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
