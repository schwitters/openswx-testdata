# SPDX-License-Identifier: MIT
# Copyright (c) 2026 openswx contributors
"""Original rational multi-span partial-trim and exact STEP regression."""
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
DATA = ROOT / 'verification/rational-spans-001'
sys.path.insert(0, str(ROOT / 'tools'))
try:
    from step_check import read_step, measure, compare_solids
    HAVE_OCP = True
except ModuleNotFoundError:
    HAVE_OCP = False


def load(name):
    return json.loads((DATA / (name + '.json')).read_text())


# Independent Cox-de Boor basis and analytic rational derivative from the recipe.
import math
KNOTS = [0,0,0,0,.4,1,1,1,1]
POINTS = [(0,0),(2,0),(5,1),(9,4),(12,9)]
WEIGHTS = [1,.8,1.3,.9,1.1]
def profile(t):
    def basis(i,p):
        if p==0:
            return float(KNOTS[i]<=t<KNOTS[i+1] or (t==1 and KNOTS[i]<1 and KNOTS[i+1]==1))
        left=KNOTS[i+p]-KNOTS[i]
        right=KNOTS[i+p+1]-KNOTS[i+1]
        return ((t-KNOTS[i])/left*basis(i,p-1) if left else 0)+((KNOTS[i+p+1]-t)/right*basis(i+1,p-1) if right else 0)
    def derivative(i):
        a=KNOTS[i+3]-KNOTS[i];b=KNOTS[i+4]-KNOTS[i+1]
        return (3/a*basis(i,2) if a else 0)-(3/b*basis(i+1,2) if b else 0)
    n=[basis(i,3)*w for i,w in enumerate(WEIGHTS)]
    d=[derivative(i)*w for i,w in enumerate(WEIGHTS)]
    w=math.fsum(n);dw=math.fsum(d)
    x,y=[math.fsum(n[i]*POINTS[i][k] for i in range(5)) for k in (0,1)]
    dx,dy=[math.fsum(d[i]*POINTS[i][k] for i in range(5)) for k in (0,1)]
    return x/w,y/w,(dx*w-x*dw)/(w*w),(dy*w-y*dw)/(w*w)
def cut_parameter():
    lo,hi=0.,1.
    for _ in range(64):
        mid=(lo+hi)/2
        if profile(mid)[0]<3:lo=mid
        else:hi=mid
    return (lo+hi)/2
def analytic_measures():
    first=cut_parameter(); area=0.;length=0.
    for a,b in [(first,.4),(.4,1.)]:
        n=4096;h=(b-a)/n;areas=[];lengths=[]
        for i in range(n+1):
            x,y,dx,dy=profile(a+i*h)
            c=1 if i in (0,n) else 4 if i%2 else 2
            areas.append(c*(9-y)*dx);lengths.append(c*math.hypot(dx,dy))
        area+=h/3*math.fsum(areas);length+=h/3*math.fsum(lengths)
    return {'volume_mm3':area*8,'area_mm2':2*area+(9+9-profile(first)[1]+length)*8,'cut_parameter':first}


