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


def aggregate_measures(bodies):
    """Sum disjoint body measures; weight centroids by geometric volume."""
    bodies = list(bodies)
    volume = sum(b["volume_m3"] for b in bodies)
    result = {"volume_m3":volume,"area_m2":sum(b["area_m2"] for b in bodies)}
    if volume>0 and all("centroid_m" in b for b in bodies):
        result["centroid_m"] = [sum(b["volume_m3"]*b["centroid_m"][i] for b in bodies)/volume
                                for i in range(3)]
    return result


def multiple_solid_measures(recipe):
    values = recipe["analytic"]["dimensions_m"]
    expected = {prefix+"_"+axis for prefix in ("first","second") for axis in ("width","depth","height")} | {"gap"}
    if set(values)!=expected:
        raise CorpusError("multiple solids: expected two block dimensions and a positive gap")
    measures = {}
    for prefix,key,x in (("first","large-block",0),
                         ("second","small-block",values["first_width"]+values["gap"])):
        w,d,h = (values[prefix+"_"+axis] for axis in ("width","depth","height"))
        volume,area = w*d*h,2*(w*d+w*h+d*h)
        if not all(math.isfinite(v) and v>0 for v in (volume,area)):
            raise CorpusError("multiple solids: unresolved block measures")
        measures[key] = {"volume_m3":volume,"area_m2":area,"centroid_m":[x+w/2,d/2,h/2]}
    return measures


def selected_bodies(selection,native):
    """Map explicit Parasolid IDs to native keys without assuming body order."""
    bodies = {b["key"]:b for b in native["bodies"]}
    if len(bodies)!=len(native["bodies"]):
        raise CorpusError("duplicate native body key")
    if "body_id" in selection:
        if "bodies" in selection or len(bodies)!=1:
            raise CorpusError("single body selection requires exactly one native body")
        entries = [{"body_id":selection["body_id"],"native_body_key":next(iter(bodies))}]
    else:
        entries = selection.get("bodies",[])
    keys = [e["native_body_key"] for e in entries]
    ids = [e["body_id"] for e in entries]
    if len(keys)!=len(set(keys)) or set(keys)!=set(bodies) or len(ids)!=len(set(ids)):
        raise CorpusError("body selections must uniquely cover every native body")
    return [(e,bodies[e["native_body_key"]]) for e in entries]


def ellipse_perimeter(major, minor):
    """Integrate the periodic ellipse speed with a converged trapezoidal rule."""
    if not (math.isfinite(major) and math.isfinite(minor) and 0 < minor <= major):
        raise CorpusError("ellipse requires positive finite ordered radii")
    previous = None
    for count in (64,128,256,512,1024,2048,4096,8192):
        value = 2*math.pi/count*math.fsum(
            math.hypot(major*math.sin(2*math.pi*i/count),minor*math.cos(2*math.pi*i/count))
            for i in range(count))
        if previous is not None and math.isclose(value,previous,rel_tol=1e-13):
            return value
        previous = value
    raise CorpusError("ellipse perimeter quadrature did not converge")


