# SPDX-License-Identifier: MIT
# Copyright (c) 2026 openswx contributors
"""Original crossed-cylinder benchmark: binding success is not STEP success."""
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'verification/cross-bore-001'
sys.path.insert(0, str(ROOT / 'tools'))
try:
    from step_check import read_step, measure
    from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_BSplineCurve, GeomAbs_Cylinder, GeomAbs_Plane
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE
    from OCP.TopExp import TopExp
    from OCP.TopTools import TopTools_IndexedMapOfShape
    from OCP.TopoDS import TopoDS
    HAVE_OCP = True
except ModuleNotFoundError:
    HAVE_OCP = False


def expected():
    return json.loads((DATA / 'expected.json').read_text())


def analytic_measures(steps):
    # Independent integration of two perpendicular cylinder equations in mm.
    # x=r*sin(t) removes endpoint square-root singularities in the bore volume.
    outer, bore, height = 26, 4, 20
    def integral(f):
        h = math.pi / (2 * steps)
        return h / 3 * math.fsum(
            (1 if i in (0, steps) else 4 if i % 2 else 2) * f(i * h)
            for i in range(steps + 1))
    def root(t):
        return math.sqrt(outer**2 - bore**2 * math.sin(t)**2)
    removed = 8 * bore**2 * integral(lambda t: math.cos(t)**2 * root(t))
    removed_area = 8 * outer * bore**2 * integral(
        lambda t: math.cos(t)**2 / root(t))
    bore_area = 8 * bore * integral(root)
    return (math.pi * outer**2 * height - removed,
            2 * math.pi * outer * height + 2 * math.pi * outer**2 -
            removed_area + bore_area)