class RationalSpansTest(unittest.TestCase):
    def test_original_capture_integrity_and_closure(self):
        manifest = load('manifest')
        self.assertEqual(manifest['origin'], 'original_synthetic')
        self.assertEqual(manifest['license'], 'MIT')
        for a in manifest['artifacts']:
            self.assertEqual(Path(a['path']).name, a['path'])
            data = (DATA / a['path']).read_bytes()
            self.assertEqual(len(data), a['bytes'])
            self.assertEqual(hashlib.sha256(data).hexdigest(), a['sha256'])
        for role, ext in [('source','sldprt'), ('step','step'),
                          ('parasolid_binary','x_b'), ('parasolid_text','x_t')]:
            data = (DATA / ('spans.' + ext)).read_bytes()
            receipt = load('receipts')[role]
            self.assertEqual(len(data), receipt['byte_length'])
            self.assertEqual(hashlib.sha256(data).hexdigest(), receipt['sha256'])
            self.assertTrue(receipt['native_returned_success'])
        for scope in ['document','configuration']:
            self.assertEqual(load('properties-' + scope)['result']['structuredContent']['result']['properties'], [])
        closes = [e for e in load('journal') if e['request']['params']['name'] == 'sw.document.close']
        self.assertEqual(len(closes), 1)
        self.assertFalse(closes[0]['response']['result']['isError'])
        closed = closes[0]['response']['result']['structuredContent']['result']
        self.assertEqual(closed['status'], 'completed')
        self.assertTrue(closed['readback']['closed'])
        native = load('brep')['result']['structuredContent']['result']['entities']
        counts = Counter(e['kind'] for e in native)
        for kind, count in [('body', 1), ('face', 5), ('edge', 9), ('vertex', 6)]:
            self.assertEqual(counts[kind], count)
        self.assertEqual(next(e['body_kind'] for e in native if e['kind']=='body'), 'solid')
        self.assertFalse(load('expected')['baseline']['output_created'])
        self.assertIn('certified monotone projection', load('expected')['baseline']['error']['message'])

    def test_independent_piecewise_oracle(self):
        actual = analytic_measures()
        for name, value in load('expected')['oracle'].items():
            self.assertAlmostEqual(actual[name], value, delta=1e-9)
        self.assertLess(actual['cut_parameter'], .4)
        self.assertAlmostEqual(profile(actual['cut_parameter'])[0], 3, delta=1e-12)
        recipe = load('recipe')['profile']['entities'][0]
        self.assertEqual(recipe['degree'], 3)
        self.assertEqual(recipe['knots'], KNOTS)
        self.assertEqual(recipe['weights'], WEIGHTS)
        for a,b in zip(recipe['control_points'], POINTS):
            self.assertAlmostEqual(a[0]*1000,b[0],delta=1e-12)
            self.assertAlmostEqual(a[1]*1000,b[1],delta=1e-12)

    @unittest.skipUnless(HAVE_OCP, 'OCP required')
    def test_native_solid_matches_oracle(self):
        shape, counts = read_step(DATA / 'spans.step')
        self.assertEqual(counts, load('expected')['step_counts'])
        oracle = analytic_measures()
        self.assertAlmostEqual(measure(shape, True), oracle['volume_mm3'], delta=1e-6)
        self.assertAlmostEqual(measure(shape, False), oracle['area_mm2'], delta=1e-6)

    @unittest.skipUnless(os.environ.get('OPENSWX_CORPUS_BUILD') and
                         os.environ.get('OPENSWX_CORPUS_EXPORTER'), 'library drivers required')
    def test_live_partial_binding_and_complete_step(self):
        build = Path(os.environ['OPENSWX_CORPUS_BUILD']).absolute()
        exporter = str(Path(os.environ['OPENSWX_CORPUS_EXPORTER']).absolute())
        with tempfile.TemporaryDirectory() as directory:
            extracted = Path(directory) / 'payloads'
            run = subprocess.run([str(build/'asmbox/swx_dump'), '--extract-parasolid',
                                  str(extracted), str(DATA/'spans.sldprt')], capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr)
            payload = next(p for p in json.loads(run.stdout)['payloads'] if p['index']==0)
            self.assertEqual(payload['configuration_name'], 'Default')
            run = subprocess.run([str(build/'libopenparasolid/parasolid_inspect'), '--geometry',
                                  '--body-geometry','2','--binding-tolerance','1e-8',str(extracted/payload['file'])],
                                 capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stdout+run.stderr)
            report = json.loads(run.stdout)
            self.assertTrue(report['complete'])
            self.assertEqual(report['diagnostics'], [])
            self.assertEqual(report['model']['issues'], [])
            self.assertEqual(report['body_geometry']['counts'], load('expected')['body_geometry_counts'])
            curves = [g for g in report['model']['geometry'] if g['kind']=='nurbs_curve']
            self.assertEqual(len(curves),2)
            ids = {g['source'] for g in curves}
            for g in curves:
                self.assertEqual(g['axis']['knots'], [0,.4,1])
                self.assertEqual(g['axis']['multiplicities'], [4,1,4])
                self.assertEqual(g['axis']['degree'],3)
                self.assertEqual(g['axis']['control_count'],5)
                self.assertTrue(g['controls']['rational'])
                controls = g['controls']['values']
                self.assertEqual(controls[3::4], WEIGHTS)
                for i, ((x,y), w) in enumerate(zip(POINTS, WEIGHTS)):
                    self.assertAlmostEqual(controls[4*i], x*w/1000, delta=1e-17)
                    self.assertAlmostEqual(controls[4*i+1], y*w/1000, delta=1e-17)
            edges = [fin for f in report['body_geometry']['faces'] for loop in f['loops']
                     for fin in loop['fins'] if fin['curve'] in ids]
            self.assertEqual(len(edges),4)
            for fin in edges:
                self.assertAlmostEqual(min(fin['start'],fin['end']),cut_parameter(),delta=1e-12)
                self.assertEqual(max(fin['start'],fin['end']),1)
            target = Path(directory)/'output.step'
            run = subprocess.run([exporter,str(DATA/'spans.sldprt'),'0','2',str(target)],capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stdout+run.stderr)
            self.assertEqual(json.loads(run.stdout),load('expected')['step_statistics'])
            self.assertIn('RATIONAL_B_SPLINE_SURFACE',target.read_text())
            if HAVE_OCP:
                native,_=read_step(DATA/'spans.step')
                current,counts=read_step(target)
                self.assertEqual(counts,load('expected')['step_counts'])
                self.assertEqual(compare_solids(native,current),[0,0])
                oracle=analytic_measures()
                self.assertAlmostEqual(measure(current,True),oracle['volume_mm3'],delta=1e-6)
                self.assertAlmostEqual(measure(current,False),oracle['area_mm2'],delta=1e-6)


if __name__ == '__main__':
    unittest.main()