def analytic_measures(recipe):
    kind = recipe["analytic"]["shape"]
    values = recipe["analytic"]["dimensions_m"]
    if kind == "multiple_solids":
        return aggregate_measures(multiple_solid_measures(recipe).values())
    if kind == "elliptic_prism":
        if set(values) != {"major_radius","minor_radius","height"}:
            raise CorpusError("elliptic prism: expected two semiaxes and height")
        major,minor,height = (values[k] for k in ("major_radius","minor_radius","height"))
        if not (math.isfinite(height) and height>0 and major>minor):
            raise CorpusError("elliptic prism requires a positive height and distinct ordered radii")
        perimeter = ellipse_perimeter(major,minor)
        volume,area = math.pi*major*minor*height,2*math.pi*major*minor+height*perimeter
        if not all(math.isfinite(v) and v>0 for v in (volume,area)):
            raise CorpusError("elliptic prism: unresolved measures")
        return {"volume_m3":volume,"area_m2":area}
    if kind == "chamfer_cylinder":
        if set(values) != {"radius", "height", "chamfer_size"}:
            raise CorpusError("chamfer cylinder: expected radius, height and chamfer size")
        radius,height,size = values["radius"],values["height"],values["chamfer_size"]
        if not (all(math.isfinite(v) and v>0 for v in (radius,height,size)) and size < radius and size < height):
            raise CorpusError("chamfer requires positive top radius and remaining cylinder")
        top = radius-size
        volume = math.pi*(radius**2*(height-size)+size*(radius**2+radius*top+top**2)/3)
        area = math.pi*(radius**2+top**2+2*radius*(height-size)+(radius+top)*math.sqrt(2)*size)
        if not all(math.isfinite(v) and v>0 for v in (volume,area)):
            raise CorpusError("chamfer cylinder: unresolved measures")
        return {"volume_m3":volume,"area_m2":area}
    if kind == "fillet_cylinder":
        if set(values) != {"radius", "height", "fillet_radius"}:
            raise CorpusError("fillet cylinder: expected cylinder radius, height and fillet radius")
        radius,height,blend = values["radius"],values["height"],values["fillet_radius"]
        if not (blend < height and 2*blend < radius):
            raise CorpusError("fillet requires a positive remaining cylinder and regular ring torus")
        major = radius-blend
        volume = math.pi*(radius**2*(height-blend)+major**2*blend+major*math.pi*blend**2/2+2*blend**3/3)
        area = math.pi*(radius**2+major**2+2*radius*(height-blend)+2*blend**2)+math.pi**2*major*blend
        if not all(math.isfinite(v) and v>0 for v in (volume,area)):
            raise CorpusError("fillet cylinder: unresolved measures")
        return {"volume_m3":volume,"area_m2":area}
    if kind in ("torus", "torus_cut"):
        if set(values) != {"major_radius", "minor_radius"}:
            raise CorpusError("torus: expected major and minor radii")
        major,minor = values["major_radius"],values["minor_radius"]
        if not minor < major:
            raise CorpusError("ring torus requires minor radius smaller than major radius")
        volume,area = 2*math.pi**2*major*minor**2,4*math.pi**2*major*minor
        if kind == "torus_cut":
            angle = recipe["analytic"]["angle_rad"]
            if not 0 < angle < 2*math.pi:
                raise CorpusError("torus cut requires a strict partial revolution")
            volume *= angle/(2*math.pi)
            area = area*angle/(2*math.pi)+2*math.pi*minor**2
        if not all(math.isfinite(v) and v>0 for v in (volume,area)):
            raise CorpusError("torus: unresolved measures")
        return {"volume_m3":volume,"area_m2":area}
    if kind == "sphere_cap":
        if set(values) != {"radius", "cap_height"}:
            raise CorpusError("sphere cap: expected radius and cap height")
        radius,height = values["radius"],values["cap_height"]
        if not height < radius:
            raise CorpusError("minor sphere cap requires height smaller than radius")
        return {"volume_m3":math.pi*height**2*(radius-height/3),
                "area_m2":math.pi*height*(4*radius-height)}
    if kind == "sphere":
        if set(values) != {"radius"}:
            raise CorpusError("sphere: expected one radius")
        radius = values["radius"]
        volume,area = 4*math.pi*radius**3/3,4*math.pi*radius**2
        if not all(math.isfinite(v) and v>0 for v in (volume,area)):
            raise CorpusError("sphere: unresolved measures")
        return {"volume_m3":volume,"area_m2":area}
    keys = {"cone_sector": {"bottom_radius", "top_radius", "height"},
            "cone_frustum": {"bottom_radius", "top_radius", "height"},
            "block": {"width", "depth", "height"},
            "cylinder": {"radius", "height"},
            "tube": {"outer_radius", "inner_radius", "height"},
            "blind_hole": {"outer_radius", "inner_radius", "height", "hole_depth"},
            "through_hole": {"width", "depth", "height", "bore_radius", "bore_x", "bore_y"},
            "stepped_bore": {"outer_radius", "bore_radius", "counterbore_radius", "height", "counterbore_depth"},
            "concave_profile": {"width", "depth", "height", "vertical_leg_width", "horizontal_leg_depth"},
            "two_holes": {"width", "depth", "height", "bore_radius", "first_x", "first_y", "second_x", "second_y"}}[kind]
    if set(values) != keys:
        raise CorpusError(f"{kind}: expected dimensions {sorted(keys)}")
    height = values["height"]
    if kind == "block":
        width, depth = values["width"], values["depth"]
        volume = width * depth * height
        area = 2 * (width * depth + width * height + depth * height)
    elif kind in ("cone_frustum", "cone_sector"):
        bottom, top = values["bottom_radius"], values["top_radius"]
        if not top < bottom:
            raise CorpusError("cone frustum requires a smaller positive top radius")
        volume = math.pi*height*(bottom**2+bottom*top+top**2)/3
        area = math.pi*(bottom**2+top**2+(bottom+top)*math.hypot(height,bottom-top))
        if kind == "cone_sector":
            angle = recipe["analytic"]["angle_rad"]
            if not 0 < angle < 2*math.pi:
                raise CorpusError("cone sector requires a strict partial revolution")
            volume *= angle/(2*math.pi)
            area = area*angle/(2*math.pi)+(bottom+top)*height
    elif kind == "concave_profile":
        width, depth = values["width"], values["depth"]
        leg, foot = values["vertical_leg_width"], values["horizontal_leg_depth"]
        if not (leg < width and foot < depth):
            raise CorpusError("L-profile requires a positive notch and two remaining legs")
        section = width*foot + leg*(depth-foot)
        volume = section*height
        area = 2*section + 2*(width+depth)*height
    elif kind == "two_holes":
        width, depth, radius = values["width"], values["depth"], values["bore_radius"]
        centers = ((values["first_x"],values["first_y"]),(values["second_x"],values["second_y"]))
        if not all(radius < x < width-radius and radius < y < depth-radius for x,y in centers):
            raise CorpusError("both bores need positive side clearance")
        if not math.dist(*centers) > 2*radius:
            raise CorpusError("two bores must be strictly separated")
        volume = (width*depth-2*math.pi*radius**2)*height
        area = 2*(width*depth+width*height+depth*height)-4*math.pi*radius**2+4*math.pi*radius*height
    elif kind == "through_hole":
        width, depth, radius = values["width"], values["depth"], values["bore_radius"]
        x, y = values["bore_x"], values["bore_y"]
        if not (radius < x < width-radius and radius < y < depth-radius):
            raise CorpusError("through bore must have positive clearance from all block sides")
        volume = (width * depth - math.pi * radius**2) * height
        area = 2*(width*depth + width*height + depth*height) - 2*math.pi*radius**2 + 2*math.pi*radius*height
    elif kind == "stepped_bore":
        radius, bore, counter = values["outer_radius"], values["bore_radius"], values["counterbore_radius"]
        depth = values["counterbore_depth"]
        if not (bore < counter < radius and depth < height):
            raise CorpusError("stepped bore requires ordered radii, a positive wall and a remaining shoulder")
        volume = math.pi * ((radius**2-bore**2)*height - (counter**2-bore**2)*depth)
        area = 2*math.pi*(radius**2-bore**2) + 2*math.pi*(radius*height+bore*(height-depth)+counter*depth)
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


