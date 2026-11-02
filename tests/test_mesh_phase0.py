"""Independent small numerical oracles; no real section or historical code."""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import h5py
import numpy as np
from numpy.testing import assert_allclose, assert_array_equal
from scipy import sparse
from scipy.integrate import quad
from scipy.special import gamma

from bsfm.mesh import artifacts, continuum, coordinates, derivatives, fem, geometry
from bsfm.mesh import inputs, marginal, phase0, probes, projectors, resources, spectral, support
from bsfm.mesh.identities import REPO, file_record, logical, ordered_ids, read_json, sha, write_json

ENV = Path(os.environ.get('BSFM_MESH_ENVIRONMENT', str(REPO.parent/'BSFM_ENVIRONMENTS/mesh-phase0-20261031')))
CONFIG = read_json(REPO/'config/mesh/phase0-harness.json')


def fixture():
    grid=np.linspace(0,1,17)
    xy=np.array([(x,y) for x in grid for y in grid],dtype='float64')
    # Duplicate and near-coincident observations retain different identities.
    xy[-2]=xy[20];xy[-3]=xy[21]+1e-13
    raw=xy*coordinates.SCALE+np.array([100.,200.])
    rows=np.arange(len(raw),dtype='int64')*2
    ids=np.array([f'cell-{i:04d}' for i in rows]);types=np.arange(len(raw))%3
    idx=np.lexsort((rows,types)).astype('int64')
    return dict(all_xy=raw,model_xy=raw[idx],all_rows=rows,model_rows=rows[idx],
        all_ids=ids,model_ids=ids[idx],model_index=idx,types=types[idx],axis_order=np.array(['center_y','center_x']))


def study_fixture():
    study=copy.deepcopy(read_json(REPO/'config/mesh/study-design.json'))
    study['factors']['fine_collar']=.15
    study['factors']['inner_targets']=[dict(level='synthetic-h0',value=.35),dict(level='synthetic-h1',value=.22)]
    study['factors']['buffers']=[dict(level='synthetic-b0',value=.4),dict(level='synthetic-b1',value=.8)]
    study['factors']['ranges']=[dict(range_id=f's{i}',ell=e,role='synthetic_test') for i,e in enumerate([.3,1.,3.])]
    return study


def response_fixture(directory):
    data=fixture();path=Path(directory)/'response.h5'
    names={'all_xy':'/coordinates/all_source','model_xy':'/coordinates/model_source',
        'all_ids':'/axes/cells_all/ids','model_ids':'/axes/cells_model/ids',
        'all_rows':'/axes/cells_all/source_row','model_rows':'/axes/cells_model/source_row',
        'model_index':'/axes/cells_model/all_cell_index','types':'/metadata/model_type_code',
        'axis_order':'/axes/coordinates/labels'}
    records={}
    with h5py.File(path,'x') as f:
        for key,name in names.items():
            a=data[key]
            if a.dtype.kind=='U':
                f.create_dataset(name,data=a.astype(object),dtype=h5py.string_dtype('utf-8'))
                dtype='utf8';digest=ordered_ids(a)
            else:
                a=a.astype('<f8' if a.dtype.kind=='f' else '<i8');f.create_dataset(name,data=a)
                dtype='float64' if a.dtype.kind=='f' else 'int64';digest=hashlib.sha256(a.tobytes()).hexdigest()
            records[name]=dict(shape=list(a.shape),dtype=dtype,semantic_sha256=digest)
    manifest=dict(status='complete',section='SYNTHETIC',coordinates=dict(axis_order=['center_y','center_x'],units='source_native'),
        dimensions=dict(all_cells=289,model_cells=289),datasets=records,artifacts={'response.h5':dict(path='response.h5',**file_record(path))})
    return data,manifest


