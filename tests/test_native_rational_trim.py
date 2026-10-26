# SPDX-License-Identifier: MIT
# Copyright (c) 2026 openswx contributors
"""Original rational partial-domain coupon; binding and STEP scope are separate."""
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
DATA = ROOT / 'verification/rational-trim-001'
sys.path.insert(0, str(ROOT/'tools'))
try:
    from step_check import read_step, measure
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.GeomAbs import GeomAbs_BSplineCurve
    from OCP.TopAbs import TopAbs_EDGE
    from OCP.TopExp import TopExp
    from OCP.TopTools import TopTools_IndexedMapOfShape
    from OCP.TopoDS import TopoDS
    HAVE_OCP = True
except ModuleNotFoundError:
    HAVE_OCP = False


def load(name):
    return json.loads((DATA/(name+'.json')).read_text())


def profile(u):
    w = 1-.75*u+2.25*u*u-1.5*u**3
    dw = -.75+4.5*u-4.5*u*u
    x, y = 9*u+12*u*u-9*u**3, 9*u**3
    dx, dy = 9+24*u-27*u*u, 27*u*u
    return x/w, y/w, (dx*w-x*dw)/(w*w), (dy*w-y*dw)/(w*w)


def cut_parameter():
    lo, hi = 0., 1.
    for _ in range(64):
        mid = (lo+hi)/2
        if profile(mid)[0] < 5:
            lo = mid
        else:
            hi = mid
    return (lo+hi)/2


def analytic_measures():
    start, n = cut_parameter(), 8192
    h = (1-start)/n
    section, length = [], []
    for i in range(n+1):
        x, y, dx, dy = profile(start+h*i)
        coefficient = 1 if i in (0, n) else 4 if i % 2 else 2
        section.append(coefficient*(9-y)*dx)
        length.append(coefficient*math.hypot(dx, dy))
    area = h/3*math.fsum(section)
    perimeter = 7+9-profile(start)[1]+h/3*math.fsum(length)
    return area*8, 2*area+perimeter*8