def check_polygon(vertices):
    """Require one simple closed contour; closing edge is implicit."""
    edges = list(zip(vertices,vertices[1:]+vertices[:1]))
    def cross(a,b,c):
        return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    def on_segment(a,b,p):
        return cross(a,b,p)==0 and all(min(x,y)<=z<=max(x,y) for x,y,z in zip(a,b,p))
    def intersects(a,b,c,d):
        return ((cross(a,b,c)*cross(a,b,d)<0 and cross(c,d,a)*cross(c,d,b)<0) or
                any((on_segment(a,b,c),on_segment(a,b,d),on_segment(c,d,a),on_segment(c,d,b))))
    for i,(a,b) in enumerate(edges):
        for j,(c,d) in enumerate(edges):
            if j<=i or j==i+1 or (i==0 and j==len(edges)-1):
                continue
            if intersects(a,b,c,d):
                raise CorpusError("polygon must not self-intersect or touch nonadjacent edges")
    twice_area = sum(a[0]*b[1]-b[0]*a[1] for a,b in edges)
    if not math.isfinite(twice_area) or twice_area==0:
        raise CorpusError("polygon must enclose a finite nonzero area")


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
    sketches = {}
    has_solid = False
    for step in recipe["steps"][1:]:
        if step["operation"].startswith("sketch_"):
            if step["operation"] == "sketch_polygon":
                check_polygon(step["parameters"]["vertices_m"])
            profiles.add(step["id"])
            sketches[step["id"]] = step
        elif step["operation"] in ("extrude", "revolve"):
            if not set(step["parameters"]["profiles"]) <= profiles:
                raise CorpusError("extrusion references an unknown or later sketch")
            if step["operation"] == "revolve":
                profile = sketches[step["parameters"]["profiles"][0]]
                if profile["operation"] not in ("sketch_polygon", "sketch_semicircle", "sketch_spherical_cap", "sketch_offset_circle") or profile["parameters"]["plane"] != "XZ":
                    raise CorpusError("starter revolution requires a supported XZ profile")
            if step["parameters"]["operation"] == "cut" and not has_solid:
                raise CorpusError("cut requires an earlier solid-body extrusion")
            if step["parameters"]["operation"] == "new_body":
                has_solid = True
        elif step["operation"] == "fillet":
            if not has_solid:
                raise CorpusError("fillet requires an earlier solid-body feature")
        else:
            raise CorpusError("starter recipe must have exactly one create_part")
    if recipe["steps"][-1]["operation"] not in ("extrude", "revolve", "fillet"):
        raise CorpusError("starter recipe must end with an extrusion, revolution or fillet")
    kind = recipe["analytic"]["shape"]
    if kind in ("cone_frustum", "cone_sector", "sphere", "sphere_cap", "torus", "torus_cut", "chamfer_cylinder"):
        revolutions = [step for step in recipe["steps"] if step["operation"] == "revolve"]
        expected_angle = recipe["analytic"].get("angle_rad",2*math.pi)
        if len(revolutions) != 1 or revolutions[0]["parameters"]["angle_rad"] != expected_angle:
            raise CorpusError("revolution construction angle differs from analytic angle")
        if kind in ("torus", "torus_cut"):
            profile = sketches[revolutions[0]["parameters"]["profiles"][0]]
            values = recipe["analytic"]["dimensions_m"]
            if profile["operation"] != "sketch_offset_circle" or profile["parameters"]["radial_offset_m"] != values["major_radius"] or profile["parameters"]["radius_m"] != values["minor_radius"]:
                raise CorpusError("torus construction requires matching offset and circle radius")
        if kind in ("sphere", "sphere_cap"):
            profile = sketches[revolutions[0]["parameters"]["profiles"][0]]
            expected_profile = "sketch_semicircle" if kind == "sphere" else "sketch_spherical_cap"
            if profile["operation"] != expected_profile or profile["parameters"]["radius_m"] != recipe["analytic"]["dimensions_m"]["radius"]:
                raise CorpusError("sphere construction requires the matching profile radius")
            if kind == "sphere_cap" and profile["parameters"]["cap_height_m"] != recipe["analytic"]["dimensions_m"]["cap_height"]:
                raise CorpusError("sphere cap construction height differs from analytic height")
    if kind == "elliptic_prism":
        if [s["operation"] for s in recipe["steps"]] != ["create_part","sketch_ellipse","extrude"]:
            raise CorpusError("elliptic prism requires one ellipse extrusion")
        profile,extrusion = (s["parameters"] for s in recipe["steps"][1:])
        values = recipe["analytic"]["dimensions_m"]
        if (profile["plane"] != "XY" or profile["center_m"] != [0,0,0] or
                profile["major_radius_m"] != values["major_radius"] or
                profile["minor_radius_m"] != values["minor_radius"] or
                extrusion["height_m"] != values["height"] or extrusion["direction"] != [0,0,1] or
                extrusion["operation"] != "new_body" or
                extrusion["profiles"] != [recipe["steps"][1]["id"]]):
            raise CorpusError("ellipse extrusion differs from analytic dimensions or placement")
    if kind == "chamfer_cylinder":
        if [s["operation"] for s in recipe["steps"]] != ["create_part","sketch_polygon","revolve"]:
            raise CorpusError("chamfer cylinder requires one revolved profile")
        radius,height,size = (recipe["analytic"]["dimensions_m"][k] for k in ("radius","height","chamfer_size"))
        profile = recipe["steps"][1]["parameters"]
        expected = [[0,0],[radius,0],[radius,height-size],[radius-size,height],[0,height]]
        vertices = profile["vertices_m"]
        # Decimal metre values can differ by a rounding bit after subtraction.
        matches = len(vertices)==len(expected) and all(
            math.isclose(a,b,rel_tol=0,abs_tol=1e-15)
            for actual,target in zip(vertices,expected) for a,b in zip(actual,target))
        revolution = recipe["steps"][-1]["parameters"]
        if (profile["origin_m"] != [0,0,0] or not matches or
                revolution["profiles"] != [recipe["steps"][1]["id"]] or
                revolution["angle_rad"] != 2*math.pi):
            raise CorpusError("chamfer profile differs from analytic geometry")
    if kind == "fillet_cylinder":
        if [s["operation"] for s in recipe["steps"]] != ["create_part","sketch_circle","extrude","fillet"]:
            raise CorpusError("fillet cylinder requires one base extrusion followed by one native fillet")
        circle,extrusion,fillet = (s["parameters"] for s in recipe["steps"][1:])
        values = recipe["analytic"]["dimensions_m"]
        if circle["radius_m"] != values["radius"] or circle["center_m"] != [0,0,0] or extrusion["height_m"] != values["height"] or extrusion["direction"] != [0,0,1] or extrusion["operation"] != "new_body" or extrusion["profiles"] != [recipe["steps"][1]["id"]]:
            raise CorpusError("fillet cylinder base differs from analytic dimensions")
        selector = fillet["edge_selector"]
        if fillet["radius_m"] != values["fillet_radius"] or selector["center_m"] != [0,0,values["height"]] or selector["radius_m"] != values["radius"]:
            raise CorpusError("fillet radius or selected circular rim differs from analytic geometry")
    analytic_measures(recipe)
    return recipe