class CrossBoreEvidenceTest(unittest.TestCase):
    def test_original_capture_and_receipts(self):
        manifest = json.loads((DATA / 'manifest.json').read_text())
        self.assertEqual(manifest['origin'], 'original_synthetic')
        self.assertEqual(manifest['license'], 'MIT')
        for a in manifest['artifacts']:
            self.assertEqual(Path(a['path']).name, a['path'])
            data = (DATA / a['path']).read_bytes()
            self.assertEqual(len(data), a['bytes'])
            self.assertEqual(hashlib.sha256(data).hexdigest(), a['sha256'])
        receipts = json.loads((DATA / 'receipts.json').read_text())
        for role, ext in [('source', 'sldprt'), ('step', 'step'),
                          ('parasolid_binary', 'x_b')]:
            data = (DATA / ('cross-bore.' + ext)).read_bytes()
            self.assertEqual(len(data), receipts[role]['byte_length'])
            self.assertEqual(hashlib.sha256(data).hexdigest(), receipts[role]['sha256'])
        capture = json.loads((DATA / 'capture.json').read_text())
        self.assertTrue(capture['documents_closed'])
        self.assertFalse(capture['authentication_headers_recorded'])
        events = {e['label']: e for e in capture['events']}
        self.assertEqual(events['close']['response']['result']['structuredContent']
                         ['result']['status'], 'completed')
        self.assertEqual(events['reclose']['response']['result']['structuredContent']
                         ['result']['status'], 'completed')
        for scope in ('document', 'configuration'):
            self.assertEqual(events['properties-' + scope]['response']['result']
                             ['structuredContent']['result']['properties'], [])
        self.assertEqual(events['cross-bore']['request']['params']['arguments']
                         ['params']['feature']['operation'], 'cut')

    def test_binding_and_native_topology_are_distinct_from_export_support(self):
        exp = expected()
        source = json.loads((DATA / 'source-inspection.json').read_text())
        self.assertTrue(source['complete'])
        self.assertTrue(source['model']['typed_geometry_complete'])
        self.assertEqual(source['body_geometry']['counts'], exp['source_counts'])
        self.assertEqual(source['model']['geometry_counts'], exp['source_geometry'])
        native = json.loads((DATA / 'brep.json').read_text())
        counts = {kind: sum(e['kind'] == kind for e in native['entities'])
                  for kind in ('body', 'face', 'edge', 'loop', 'vertex')}
        self.assertEqual(counts, {'body': 1, 'face': 4, 'edge': 4,
                                  'loop': 8, 'vertex': 0})
        error = json.loads((DATA / 'export-error.json').read_text())
        self.assertEqual(error['error_code'], 'unsupported_format')
        self.assertEqual(error['message'], exp['current_step_message'])
        self.assertFalse(exp['partial_output_created'])

    def test_independent_geometric_integrals_converge(self):
        a, b = analytic_measures(4096), analytic_measures(8192)
        for first, second in zip(a, b):
            self.assertAlmostEqual(first, second, places=9)
        self.assertAlmostEqual(b[0], expected()['independent_volume_mm3'], places=9)
        self.assertAlmostEqual(b[1], expected()['independent_area_mm2'], places=9)

    @unittest.skipUnless(os.environ.get('OPENSWX_CORPUS_BUILD'), 'reader build not configured')
    def test_live_reader_binds_saved_source(self):
        build = Path(os.environ['OPENSWX_CORPUS_BUILD']).absolute()
        exp = expected()
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([str(build / 'asmbox/swx_dump'),
                '--extract-parasolid', directory, str(DATA / 'cross-bore.sldprt')],
                capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            payloads = json.loads(result.stdout)['payloads']
            payload = next(p for p in payloads if p['category'] == 'partitions')
            result = subprocess.run([str(build / 'libopenparasolid/parasolid_inspect'),
                '--geometry', '--body-geometry', '2', '--binding-tolerance', '1e-8',
                '--intersection-chart-tolerance', '1e-7',
                '--intersection-solve-tolerance', '1e-9',
                str(Path(directory) / payload['file'])], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report['body_geometry']['counts'], exp['source_counts'])
            self.assertEqual(report['model']['geometry_counts'], exp['source_geometry'])

    @unittest.skipUnless(os.environ.get('OPENSWX_CORPUS_EXPORTER'), 'STEP driver not configured')
    def test_live_export_remains_explicitly_unsupported_without_partial_output(self):
        exporter = str(Path(os.environ['OPENSWX_CORPUS_EXPORTER']).absolute())
        env = {**os.environ, 'OPENSWX_CORPUS_INTERSECTION_CHART_TOLERANCE': '1e-7',
               'OPENSWX_CORPUS_INTERSECTION_SOLVE_TOLERANCE': '1e-9'}
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'preview.step'
            args = [exporter, str(DATA / 'cross-bore.sldprt'), '0', '2', str(target)]
            result = subprocess.run(args, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertEqual(json.loads(result.stdout)['message'],
                             expected()['current_step_message'])
            self.assertFalse(target.exists())
            env['OPENSWX_CORPUS_INTERSECTION_SOLVE_TOLERANCE'] = 'nan'
            result = subprocess.run(args, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertFalse(target.exists())

    @unittest.skipUnless(HAVE_OCP, 'optional cadquery-ocp is not installed')
    def test_native_step_preserves_supports_but_approximates_intersection_edges(self):
        shape, counts = read_step(DATA / 'cross-bore.step')
        exp = expected()
        self.assertEqual(counts, exp['native_step_counts'])
        cylinders, planes = [], 0
        faces = TopTools_IndexedMapOfShape()
        TopExp.MapShapes_s(shape, TopAbs_FACE, faces)
        for i in range(1, faces.Extent() + 1):
            surface = BRepAdaptor_Surface(TopoDS.Face_s(faces.FindKey(i)))
            if surface.GetType() == GeomAbs_Cylinder:
                cylinders.append(surface.Cylinder())
            else:
                self.assertEqual(surface.GetType(), GeomAbs_Plane)
                planes += 1
        self.assertEqual(planes, 2)
        self.assertEqual(sorted(round(c.Radius(), 10) for c in cylinders), [4, 26])
        self.assertAlmostEqual(cylinders[0].Axis().Direction().Dot(
            cylinders[1].Axis().Direction()), 0, places=12)
        edges = TopTools_IndexedMapOfShape()
        TopExp.MapShapes_s(shape, TopAbs_EDGE, edges)
        splines = []
        for i in range(1, edges.Extent() + 1):
            curve = BRepAdaptor_Curve(TopoDS.Edge_s(edges.FindKey(i)))
            if curve.GetType() == GeomAbs_BSplineCurve:
                spline = curve.BSpline()
                splines.append((spline.Degree(), spline.NbPoles(), spline.IsRational()))
        # Two linear importer-created cylinder seams and two native cubic
        # approximations of the non-circular intersection branches.
        self.assertEqual(sorted(splines), [(1, 2, False)] * 2 + [(3, 65, False)] * 2)
        volume, area = measure(shape, True), measure(shape, False)
        self.assertTrue(math.isclose(volume, exp['native_step_volume_mm3'], rel_tol=1e-11))
        self.assertTrue(math.isclose(area, exp['native_step_area_mm2'], rel_tol=1e-11))
        exact_volume, exact_area = analytic_measures(8192)
        # This is the frozen native export's observed approximation, not an
        # increased reader/exporter length tolerance or a curve certificate.
        self.assertGreater(abs(volume - exact_volume), .001)
        self.assertLess(abs(volume - exact_volume), .01)
        self.assertLess(abs(area - exact_area), .001)


if __name__ == '__main__':
    unittest.main()
