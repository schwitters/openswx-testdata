# SPDX-License-Identifier: MIT
# Copyright (c) 2026 openswx contributors
"""Native meridian sectors and an independent equivalent-pole sphere reference."""
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
DATA = ROOT / 'verification/analytic-cuts-001'
sys.path.insert(0, str(ROOT / 'tools'))
try:
    from step_check import read_step, measure, compare_solids
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
    from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_Circle, GeomAbs_Sphere
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopoDS import TopoDS
    HAVE_OCP = True
except ModuleNotFoundError:
    HAVE_OCP = False


def load(name):
    return json.loads((DATA / (name + '.json')).read_text())


def cases():
    return load('expected')['cases']


class NativeAnalyticCutsTest(unittest.TestCase):
    def test_original_artifacts_and_native_receipts_match(self):
        manifest = load('manifest')
        self.assertEqual(manifest['origin'], 'original_synthetic')
        self.assertEqual(manifest['license'], 'MIT')
        for artifact in manifest['artifacts']:
            path = artifact['path']
            self.assertEqual(Path(path).name, path)
            data = (DATA / path).read_bytes()
            self.assertEqual(len(data), artifact['bytes'])
            self.assertEqual(hashlib.sha256(data).hexdigest(), artifact['sha256'])
        receipts = load('receipts')
        for c in cases():
            for role in ('source', 'step', 'parasolid_binary', 'parasolid_text'):
                data = (DATA / c[role]).read_bytes()
                receipt = receipts[c['name']][role]
                self.assertEqual(len(data), receipt['byte_length'])
                self.assertEqual(hashlib.sha256(data).hexdigest(), receipt['sha256'])
                self.assertTrue(receipt['native_returned_success'])
                self.assertEqual(receipt['native_errors'], 0)

    def test_capture_has_original_construction_empty_properties_and_closed_documents(self):
        capture = load('capture')
        self.assertFalse(capture['authentication_headers_recorded'])
        self.assertTrue(capture['documents_closed'])
        opened, closed, properties, construction = set(), set(), 0, []
        for e in capture['events']:
            tool = e['request']['params']['name']
            args = e['request']['params']['arguments']
            result = e['response'].get('result', {}).get('structuredContent', {}).get('result', {})
            if tool == 'sw.document.new' and result:
                opened.add(result['document'])
            if tool == 'sw.document.close' and result.get('status') == 'completed':
                closed.add(args['document'])
            if tool == 'sw.properties.get' and result:
                self.assertEqual(result['properties'], [])
                properties += 1
            if tool == 'sw.feature.create':
                construction.append(args['params']['feature'])
        self.assertEqual(len(opened), 3)
        self.assertEqual(opened, closed)
        self.assertEqual(properties, 6)
        angles = sorted(f['angle'] for f in construction if f['type'] == 'revolve')
        self.assertEqual(angles, [math.pi/2, 3*math.pi/2])
        self.assertEqual(sum(f['type'] == 'surface' for f in construction), 1)

    def test_saved_source_topology_and_historical_failures(self):
        for c in cases():
            source = load('source-inspection')[c['name']]
            self.assertTrue(source['complete'])
            self.assertTrue(source['model']['typed_geometry_complete'])
            self.assertEqual(source['body_geometry']['counts'], c['source_counts'])
            before = load('baseline-errors')[c['name']]
            if c['name'] == 'sphere':
                self.assertEqual(before['exit_code'], 0)
                self.assertEqual(source['model']['missing_reference_count'], 13)
            else:
                self.assertEqual(before['exit_code'], 2)
                self.assertFalse(before['output_created'])
                self.assertIn('Torus cut circle is tilted', before['stderr'])
                self.assertEqual(source['model']['missing_reference_count'], 0)
                torus, = (g for g in source['model']['geometry'] if g['kind'] == 'torus')
                self.assertEqual(torus['major_radius'], .020)
                self.assertEqual(torus['minor_radius'], .004)
                circles = [g for g in source['model']['geometry'] if g['kind'] == 'circle']
                self.assertEqual(len(circles), 2)
                for circle in circles:
                    self.assertEqual(circle['radius'], .004)
                    self.assertAlmostEqual(sum(a*b for a, b in zip(circle['normal'], torus['axis'])),
                                           0, places=12)

    def sphere_supports(self, shape, c):
        face = TopoDS.Face_s(TopExp_Explorer(shape, TopAbs_FACE).Current())
        surface = BRepAdaptor_Surface(face)
        self.assertEqual(surface.GetType(), GeomAbs_Sphere)
        sphere = surface.Sphere()
        self.assertAlmostEqual(sphere.Radius(), c['radius_mm'], places=9)
        for actual, expected in zip(sphere.Location().Coord(), c['center_mm']):
            self.assertAlmostEqual(actual, expected, places=9)
        curves = TopExp_Explorer(shape, TopAbs_EDGE)
        circles = 0
        while curves.More():
            curve = BRepAdaptor_Curve(TopoDS.Edge_s(curves.Current()))
            if curve.GetType() == GeomAbs_Circle:
                circles += 1
                circle = curve.Circle()
                self.assertAlmostEqual(circle.Radius(), 4, places=9)
                for i, value in enumerate(circle.Location().Coord()):
                    self.assertAlmostEqual(value, c['center_mm'][i] +
                                           c['cut_height_mm']*c['cut_axis'][i], places=9)
                direction = circle.Axis().Direction().Coord()
                self.assertAlmostEqual(abs(sum(a*b for a, b in zip(direction, c['cut_axis']))),
                                       1, places=9)
            curves.Next()
        self.assertEqual(circles, 1)

    def compare(self, path, c):
        native, _ = read_step(DATA / c['step'])
        shape, counts = read_step(path)
        self.assertEqual(counts, c['step_counts'])
        if c['name'] == 'sphere':
            self.sphere_supports(shape, c)
            self.assertLess(abs(measure(shape, False) - c['area_mm2']), 1e-6)
            for first, second in ((native, shape), (shape, native)):
                cut = BRepAlgoAPI_Cut(first, second)
                self.assertTrue(cut.IsDone())
                self.assertLess(abs(measure(cut.Shape(), False)), 1e-6)
        else:
            r, major, angle = c['minor_radius_mm'], c['major_radius_mm'], c['azimuth_radians']
            self.assertLess(abs(measure(shape, True) - math.pi*r*r*major*angle), 1e-6)
            self.assertLess(abs(measure(shape, False) - (2*math.pi*major*r*angle + 2*math.pi*r*r)), 1e-6)
            self.assertEqual(compare_solids(native, shape), [0, 0])

    @unittest.skipUnless(HAVE_OCP, 'optional cadquery-ocp is not installed')
    def test_native_reference_supports_topology_and_analytic_measures(self):
        for c in cases():
            shape, counts = read_step(DATA/c['step'])
            self.assertEqual(counts, c.get('native_step_counts', c['step_counts']))
            if c['name'] == 'sphere':
                self.sphere_supports(shape, c)
                actual = measure(shape, False)
                observed = load('occt')['sphere']['native_area_mm2']
                self.assertLess(abs(actual-observed), 1e-6)
                self.assertLess(abs(actual-c['area_mm2']), .002)
            else:
                self.compare(DATA/c['step'], c)

    @unittest.skipUnless(os.environ.get('OPENSWX_CORPUS_BUILD') and
                         os.environ.get('OPENSWX_CORPUS_EXPORTER'), 'library drivers not configured')
    def test_live_native_body_exports(self):
        exporter = str(Path(os.environ['OPENSWX_CORPUS_EXPORTER']).absolute())
        build = Path(os.environ['OPENSWX_CORPUS_BUILD']).absolute()
        for c in cases():
            with self.subTest(case=c['name']), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'export.step'
                run = subprocess.run([exporter, str(DATA/c['source']), str(c['payload']),
                                      str(c['body']), str(path)], capture_output=True, text=True)
                self.assertEqual(run.returncode, 0, run.stdout+run.stderr)
                self.assertEqual(json.loads(run.stdout), c['step_statistics'])
                extracted = Path(directory) / 'payloads'
                run = subprocess.run([str(build/'asmbox/swx_dump'), '--extract-parasolid',
                                      str(extracted), str(DATA/c['source'])], capture_output=True, text=True)
                self.assertEqual(run.returncode, 0, run.stderr)
                payload = next(p for p in json.loads(run.stdout)['payloads'] if p['index'] == c['payload'])
                run = subprocess.run([str(build/'libopenparasolid/parasolid_inspect'),
                    '--geometry', '--body-geometry', str(c['body']), '--binding-tolerance', '1e-8',
                    str(extracted/payload['file'])], capture_output=True, text=True)
                self.assertEqual(run.returncode, 2 if c['name'] == 'sphere' else 0, run.stderr)
                report = json.loads(run.stdout)
                self.assertTrue(report['complete'])
                self.assertTrue(report['model']['typed_geometry_complete'])
                self.assertEqual(report['body_geometry']['counts'], c['source_counts'])
                self.assertEqual(report['model']['missing_reference_count'],
                                 13 if c['name'] == 'sphere' else 0)
                if HAVE_OCP:
                    self.compare(path, c)

    @unittest.skipUnless(HAVE_OCP and os.environ.get('OPENSWX_CORPUS_ROUNDTRIP_FIXTURES'),
                         'OCP and equivalent-frame fixture generator not configured')
    def test_equivalent_source_frames_match_native_references(self):
        generator = str(Path(os.environ['OPENSWX_CORPUS_ROUNDTRIP_FIXTURES']).absolute())
        with tempfile.TemporaryDirectory() as directory:
            run = subprocess.run([generator, directory], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stdout+run.stderr)
            for c in cases():
                with self.subTest(case=c['name']):
                    self.compare(Path(directory)/(c['fixture']+'.step'), c)


if __name__ == '__main__':
    unittest.main()