def check_native(manifest, native, recipe):
    for key in ("configuration", "document_revision"):
        if native[key] != manifest[key]:
            raise CorpusError(f"native {key} differs from manifest")
    keys = [body["key"] for body in native["bodies"]]
    if len(keys) != len(set(keys)):
        raise CorpusError("duplicate native body key")
    if not recipe:
        return
    tolerance = manifest["tolerances"]
    def compare(measurements,targets):
        for quantity,target in targets.items():
            if quantity=="centroid_m":
                if quantity not in measurements or math.dist(measurements[quantity],target)>tolerance["length_absolute_m"]:
                    raise CorpusError("native analytic centroid mismatch")
                continue
            absolute = tolerance["volume_absolute_m3" if quantity=="volume_m3" else "area_absolute_m2"]
            if quantity not in measurements or not math.isclose(measurements[quantity],target,
                    rel_tol=tolerance["measure_relative"],abs_tol=absolute):
                raise CorpusError(f"native analytic mismatch: {quantity}, expected {target}")
    if recipe["analytic"]["shape"]=="multiple_solids":
        expected = multiple_solid_measures(recipe)
        if set(keys)!=set(expected) or any(b["kind"]!="solid" for b in native["bodies"]):
            raise CorpusError("multiple solids require both named solid bodies")
        for body in native["bodies"]:
            compare(body["measurements_si"],expected[body["key"]])
        if "document_measurements_si" not in native:
            raise CorpusError("multiple solids require document measures")
        compare(native["document_measurements_si"],aggregate_measures(expected.values()))
        if "selection" not in manifest:
            raise CorpusError("multiple solids require explicit body selections")
    else:
        if len(native["bodies"])!=1 or native["bodies"][0]["kind"]!="solid":
            raise CorpusError("analytic starter recipes require exactly one solid body")
        compare(native["bodies"][0]["measurements_si"],analytic_measures(recipe))
    if "selection" in manifest:
        selected_bodies(manifest["selection"],native)


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