class NumericalTests(unittest.TestCase):
    def setUp(self):
        self.v=np.array([[0.,0.],[1.,0.],[0.,1.]])
        self.t=np.array([[0,1,2]],dtype='int64')

    def test_consistent_mass_and_stiffness_independent(self):
        m,g=fem.assemble(self.v,self.t)
        assert_allclose(m.toarray(),(np.ones((3,3))+np.eye(3))/24,atol=0,rtol=0)
        assert_allclose(g.toarray(),[[1,-.5,-.5],[-.5,.5,0],[-.5,0,.5]],atol=0,rtol=0)
        self.assertLess(max(fem.validate(self.v,self.t,m,g).values()),1e-15)

    def test_project_vertex_edge_interior_duplicate_nearby(self):
        xy=np.array([[0,0],[.5,0],[.2,.3],[.2,.3],[.2+1e-13,.3]])
        a=projectors.project(self.v,self.t,xy)
        assert_allclose(a.toarray(),np.c_[1-xy.sum(axis=1),xy],atol=1e-15)
        self.assertLessEqual(max(np.diff(a.indptr)),3)
        assert_allclose(a@self.v,xy,atol=1e-15)

    def test_outside_rejected(self):
        with self.assertRaises(ValueError):projectors.project(self.v,self.t,np.array([[1.,1.]]))

    def test_reversed_degenerate_and_one_based_rejected(self):
        for t in (self.t[:,[0,2,1]],np.array([[0,0,2]]),self.t+1,self.t.astype(float)):
            with self.subTest(t=t.tolist()),self.assertRaises(ValueError):geometry.triangles(self.v,t)

    def test_duplicate_triangles_rejected(self):
        with self.assertRaises(ValueError):geometry.triangles(self.v,np.vstack((self.t,self.t)))

    def test_canonical_vertex_triangle_order(self):
        v,t=geometry.canonicalize(self.v,self.t)
        order=np.array([2,0,1]);inv=np.argsort(order)
        v2,t2=geometry.canonicalize(self.v[order],inv[self.t][:,[0,2,1]])
        assert_array_equal(v,v2);assert_array_equal(t,t2)

    def test_full_spectrum_against_dense_precision_power(self):
        m,g=fem.assemble(self.v,self.t);md=m.toarray();gd=g.toarray()
        lam,u,report=spectral.spectrum(m,g)
        self.assertEqual(report['modes'],3);self.assertFalse(report['truncated'])
        for ell in [.15,.3,1.,3.,5.]:
            k2=40/ell**2;k=gd+k2*md;ki=np.linalg.inv(k)
            oracle=20*np.pi*k2**5*np.linalg.matrix_power(ki@md,5)@ki
            w,dw=spectral.modal(lam,ell);full=spectral.full_covariance(u,w)
            assert_allclose(full,oracle,rtol=2e-12,atol=2e-14)
            idx=np.array([0,2]);a=marginal.active_covariance(u,w,idx)
            assert_allclose(a,oracle[np.ix_(idx,idx)],rtol=2e-12,atol=2e-14)
            l,dl,ds=marginal.root_and_derivative(u,w,dw,idx)
            self.assertTrue(np.all(np.diag(l)>0));assert_array_equal(l,np.tril(l))
            assert_allclose(l@l.T,a,rtol=2e-14,atol=2e-14)
            assert_allclose(dl@l.T+l@dl.T,ds,rtol=2e-12,atol=2e-13)

    def test_derivatives_multiple_ranges_and_steps(self):
        m,g=fem.assemble(self.v,self.t);lam,u,_=spectral.spectrum(m,g)
        for ell in [.15,.3,1.,3.,5.]:
            result=derivatives.check(u,lam,np.array([0,2]),ell)
            self.assertLess(result['identity']['relative'],1e-12)
            self.assertEqual(len(result['finite_differences']),3)
            for row in result['finite_differences']:
                self.assertLess(row['covariance']['relative'],2e-5)
                self.assertLess(row['root']['relative'],2e-5)

    def test_matern_integral_oracle_and_limits(self):
        # Gamma mixture integral, independent of the implementation's Bessel call.
        for z in [0,1e-10,1e-4,.01,.5,1.,5.,15.]:
            oracle=quad(lambda t: t**4*np.exp(-t-z*z/(4*t))/gamma(5),0,np.inf,epsabs=2e-13,epsrel=2e-13)[0]
            actual=float(continuum.matern(z/np.sqrt(40),1))
            self.assertAlmostEqual(actual,oracle,places=12)
        self.assertEqual(float(continuum.matern(0,1)),1.)
        self.assertTrue(np.isfinite(continuum.matern([0,1e-300,1000],1)).all())
        with self.assertRaises(ValueError):continuum.matern([-1],1)

    def test_separated_clusters_connected_support_and_offsets(self):
        points=np.vstack((self.v,self.v+np.array([4.,0.])))
        h,c,o=support.enclosure(points,.2,.4,128)
        self.assertEqual(float(support.distance(np.array([[2.,.3]]),h)[0]),0.)
        self.assertLess(np.max(support.distance(points,c)),1e-12)
        self.assertGreater(o[:,0].max(),c[:,0].max())
        _,_,o2=support.enclosure(points,.2,.8,128)
        self.assertAlmostEqual(o2[:,0].max()-o[:,0].max(),.4,places=12)

    def test_edge_crossing_collar_min_distance(self):
        p=np.array([[0,0],[1,0],[1,1],[0,1]],float)
        assert_allclose(support.edge_distance(np.array([[-1,.5],[2,0]]),np.array([[2,.5],[2,1]]),p),[0,1],atol=1e-14)

    def test_grading_cap_and_candidate_grid(self):
        assert_allclose(support.target(np.array([0,1,10]),.1,.5),[.1,.25,.5])
        candidates=phase0.candidates(read_json(REPO/'config/mesh/study-design.json'))
        self.assertEqual(len(candidates),6)
        self.assertEqual(len(set(c['h'] for c in candidates)),3)
        self.assertEqual(len(set(c['buffer'] for c in candidates)),2)

    def test_changed_design_is_not_silently_ignored(self):
        study=read_json(REPO/'config/mesh/study-design.json');phase0.validate_design(study,CONFIG)
        study['target']['nu']=2
        with self.assertRaises(ValueError):phase0.validate_design(study,CONFIG)

    def test_authenticated_response_fixture_and_tampering(self):
        with tempfile.TemporaryDirectory() as d:
            data,manifest=response_fixture(d)
            loaded=inputs.load_bundle(d,manifest,expected_section='SYNTHETIC')
            for key in data:assert_array_equal(data[key],loaded[key])
            bad=copy.deepcopy(manifest);bad['coordinates']['units']='microns'
            with self.assertRaises(ValueError):inputs.load_bundle(d,bad)
            bad=copy.deepcopy(manifest);bad['datasets']['/coordinates/all_source']['semantic_sha256']='0'*64
            with self.assertRaises(ValueError):inputs.load_bundle(d,bad)
            with (Path(d)/'response.h5').open('ab') as f:f.write(b'x')
            with patch('bsfm.mesh.inputs.h5py.File') as opening:
                with self.assertRaises(ValueError):inputs.load_bundle(d,manifest)
                opening.assert_not_called()

    def test_missing_coordinate_metadata_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            _,manifest=response_fixture(d)
            with h5py.File(Path(d)/'response.h5','r+') as f:del f['/axes/coordinates/labels']
            manifest['artifacts']['response.h5'].update(file_record(Path(d)/'response.h5'))
            with self.assertRaises(KeyError):inputs.load_bundle(d,manifest)

    def test_git_dirty_run_refused(self):
        with patch('bsfm.mesh.inputs.subprocess.check_output',side_effect=['a'*40,'?? uncommitted.py']):
            with self.assertRaises(ValueError):inputs.code('a'*40,real=True)

    def test_failed_candidate_is_durable_and_no_automatic_fallback(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'failed'
            with patch('bsfm.mesh.phase0.supervised',side_effect=ValueError('deliberate resource exclusion')):
                with self.assertRaises(ValueError):phase0.run(fixture(),dict(code={},environment={}),ENV,root,study_fixture(),CONFIG,synthetic=True)
            self.assertFalse((root/'manifest.json').exists())
            failure=read_json(root/'failure.json');self.assertEqual(failure['status'],'failed')
            detail=read_json(Path(failure['attempt'])/'failure.json')
            self.assertTrue(detail['attempt_retained']);self.assertEqual(len(detail['not_run']),3)
            self.assertEqual(detail['completed_candidates'],[])

    def test_transform_and_identity_order(self):
        x=fixture();inputs.validate_population(x,dict(all_cells=289,model_cells=289))
        z,meta=coordinates.transform(x['all_xy'])
        assert_allclose(z*meta['scale']+meta['origin'],x['all_xy'],atol=1e-12)
        self.assertEqual(meta['axis_order'],['center_y','center_x'])
        for key in ['model_ids','model_rows','model_xy','types']:
            bad=copy.deepcopy(x);bad[key]=bad[key][::-1]
            with self.subTest(key=key),self.assertRaises(ValueError):inputs.validate_population(bad,dict(all_cells=289,model_cells=289))

    def test_fixed_probes_repeat_and_fill(self):
        x=fixture();z,_=coordinates.transform(x['all_xy']);xy=z[x['model_index']]
        a,one=probes.choose(xy,x['model_rows'],support.hull(z),CONFIG['probes'])
        b,two=probes.choose(xy,x['model_rows'],support.hull(z),CONFIG['probes'])
        assert_array_equal(a,b);self.assertEqual(one,two);self.assertEqual(len(set(a)),256)
        for name in ['boundary','interior','dense','sparse']:self.assertEqual(one['strata'].count(name),64)
        self.assertTrue(one['gap']['fixed_256_unchanged'])
        with self.assertRaises(ValueError):probes.choose(xy[:100],x['model_rows'][:100],support.hull(z),CONFIG['probes'])

    def test_sparse_roundtrip_and_index_corruption(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'tiny.h5';m,g=fem.assemble(self.v,self.t)
            artifacts.save_payload(path,dict(vertices=self.v,triangles=self.t),dict(mass=m,stiffness=g,projector=sparse.eye(3,format='csr')))
            arr,mat,hashes=artifacts.load_payload(path)
            assert_array_equal(arr['triangles'],self.t);assert_array_equal(mat['mass'].toarray(),m.toarray())
            self.assertEqual(hashes,artifacts.load_payload(path)[2])
            with h5py.File(path,'r+') as f:f['mass/indices'][0]=3
            with self.assertRaises(ValueError):artifacts.load_payload(path)

    def test_interrupted_attempt_is_not_complete(self):
        with tempfile.TemporaryDirectory() as d:
            attempt=artifacts.new_attempt(d,'candidate')
            write_json(attempt/'run-spec.json',dict(status='incomplete'))
            with self.assertRaises(ValueError):artifacts.validate_closed(attempt)
            (Path(d)/'candidate').mkdir()
            with self.assertRaises(ValueError):artifacts.new_attempt(d,'candidate')

    def test_headroom_rejection(self):
        with patch('bsfm.mesh.resources.psutil.virtual_memory') as vm:
            vm.return_value.available=7*resources.GiB
            with self.assertRaises(ValueError):resources.preflight()

    def test_memory_ceiling_terminates_worker_and_records_failure(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d)
            with self.assertRaises(ValueError):resources.supervised([sys.executable,'-B','-c','import time; time.sleep(20)'],REPO,os.environ.copy(),d/'log',d/'record.json',ceiling_GiB=.001,minimum_GiB=0,poll_seconds=.01)
            rec=read_json(d/'record.json');self.assertEqual(rec['reason'],'process_tree_memory_ceiling')
            self.assertGreater(rec['peak_process_tree_bytes'],1024**2)

    def test_process_tree_child_detection(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d)
            command=[sys.executable,'-B','-c',"import subprocess,sys; subprocess.run([sys.executable,'-B','-c','import time; time.sleep(.4)'])"]
            rec=resources.supervised(command,REPO,os.environ.copy(),d/'log',d/'record.json',minimum_GiB=0,poll_seconds=.01)
            self.assertEqual(rec['status'],'pass');self.assertGreaterEqual(rec['maximum_children'],2)


class TransportTests(unittest.TestCase):
    def test_hdf5_object_strings_through_runner_to_fresh_pickle_free_reader(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            _, manifest = response_fixture(directory)
            source = directory / 'response.h5'
            # Exercise UTF-8, variable lengths, combining characters and a
            # non-BMP code point, while preserving the canonical identity join.
            with h5py.File(source, 'r+') as f:
                ids = f['/axes/cells_all/ids'].asstr()[:]
                ids[:5] = ['cell-\u03b1', 'cell-\U0001f9ec', 'cell-e\u0301',
                           'cell-' + 'x' * 300, 'cell-\u00e9 ']
                model_ids = ids[f['/axes/cells_model/all_cell_index'][:]]
                for name, values in [('/axes/cells_all/ids', ids),
                                     ('/axes/cells_model/ids', model_ids)]:
                    f[name][:] = values
                    manifest['datasets'][name]['semantic_sha256'] = ordered_ids(values)
            manifest['artifacts']['response.h5'].update(file_record(source))
            data = inputs.load_bundle(directory, manifest, expected_section='SYNTHETIC')
            for name in ['all_ids', 'model_ids', 'axis_order']:
                self.assertEqual(data[name].dtype.kind, 'O')
            original = {name: value.copy() for name, value in data.items()}
            root = directory / 'transport-run'
            # Use the actual run/write boundary, stopping before geometry.
            with patch('bsfm.mesh.phase0.supervised', side_effect=ValueError('transport-only regression')):
                with self.assertRaisesRegex(ValueError, 'transport-only regression'):
                    phase0.run(data, dict(code={}, environment={}), ENV, root,
                               study_fixture(), CONFIG, synthetic=True)
            for name in data:
                assert_array_equal(data[name], original[name])
                self.assertEqual(data[name].dtype, original[name].dtype)
            reader = r'''
import hashlib, json, sys
import h5py
import numpy as np
names = {'all_ids':'/axes/cells_all/ids', 'model_ids':'/axes/cells_model/ids',
         'axis_order':'/axes/coordinates/labels', 'all_rows':'/axes/cells_all/source_row',
         'model_rows':'/axes/cells_model/source_row', 'model_index':'/axes/cells_model/all_cell_index',
         'types':'/metadata/model_type_code', 'all_xy':'/coordinates/all_source',
         'model_xy':'/coordinates/model_source'}
hashes = {}
with h5py.File(sys.argv[1], 'r') as source, np.load(sys.argv[2], allow_pickle=False) as transport:
    assert set(transport.files) == set(names)
    for name, dataset in names.items():
        actual = transport[name]
        assert not actual.dtype.hasobject, name
        if name in ('all_ids', 'model_ids', 'axis_order'):
            expected = source[dataset].asstr()[:]
            assert expected.dtype.kind == 'O' and actual.dtype.kind == 'U', name
            assert actual.ndim == 1 and actual.shape == expected.shape, name
            before = [value.encode('utf-8') for value in expected]
            after = [str(value).encode('utf-8') for value in actual]
            assert before == after, name
            digest = hashlib.sha256()
            for value in after:
                digest.update(len(value).to_bytes(8, 'little')); digest.update(value)
            hashes[name] = digest.hexdigest()
            if name != 'axis_order': assert len(set(actual.tolist())) == len(actual), name
        else:
            expected = source[dataset][:]
            assert actual.dtype == expected.dtype and actual.shape == expected.shape, name
            assert actual.tobytes(order='C') == expected.tobytes(order='C'), name
    assert transport['axis_order'].tolist() == ['center_y', 'center_x']
print(json.dumps(hashes))
'''
            result = subprocess.run([sys.executable, '-B', '-c', reader,
                                     str(source), str(root / 'inputs.npz')],
                                    capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(result.stdout), {
                name: ordered_ids(original[name]) for name in ['all_ids', 'model_ids', 'axis_order']})

    def assert_rejected_before_writing(self, name, values):
        data = fixture()
        data[name] = values
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'inputs.npz'
            with self.assertRaises(ValueError):
                phase0.write_transport(path, data)
            self.assertFalse(path.exists())

    def test_transport_rejects_non_one_dimensional_strings(self):
        for name in ['all_ids', 'model_ids', 'axis_order']:
            for values in [np.array('cell', dtype=object), np.array([['cell']], dtype=object)]:
                with self.subTest(name=name, shape=values.shape):
                    self.assert_rejected_before_writing(name, values)

    def test_transport_rejects_non_strings_without_coercion(self):
        for name in ['all_ids', 'model_ids', 'axis_order']:
            for invalid in [None, 1, 1.5, True, b'cell', np.bytes_('cell')]:
                with self.subTest(name=name, invalid=repr(invalid)):
                    self.assert_rejected_before_writing(name, ['cell', invalid])

    def test_transport_rejects_duplicate_identities(self):
        for name in ['all_ids', 'model_ids']:
            with self.subTest(name=name):
                self.assert_rejected_before_writing(name, np.array(['same', np.str_('same')], dtype=object))

    def test_transport_requires_exact_coordinate_axis_order(self):
        for values in [['center_x', 'center_y'], ['center_y'], ['center_y', 'center_x', 'z'],
                       ['center_y', 'center_x ']]:
            with self.subTest(values=values):
                self.assert_rejected_before_writing('axis_order', np.array(values, dtype=object))

    def test_transport_rejects_lossy_unicode_conversion(self):
        # NumPy fixed-width Unicode scalar extraction drops trailing NULs.
        for name in ['all_ids', 'model_ids']:
            with self.subTest(name=name):
                self.assert_rejected_before_writing(name, np.array(['cell\x00'], dtype=object))

    def test_transport_rejects_any_remaining_object_array(self):
        self.assert_rejected_before_writing('all_rows', np.array([1, 2], dtype=object))


@unittest.skipUnless(os.environ.get('BSFM_MESH_INTEGRATION')=='1','Set BSFM_MESH_INTEGRATION=1 for bounded R/fmesher integration')
class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(tempfile.mkdtemp(prefix='bsfm-phase0-review-'))
        print('Synthetic evidence retained: '+str(cls.root),flush=True)
        x=fixture();study=study_fixture();cfg=copy.deepcopy(CONFIG)
        # Synthetic geometries use the same bridge policy; reduced physical scales
        # are explicit fixture choices and never offered by the real CLI.
        chosen=phase0.candidates(study)
        provenance=dict(code=inputs.code(),environment=inputs.environment(ENV,full=False),fixture='deterministic-17x17-with-duplicate-locations')
        cls.first=phase0.run(x,provenance,ENV,cls.root/'first',study,cfg,synthetic=True,selected_candidates=[chosen[0]])
        cls.second=phase0.run(x,provenance,ENV,cls.root/'repeat',study,cfg,synthetic=True,selected_candidates=[chosen[0]])
        cls.bundle=cls.first/chosen[0]['id']
        cls.other=cls.second/chosen[0]['id']
        cls.extra=[]
        from bsfm.mesh.bridge import build
        z,_=coordinates.transform(x['all_xy'])
        for i,c in enumerate([chosen[1],chosen[2]]):
            geo=build(z,z[x['model_index']],ENV,cls.root/f'extra-geometry-{i}',c['h'],.15,c['buffer'],study['accuracy']['central99'][1]/4,cfg['geometry'])
            cls.extra.append(geo['geometry'])
        write_json(cls.root/'additional-geometries.json',cls.extra)

    def test_closed_bundle(self):
        self.assertEqual(artifacts.validate_closed(self.bundle)['status'],'pass')

    def test_fresh_worker_semantic_determinism(self):
        self.assertEqual(read_json(self.bundle/'manifest.json')['logical_hashes'],read_json(self.other/'manifest.json')['logical_hashes'])
        a=read_json(self.bundle/'ranges.json');b=read_json(self.other/'ranges.json')
        self.assertEqual([r['logical_hashes'] for r in a],[r['logical_hashes'] for r in b])

    def test_resolution_and_buffer_variants(self):
        original=read_json(self.bundle/'compute.json')['geometry']
        self.assertNotEqual(original['vertices'],self.extra[0]['vertices'])
        self.assertNotEqual(original['vertices'],self.extra[1]['vertices'])
        for r in [original]+self.extra:
            self.assertLessEqual(r['max_edge_target_ratio'],1+1e-8);self.assertEqual(r['components'],1)
            self.assertLess(r['independent_projector_error'],1e-9)

    def test_bundle_portability_without_attempts(self):
        isolated=self.root/'isolated';shutil.copytree(self.bundle,isolated)
        self.assertEqual(len(list(isolated.iterdir())),8)
        self.assertEqual(artifacts.validate_closed(isolated)['status'],'pass')

    def test_file_hash_and_manifest_corruption(self):
        for name in ['geometry.h5','ranges.json','run-spec.json','execution.json','manifest.json']:
            with self.subTest(file=name),tempfile.TemporaryDirectory() as d:
                dst=Path(d)/'copy';shutil.copytree(self.bundle,dst)
                if name=='manifest.json':
                    m=read_json(dst/name);m['status']='failed';(dst/name).write_text(json.dumps(m))
                else:
                    with (dst/name).open('ab') as f:f.write(b'corruption')
                with self.assertRaises((ValueError,json.JSONDecodeError,__import__('jsonschema').ValidationError)):artifacts.validate_closed(dst)

    def test_semantic_corruptions_even_with_updated_file_hashes(self):
        for name in ['raw_all','triangles','projector/data','mass/data','regions','model_rows','eigenvectors']:
            with self.subTest(dataset=name),tempfile.TemporaryDirectory() as d:
                dst=Path(d)/'copy';shutil.copytree(self.bundle,dst)
                with h5py.File(dst/'geometry.h5','r+') as f:
                    ds=f[name];a=ds[:];a.flat[0]+=1;ds[:]=a
                m=read_json(dst/'manifest.json');m['files']['geometry.h5']=file_record(dst/'geometry.h5')
                try:m['logical_hashes']=artifacts.load_payload(dst/'geometry.h5')[2]
                except ValueError:pass
                (dst/'manifest.json').write_text(json.dumps(m))
                with self.assertRaises((ValueError,IndexError)):artifacts.validate_closed(dst)

    def test_missing_artifact_and_final_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            dst=Path(d)/'copy';shutil.copytree(self.bundle,dst);(dst/'validation.json').unlink()
            with self.assertRaises(ValueError):artifacts.validate_closed(dst)
        with self.assertRaises(ValueError):artifacts.finalize(self.bundle,self.other,sha(self.bundle/'run-spec.json'))


if __name__=='__main__':unittest.main(verbosity=2)
