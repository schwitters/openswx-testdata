# SPDX-License-Identifier: MIT
# Copyright (c) 2026 openswx contributors
"""Original native prisms with edge vertices inside retained spline domains."""
from fractions import Fraction
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
DATA = ROOT / 'verification/spline-trim-001'
sys.path.insert(0, str(ROOT / 'tools'))
try:
    from step_check import read_step, measure, compare_solids
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.GeomAbs import GeomAbs_BSplineCurve
    from OCP.TopAbs import TopAbs_EDGE
    from OCP.TopExp import TopExp
    from OCP.TopTools import TopTools_IndexedMapOfShape
    from OCP.TopoDS import TopoDS
    HAVE_OCP = True
except ModuleNotFoundError:
    HAVE_OCP = False


def cases():
    return json.loads((DATA / 'expected.json').read_text())['cases']


def polynomial(values, t):
    return sum(v * t**i for i, v in enumerate(values))


def analytic(case):
    x, y = case['x_polynomial_mm'], case['y_polynomial_mm']
    cut = Fraction(case['cut_parameter_fraction'])
    section = Fraction(0)
    for i, xi in enumerate(x[1:], 1):
        for j, yi in enumerate([case['top_mm']] + [-v for v in y[1:]]):
            power = i + j
            section += Fraction(i * xi * yi, power) * (1 - cut**power)
    def speed(t):
        dx = sum(i * v * t**(i-1) for i, v in enumerate(x) if i)
        dy = sum(i * v * t**(i-1) for i, v in enumerate(y) if i)
        return math.hypot(dx, dy)
    n = 8192
    h = (1 - float(cut)) / n
    length = h / 3 * math.fsum(
        (1 if i in (0, n) else 4 if i % 2 else 2) * speed(float(cut) + i*h)
        for i in range(n+1))
    perimeter = (polynomial(x, 1) - polynomial(x, float(cut)) +
                 case['top_mm'] - polynomial(y, float(cut)) + length)
    return (section * case['depth_mm'],
            2 * float(section) + case['depth_mm'] * perimeter)


