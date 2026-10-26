# SPDX-License-Identifier: MIT
# Copyright (c) 2026 openswx contributors
"""Exact polynomial plane/swept graph, distinct from the approximate native STEP."""
from collections import Counter
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
DATA = ROOT / 'verification/slanted-sweep-001'
sys.path.insert(0, str(ROOT / 'tools'))
try:
    from step_check import read_step, measure
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
    from OCP.GeomAbs import GeomAbs_BSplineCurve
    from OCP.TopAbs import TopAbs_EDGE
    from OCP.TopExp import TopExp
    from OCP.TopTools import TopTools_IndexedMapOfShape
    from OCP.TopoDS import TopoDS
    HAVE_OCP = True
except ModuleNotFoundError:
    HAVE_OCP = False


def load(name):
    return json.loads((DATA / (name + '.json')).read_text())


def analytic_measures():
    # X=12t, Y=9t^3, H=8+3t; material lies below Y=9 and above the profile.
    # Integrating H dA gives 108*(8+3/2-8/4-3/5)=745.2 exactly.
    intervals = 16384
    h = 1 / intervals
    mantle = h / 3 * math.fsum(
        (1 if i in (0, intervals) else 4 if i % 2 else 2)
        * (8 + 3*i*h) * math.hypot(12, 27*(i*h)**2)
        for i in range(intervals + 1))
    return {'volume_mm3': 745.2,
            'area_mm2': 81 + 81*math.sqrt(17)/4 + 114 + 72 + mantle}


def upper_curves(shape):
    edges = TopTools_IndexedMapOfShape()
    TopExp.MapShapes_s(shape, TopAbs_EDGE, edges)
    result = []
    for index in range(1, edges.Extent() + 1):
        curve = BRepAdaptor_Curve(TopoDS.Edge_s(edges.FindKey(index)))
        if curve.GetType() != GeomAbs_BSplineCurve:
            continue
        first, last = curve.FirstParameter(), curve.LastParameter()
        if min(curve.Value(first).Z(), curve.Value(last).Z()) <= 1:
            continue
        residuals = []
        for i in range(257):
            point = curve.Value(first + (last-first)*i/256)
            t = point.X()/12
            residuals.append(math.hypot(point.Y()-9*t**3, point.Z()-(8+3*t)))
        spline = curve.BSpline()
        result.append({'controls': curve.NbPoles(), 'degree': curve.Degree(),
                       'maximum_sampled_equation_residual_mm': max(residuals),
                       'poles': [(spline.Pole(i).X(), spline.Pole(i).Y(), spline.Pole(i).Z())
                                 for i in range(1, spline.NbPoles()+1)]})
    return result