class NativeRationalTrimTest(unittest.TestCase):
    def test_original_artifacts_receipts_and_capture_provenance(self):
        manifest = load('manifest')
        self.assertEqual(manifest['origin'], 'original_synthetic')
        self.assertEqual(manifest['license'], 'MIT')
        for artifact in manifest['artifacts']:
            self.assertEqual(Path(artifact['path']).name, artifact['path'])
            data = (DATA/artifact['path']).read_bytes()
            self.assertEqual(len(data), artifact['bytes'])
            self.assertEqual(hashlib.sha256(data).hexdigest(), artifact['sha256'])
        for role, ext in [('source','sldprt'), ('step','step'),
                          ('parasolid_binary','x_b'), ('parasolid_text','x_t')]:
            receipt = load('receipts')[role]
            data = (DATA/('rational.'+ext)).read_bytes()
            self.assertEqual(len(data), receipt['byte_length'])
            self.assertEqual(hashlib.sha256(data).hexdigest(), receipt['sha256'])
            self.assertTrue(receipt['native_returned_success'])
        opened, closed, properties = set(), set(), 0
        capture = load('capture')
        self.assertFalse(capture['authentication_headers_recorded'])
        for event in capture['events']:
            tool = event['request']['params']['name']
            args = event['request']['params']['arguments']
            result = event['response'].get('result',{}).get('structuredContent',{}).get('result',{})
            if tool == 'sw.document.new' and result:
                opened.add(result['document'])
            if tool == 'sw.document.close' and result.get('status') == 'completed':
                closed.add(args['document'])
            if tool == 'sw.properties.get' and result:
                self.assertEqual(result['properties'], [])
                properties += 1
            if tool == 'sw.sketch.create' and event['label'] == 'profile':
                spline = args['params']['sketch']['entities'][0]
                self.assertEqual(spline['weights'], load('expected')['weights'])
                self.assertEqual(spline['control_points'], [[0,0],[.004,0],[.008,0],[.012,.009]])
        self.assertEqual(len(opened), 1)
        self.assertEqual(opened, closed)
        self.assertEqual(properties, 2)

    def test_current_export_contract_keeps_original_native_artifacts(self):
        current = ROOT/'verification/rational-sweep-001'
        manifest = json.loads((current/'manifest.json').read_text())
        for artifact in manifest['artifacts']:
            data=(current/artifact['path']).read_bytes()
            self.assertEqual(len(data),artifact['bytes'])
            self.assertEqual(hashlib.sha256(data).hexdigest(),artifact['sha256'])
        expected=json.loads((current/'expected.json').read_text())
        self.assertTrue(expected['step_supported'])
        self.assertEqual(hashlib.sha256((DATA/'rational.sldprt').read_bytes()).hexdigest(),expected['source_sha256'])
        self.assertEqual(hashlib.sha256((DATA/'rational.step').read_bytes()).hexdigest(),expected['native_reference_sha256'])

    def check_binding(self, report):
        self.assertTrue(report['complete'])
        self.assertTrue(report['model']['typed_geometry_complete'])
        self.assertEqual(report['body_geometry']['counts'], load('expected')['source_counts'])
        geometry = {g['source']:g for g in report['model']['geometry']}
        profiles = 0
        for face in report['body_geometry']['faces']:
            for loop in face['loops']:
                for fin in loop['fins']:
                    curve = geometry[fin['curve']]
                    if curve['kind'] != 'nurbs_curve':
                        continue
                    profiles += 1
                    self.assertTrue(curve['controls']['rational'])
                    self.assertEqual(curve['controls']['dimension'], 4)
                    self.assertEqual(curve['axis']['degree'], 3)
                    self.assertEqual(curve['axis']['knots'], [0,1])
                    self.assertEqual(curve['axis']['control_count'], 4)
                    values = curve['controls']['values']
                    scale = values[3]
                    for i, weight in enumerate(load('expected')['weights']):
                        self.assertAlmostEqual(values[4*i+3]/scale, weight, places=12)
                        for k in range(2):
                            self.assertAlmostEqual(1000*values[4*i+k]/values[4*i+3],
                                load('expected')['control_points_mm'][i][k], places=9)
                    self.assertAlmostEqual(min(fin['start'],fin['end']), cut_parameter(), places=10)
                    self.assertEqual(max(fin['start'],fin['end']), 1)
        self.assertEqual(profiles, 4)

    def test_frozen_complete_binding_advances_beyond_the_baseline_error(self):
        baseline = load('baseline-error')
        self.assertEqual(baseline['exit_code'], 2)
        self.assertFalse(baseline['output_created'])
        self.assertIn('Partial spline inversion requires open nonrational', baseline['stderr'])
        self.check_binding(load('source-inspection'))
        self.assertFalse(load('expected')['full_step_export_supported'])

    @unittest.skipUnless(HAVE_OCP, 'optional cadquery-ocp is not installed')
    def test_native_step_matches_independent_rational_geometry_and_integrals(self):
        shape, counts = read_step(DATA/'rational.step')
        self.assertEqual(counts, load('expected')['native_step_counts'])
        volume, area = analytic_measures()
        self.assertLess(abs(measure(shape,True)-volume), 1e-6)
        self.assertLess(abs(measure(shape,False)-area), 1e-6)
        edges = TopTools_IndexedMapOfShape()
        TopExp.MapShapes_s(shape, TopAbs_EDGE, edges)
        profiles = 0
        for i in range(1,edges.Extent()+1):
            curve = BRepAdaptor_Curve(TopoDS.Edge_s(edges.FindKey(i)))
            if curve.GetType() != GeomAbs_BSplineCurve:
                continue
            profiles += 1
            self.assertTrue(curve.BSpline().IsRational())
            self.assertEqual(curve.BSpline().Degree(), 3)
            self.assertAlmostEqual(curve.FirstParameter(), cut_parameter(), places=10)
            for u in (curve.FirstParameter(), .5, .75, 1):
                point = curve.Value(u)
                x,y,_,_ = profile(u)
                self.assertAlmostEqual(point.X(), x, places=8)
                self.assertAlmostEqual(point.Y(), y, places=8)
                self.assertLess(min(abs(point.Z()),abs(point.Z()-8)),1e-8)
        self.assertEqual(profiles, 2)

    @unittest.skipUnless(os.environ.get('OPENSWX_CORPUS_BUILD') and
                         os.environ.get('OPENSWX_CORPUS_EXPORTER'), 'library drivers not configured')
    def test_live_complete_binding_and_rational_sweep_export(self):
        build = Path(os.environ['OPENSWX_CORPUS_BUILD']).absolute()
        exporter = str(Path(os.environ['OPENSWX_CORPUS_EXPORTER']).absolute())
        with tempfile.TemporaryDirectory() as directory:
            extracted = Path(directory)/'payloads'
            run = subprocess.run([str(build/'asmbox/swx_dump'),'--extract-parasolid',
                                  str(extracted),str(DATA/'rational.sldprt')],capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr)
            payload = next(p for p in json.loads(run.stdout)['payloads'] if p['index']==0)
            run = subprocess.run([str(build/'libopenparasolid/parasolid_inspect'),'--geometry',
                '--body-geometry','2','--binding-tolerance','1e-8',str(extracted/payload['file'])],
                capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr)
            self.check_binding(json.loads(run.stdout))
            target = Path(directory)/'output.step'
            run = subprocess.run([exporter,str(DATA/'rational.sldprt'),'0','2',str(target)],
                                 capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stdout+run.stderr)
            current = json.loads((ROOT/'verification/rational-sweep-001/expected.json').read_text())
            self.assertEqual(json.loads(run.stdout), current['step_statistics'])
            self.assertIn('RATIONAL_B_SPLINE_SURFACE', target.read_text())
            if HAVE_OCP:
                from step_check import compare_solids
                native, _ = read_step(DATA/'rational.step')
                exported, counts = read_step(target)
                self.assertEqual(counts,current['step_counts'])
                self.assertEqual(compare_solids(native,exported),[0,0])
                volume,area = analytic_measures()
                self.assertLess(abs(measure(exported,True)-volume),1e-6)
                self.assertLess(abs(measure(exported,False)-area),1e-6)


if __name__ == '__main__':
    unittest.main()