class NativeSplineTrimTest(unittest.TestCase):
    def test_original_artifacts_match_manifest_and_native_receipts(self):
        manifest = json.loads((DATA / 'manifest.json').read_text())
        self.assertEqual(manifest['origin'], 'original_synthetic')
        self.assertEqual(manifest['license'], 'MIT')
        for a in manifest['artifacts']:
            self.assertEqual(Path(a['path']).name, a['path'])
            b = (DATA / a['path']).read_bytes()
            self.assertEqual(len(b), a['bytes'])
            self.assertEqual(hashlib.sha256(b).hexdigest(), a['sha256'])
        receipts = json.loads((DATA / 'receipts.json').read_text())
        for c in cases():
            for field, role in [('source', 'source'), ('step', 'step'),
                                ('parasolid_binary', 'parasolid_binary'),
                                ('parasolid_text', 'parasolid_text')]:
                b = (DATA / c[field]).read_bytes()
                self.assertEqual(len(b), receipts[c['name']][role]['byte_length'])
                self.assertEqual(hashlib.sha256(b).hexdigest(),
                                 receipts[c['name']][role]['sha256'])

    def test_original_construction_closes_owned_documents_and_has_empty_properties(self):
        capture = json.loads((DATA / 'capture.json').read_text())
        self.assertTrue(capture['documents_closed'])
        self.assertFalse(capture['authentication_headers_recorded'])
        events = {e['label']: e for e in capture['events']}
        opened, closed = set(), set()
        for e in capture['events']:
            tool = e['request']['params']['name']
            response = e['response'].get('result', {}).get('structuredContent', {}).get('result', {})
            if tool in ('sw.document.new', 'sw.document.open') and response:
                document = response.get('document', response.get('doc_id'))
                self.assertTrue(document)
                opened.add(document)
            if tool == 'sw.document.close' and response.get('status') == 'completed':
                closed.add(e['request']['params']['arguments']['document'])
        self.assertEqual(len(opened), 4)
        self.assertEqual(opened, closed)
        for c in cases():
            prefix = c['name'] + '-'
            profile = events[prefix+'profile']['request']['params']['arguments']['params']['sketch']
            self.assertEqual(profile['entities'][0]['control_points'], c['profile_controls_m'])
            cut = events[prefix+'trim']['request']['params']['arguments']['params']['feature']
            self.assertEqual(cut['operation'], 'cut')
            self.assertEqual(cut['end_condition']['kind'], 'through_all')
            for scope in ('document', 'configuration'):
                self.assertEqual(events[prefix+'properties-'+scope]['response']['result']
                                 ['structuredContent']['result']['properties'], [])
            self.assertEqual(events[prefix+'close']['response']['result']
                             ['structuredContent']['result']['status'], 'completed')

    def test_source_domains_retain_original_controls_and_partial_edge_intervals(self):
        reports = json.loads((DATA / 'source-inspection.json').read_text())
        baseline = json.loads((DATA / 'baseline-errors.json').read_text())
        for c in cases():
            report = reports[c['name']]
            self.assertTrue(report['complete'])
            self.assertTrue(report['model']['typed_geometry_complete'])
            self.assertEqual(report['body_geometry']['counts'], c['source_counts'])
            geometry = {g['source']: g for g in report['model']['geometry']}
            profiles = []
            for face in report['body_geometry']['faces']:
                for loop in face['loops']:
                    for fin in loop['fins']:
                        curve = geometry[fin['curve']]
                        if curve['kind'] != 'nurbs_curve':
                            continue
                        profiles.append(curve)
                        self.assertEqual(curve['axis']['knots'], [0, 1])
                        self.assertEqual(curve['axis']['degree'], 3)
                        self.assertEqual(curve['axis']['control_count'], 4)
                        self.assertFalse(curve['controls']['rational'])
                        lo, hi = sorted((fin['start'], fin['end']))
                        self.assertAlmostEqual(lo, c['expected_recovered_parameter'], places=12)
                        self.assertLess(abs(lo-c['cut_parameter']), 1e-8)
                        self.assertEqual(hi, 1)
                        values = curve['controls']['values']
                        for i, xy in enumerate(c['profile_controls_m']):
                            self.assertAlmostEqual(values[3*i], xy[0], places=12)
                            self.assertAlmostEqual(values[3*i+1], xy[1], places=12)
            self.assertEqual(len(profiles), 4)
            failure = baseline[c['name']]
            self.assertEqual(failure['exit_code'], 2)
            self.assertFalse(failure['partial_output_created'])
            self.assertIn('Spline domain endpoints need unambiguous', failure['error']['message'])

    def test_independent_polynomials_certify_volume_and_positive_derivative(self):
        for c in cases():
            volume, _ = analytic(c)
            self.assertEqual(str(volume), c['volume_fraction_mm3'])
        # For the second profile, projected derivative Bernstein coefficients
        # are [720,-30,810]; its quadratic minimum is nevertheless positive.
        a, b, constant = Fraction(1590), Fraction(-1500), Fraction(720)
        self.assertGreater(constant - b*b/(4*a), 0)
        self.assertEqual(3*(-1*20 + 1*10), -30)

    @unittest.skipUnless(os.environ.get('OPENSWX_CORPUS_BUILD'), 'reader not configured')
    def test_text_references_are_an_explicit_remaining_format_boundary(self):
        build = Path(os.environ['OPENSWX_CORPUS_BUILD']).absolute()
        for c in cases():
            data = (DATA / c['parasolid_text']).read_bytes()
            self.assertIn(b'PARASOLID', data[:256])
            data.decode('ascii')
            result = subprocess.run([str(build/'libopenparasolid/parasolid_inspect'),
                str(DATA/c['parasolid_text'])], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Expected an extracted binary Parasolid', result.stderr)

    @unittest.skipUnless(HAVE_OCP, 'optional cadquery-ocp is not installed')
    def test_native_reference_solids_match_independent_polynomial_oracles(self):
        for c in cases():
            shape, counts = read_step(DATA / c['step'])
            self.assertEqual(counts, c['step_counts'])
            volume, area = analytic(c)
            self.assertLess(abs(measure(shape, True) - float(volume)), 1e-6)
            self.assertLess(abs(measure(shape, False) - area), 1e-6)

    @unittest.skipUnless(os.environ.get('OPENSWX_CORPUS_BUILD') and
                         os.environ.get('OPENSWX_CORPUS_EXPORTER'), 'library drivers not configured')
    def test_live_binding_and_complete_step_export(self):
        build = Path(os.environ['OPENSWX_CORPUS_BUILD']).absolute()
        exporter = str(Path(os.environ['OPENSWX_CORPUS_EXPORTER']).absolute())
        for c in cases():
            with self.subTest(case=c['name']), tempfile.TemporaryDirectory() as directory:
                target = Path(directory) / 'export.step'
                result = subprocess.run([exporter, str(DATA / c['source']), '0', '2', str(target)],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(json.loads(result.stdout), c['step_statistics'])
                extract = Path(directory) / 'payloads'
                result = subprocess.run([str(build/'asmbox/swx_dump'), '--extract-parasolid',
                    str(extract), str(DATA/c['source'])], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                payload = next(p for p in json.loads(result.stdout)['payloads']
                               if p['category'] == 'partitions')
                result = subprocess.run([str(build/'libopenparasolid/parasolid_inspect'),
                    '--body-geometry', '2', '--binding-tolerance', '1e-8', str(extract/payload['file'])],
                    capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)['body_geometry']['counts'], c['source_counts'])
                if not HAVE_OCP:
                    continue
                native, _ = read_step(DATA/c['step'])
                shape, counts = read_step(target)
                self.assertEqual(counts, c['step_counts'])
                self.assertEqual(compare_solids(native, shape), [0, 0])
                volume, area = analytic(c)
                self.assertLess(abs(measure(shape, True) - float(volume)), 1e-6)
                self.assertLess(abs(measure(shape, False) - area), 1e-6)
                edges = TopTools_IndexedMapOfShape()
                TopExp.MapShapes_s(shape, TopAbs_EDGE, edges)
                profiles = 0
                for i in range(1, edges.Extent()+1):
                    curve = BRepAdaptor_Curve(TopoDS.Edge_s(edges.FindKey(i)))
                    if curve.GetType() != GeomAbs_BSplineCurve:
                        continue
                    profiles += 1
                    self.assertEqual(curve.BSpline().Degree(), 3)
                    self.assertFalse(curve.BSpline().IsRational())
                    self.assertAlmostEqual(curve.FirstParameter(), c['expected_recovered_parameter'], places=12)
                    self.assertAlmostEqual(curve.LastParameter(), 1, places=10)
                    for u in (curve.FirstParameter(), (curve.FirstParameter()+1)/2, 1):
                        p = curve.Value(u)
                        self.assertAlmostEqual(p.X(), polynomial(c['x_polynomial_mm'], u), places=7)
                        self.assertAlmostEqual(p.Y(), polynomial(c['y_polynomial_mm'], u), places=7)
                        self.assertLess(min(abs(p.Z()), abs(p.Z()-8)), 1e-7)
                self.assertEqual(profiles, 2)


if __name__ == '__main__':
    unittest.main()
