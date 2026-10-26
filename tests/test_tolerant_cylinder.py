# SPDX-License-Identifier: MIT
# Copyright (c) 2026 openswx contributors
"""Independent native carrier reference for a certified tolerant arc."""
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
DATA = ROOT / 'verification/tolerant-cylinder-001'
sys.path.insert(0, str(ROOT / 'tools'))
try:
    from step_check import read_step, measure
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Section
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.GCPnts import GCPnts_AbscissaPoint
    from OCP.TopAbs import TopAbs_EDGE
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopoDS import TopoDS
    from OCP.gp import gp_Pln, gp_Pnt, gp_Dir
    HAVE_OCP = True
except ModuleNotFoundError:
    HAVE_OCP = False


def edge_length(shape):
    explorer = TopExp_Explorer(shape, TopAbs_EDGE)
    lengths = []
    while explorer.More():
        curve = BRepAdaptor_Curve(TopoDS.Edge_s(explorer.Current()))
        lengths.append(GCPnts_AbscissaPoint.Length_s(curve, 1e-10))
        explorer.Next()
    return math.fsum(lengths)


class TolerantCylinderTest(unittest.TestCase):
    def test_capture_integrity(self):
        manifest = json.loads((DATA / 'manifest.json').read_text())
        self.assertEqual(manifest['origin'], 'original_synthetic')
        self.assertEqual(manifest['license'], 'MIT')
        for artifact in manifest['artifacts']:
            self.assertEqual(Path(artifact['path']).name, artifact['path'])
            data = (DATA / artifact['path']).read_bytes()
            self.assertEqual(len(data), artifact['bytes'])
            self.assertEqual(hashlib.sha256(data).hexdigest(), artifact['sha256'])
        receipts = json.loads((DATA / 'receipts.json').read_text())
        for role, ext in [('source', 'sldprt'), ('step', 'step'),
                          ('parasolid_binary', 'x_b'), ('parasolid_text', 'x_t')]:
            data = (DATA / ('carrier.' + ext)).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), receipts[role]['sha256'])

    def test_owned_document_closed_and_properties_empty(self):
        def result(response):
            return response['result']['structuredContent']['result']
        for scope in ['document', 'configuration']:
            response = json.loads((DATA / ('properties-' + scope + '.json')).read_text())
            self.assertEqual(result(response)['properties'], [])
        journal = json.loads((DATA / 'journal.json').read_text())
        closes = [entry for entry in journal
                  if entry['request']['params']['name'] == 'sw.document.close']
        self.assertEqual(len(closes), 1)
        self.assertFalse(closes[0]['response']['result']['isError'])

    @unittest.skipUnless(os.environ.get('OPENSWX_CORPUS_BUILD'), 'library build required')
    def test_original_native_source_binding(self):
        build = Path(os.environ['OPENSWX_CORPUS_BUILD']).absolute()
        expected = json.loads((DATA / 'expected.json').read_text())
        with tempfile.TemporaryDirectory() as directory:
            extracted = Path(directory) / 'payloads'
            run = subprocess.run([str(build / 'asmbox/swx_dump'), '--extract-parasolid',
                                  str(extracted), str(DATA / 'carrier.sldprt')],
                                 capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            payload = next(p for p in json.loads(run.stdout)['payloads']
                           if p['index'] == expected['payload_index'])
            run = subprocess.run([str(build / 'libopenparasolid/parasolid_inspect'),
                                  '--geometry', '--body-geometry', '1',
                                  '--binding-tolerance', '1e-8', str(extracted / payload['file'])],
                                 capture_output=True, text=True)
            self.assertEqual(run.returncode, 2, run.stdout + run.stderr)
            report = json.loads(run.stdout)
            self.assertTrue(report['complete'])
            self.assertEqual(report['diagnostics'], [])
            self.assertEqual(report['body_geometry']['counts'], expected['body_geometry_counts'])
            model = report['model']
            self.assertEqual(model['geometry_counts'], expected['model_geometry_counts'])
            self.assertEqual(model['invalid_geometry_count'], 0)
            self.assertEqual(model['unsupported_geometry_count'], 0)
            self.assertEqual(len(model['issues']), expected['missing_next_targets'])
            self.assertTrue(all(i['code'] == 'missing_target' and i['field'] == 'next'
                                for i in model['issues']))

    @unittest.skipUnless(HAVE_OCP, 'OCP required')
    def test_native_section_and_recovered_arc(self):
        native, counts = read_step(DATA / 'carrier.step')
        self.assertEqual(counts['faces'], 1)
        self.assertAlmostEqual(measure(native, False), 100 * math.pi, delta=1e-7)
        section = BRepAlgoAPI_Section(native, gp_Pln(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), False)
        section.Build()
        self.assertTrue(section.IsDone())
        self.assertAlmostEqual(edge_length(section.Shape()), 5 * math.pi, delta=2e-6)  # OCC section approximation, in mm.
        executable = os.environ.get('OPENSWX_CORPUS_TOLERANT_FIXTURES')
        if not executable:
            self.skipTest('OPENSWX_CORPUS_TOLERANT_FIXTURES required for live recovery')
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'recovered.step'
            subprocess.run([executable, str(output)], check=True, capture_output=True, text=True)
            wire, _ = read_step(output)
            def theta(v):
                w = math.sqrt(.5)
                return math.atan2(2*w*v*(1-v)+v*v, (1-v)**2+2*w*v*(1-v))
            self.assertAlmostEqual(edge_length(wire), 10*(theta(.5)-theta(.45)), delta=1e-9)
            # Every recovered point must lie on the independent native sheet.
            from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
            explorer = TopExp_Explorer(wire, TopAbs_EDGE)
            self.assertTrue(explorer.More())
            curve = BRepAdaptor_Curve(TopoDS.Edge_s(explorer.Current()))
            for i in range(33):
                t = curve.FirstParameter() + (curve.LastParameter()-curve.FirstParameter())*i/32
                vertex = BRepBuilderAPI_MakeVertex(curve.Value(t)).Vertex()
                distance = BRepExtrema_DistShapeShape(vertex, native)
                self.assertTrue(distance.IsDone())
                self.assertLess(distance.Value(), 1e-8)


if __name__ == '__main__':
    unittest.main()