class SlantedSweepTest(unittest.TestCase):
    def test_original_capture_integrity_and_owned_document_closure(self):
        manifest = load('manifest')
        self.assertEqual(manifest['origin'], 'original_synthetic')
        self.assertEqual(manifest['license'], 'MIT')
        for artifact in manifest['artifacts']:
            self.assertEqual(Path(artifact['path']).name, artifact['path'])
            data = (DATA / artifact['path']).read_bytes()
            self.assertEqual(len(data), artifact['bytes'])
            self.assertEqual(hashlib.sha256(data).hexdigest(), artifact['sha256'])
        for role, extension in [('source', 'sldprt'), ('step', 'step'),
                                ('parasolid_binary', 'x_b'), ('parasolid_text', 'x_t')]:
            data = (DATA / ('strip.' + extension)).read_bytes()
            receipt = load('receipts')[role]
            self.assertEqual(len(data), receipt['byte_length'])
            self.assertEqual(hashlib.sha256(data).hexdigest(), receipt['sha256'])
        for scope in ['document', 'configuration']:
            properties = load('properties-' + scope)['result']['structuredContent']['result']
            self.assertEqual(properties['properties'], [])
        completed_closes = []
        created_document = None
        for entry in load('journal'):
            name = entry['request']['params']['name']
            response = entry['response']['result']['structuredContent']
            if 'error' in response:
                self.assertIn(response['error']['code'], [-32304, -32306])
                self.assertIs(response['error']['data']['outcome_unknown'], False)
                continue
            result = response['result']
            if name == 'sw.document.new':
                created_document = result['document']
            if name == 'sw.document.close':
                self.assertEqual(result['status'], 'completed')
                self.assertTrue(result['readback']['closed'])
                completed_closes.append(result['document'])
        self.assertEqual(completed_closes, [created_document])
        entities = load('brep')['result']['structuredContent']['result']['entities']
        counts = Counter(entity['kind'] for entity in entities)
        for kind, count in [('body', 1), ('face', 5), ('edge', 9), ('vertex', 6)]:
            self.assertEqual(counts[kind], count)
        self.assertFalse(load('expected')['baseline']['output_created'])

    def test_recipe_and_independent_measures(self):
        profile = load('recipe')['profile']['entities'][0]
        self.assertEqual(profile['degree'], 3)
        self.assertEqual(profile['control_points'], [[0, 0], [.004, 0], [.008, 0], [.012, .009]])
        self.assertNotIn('weights', profile)
        for name, value in analytic_measures().items():
            self.assertAlmostEqual(value, load('expected')['oracle'][name], delta=1e-10)

    @unittest.skipUnless(HAVE_OCP, 'OCP required')
    def test_native_approximation_is_recorded_separately(self):
        native, counts = read_step(DATA / 'strip.step')
        observed = load('occt')
        self.assertEqual(counts, load('expected')['step_counts'])
        self.assertAlmostEqual(measure(native, True), observed['native_volume_mm3'], delta=1e-6)
        self.assertAlmostEqual(measure(native, False), observed['native_area_mm2'], delta=1e-6)
        self.assertGreater(abs(measure(native, True)-745.2), 1e-5)
        curves = upper_curves(native)
        self.assertEqual(len(curves), 1)
        self.assertEqual(curves[0]['controls'], 22)
        self.assertGreater(curves[0]['maximum_sampled_equation_residual_mm'], .0001)
        self.assertLess(curves[0]['maximum_sampled_equation_residual_mm'], .0003)

    @unittest.skipUnless(os.environ.get('OPENSWX_CORPUS_BUILD') and
                         os.environ.get('OPENSWX_CORPUS_EXPORTER'), 'library drivers required')
    def test_live_graph_binding_and_complete_export(self):
        build = Path(os.environ['OPENSWX_CORPUS_BUILD']).absolute()
        exporter = str(Path(os.environ['OPENSWX_CORPUS_EXPORTER']).absolute())
        with tempfile.TemporaryDirectory() as directory:
            extracted = Path(directory) / 'payloads'
            run = subprocess.run([str(build/'asmbox/swx_dump'), '--extract-parasolid',
                                  str(extracted), str(DATA/'strip.sldprt')], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            payload = next(p for p in json.loads(run.stdout)['payloads'] if p['index'] == 0)
            self.assertEqual(payload['configuration_name'], 'Default')
            run = subprocess.run([str(build/'libopenparasolid/parasolid_inspect'), '--geometry',
                                  '--body-geometry', '2', '--binding-tolerance', '1e-8',
                                  '--intersection-chart-tolerance', '1e-7',
                                  '--intersection-solve-tolerance', '1e-9', str(extracted/payload['file'])],
                                 capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stdout+run.stderr)
            report = json.loads(run.stdout)
            self.assertEqual(report['body_geometry']['counts'], load('expected')['body_geometry_counts'])
            geometry = {g['source']: g for g in report['model']['geometry']}
            intersections = [g for g in geometry.values() if g['kind'] == 'intersection_curve']
            self.assertEqual(len(intersections), 1)
            graph = intersections[0]
            self.assertEqual({geometry[i]['kind'] for i in graph['surfaces']}, {'plane', 'swept_surface'})
            uses = [fin for face in report['body_geometry']['faces'] for loop in face['loops']
                    for fin in loop['fins'] if fin['curve'] == graph['source']]
            self.assertEqual(len(uses), 2)
            self.assertTrue(all(fin['fin_curve'] == 0 for fin in uses))
            self.assertEqual(uses[0]['start'], uses[1]['end'])
            self.assertEqual(uses[0]['end'], uses[1]['start'])
            target = Path(directory) / 'output.step'
            env = os.environ | {'OPENSWX_CORPUS_INTERSECTION_CHART_TOLERANCE': '1e-7',
                                'OPENSWX_CORPUS_INTERSECTION_SOLVE_TOLERANCE': '1e-9'}
            run = subprocess.run([exporter, str(DATA/'strip.sldprt'), '0', '2', str(target)],
                                 env=env, capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stdout+run.stderr)
            self.assertEqual(json.loads(run.stdout), load('expected')['step_statistics'])
            if HAVE_OCP:
                current, counts = read_step(target)
                self.assertEqual(counts, load('expected')['step_counts'])
                oracle = analytic_measures()
                self.assertAlmostEqual(measure(current, True), oracle['volume_mm3'], delta=1e-6)
                self.assertAlmostEqual(measure(current, False), oracle['area_mm2'], delta=1e-6)
                curves = upper_curves(current)
                self.assertEqual(len(curves), 1)
                self.assertEqual(curves[0]['degree'], 3)
                expected = [(0, 0, 8), (4, 0, 9), (8, 0, 10), (12, 9, 11)]
                self.assertEqual(len(curves[0]['poles']), 4)
                for actual, point in zip(curves[0]['poles'], expected):
                    for a, b in zip(actual, point):
                        self.assertAlmostEqual(a, b, delta=1e-10)
                native, _ = read_step(DATA/'strip.step')
                # The native curve is approximate: Boolean output is diagnostic,
                # while exact coefficients and recipe integrals define acceptance.
                for a, b in [(native, current), (current, native)]:
                    difference = BRepAlgoAPI_Cut(a, b)
                    self.assertTrue(difference.IsDone())
                    self.assertTrue(math.isfinite(measure(difference.Shape(), True)))


if __name__ == '__main__':
    unittest.main()
