"""Real preparation/GPINIT to sampler assembly; synthetic final mesh, no R build."""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
import jax
import numpy as np
from scipy.io import mmwrite

from bsfm.preprocessing import dataset
from bsfm.mesh import october26 as mesh
from bsfm.mesh.projectors import project, active
from bsfm.sampler.run_inputs import load_inputs
from bsfm.sampler.run_storage import file_record
from bsfm.sampler.run_initialization import initialize
from bsfm.sampler.run_genesis import boundary
from test_gp_initialization import fixture

ROOT = Path(__file__).resolve().parents[1]
CHART = 'october26_glial_min_max_span'


class DatasetSamplerInputs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from bsfm.initialization import gp_svd as gp
        cls.tmp = tempfile.TemporaryDirectory(); cls.addClassCleanup(cls.tmp.cleanup)
        cls.base = Path(cls.tmp.name)/'base'; cls.base.mkdir()
        old = fixture(); keep = old['cell_id'] != 2
        labels = np.array(['neurons', 'support'])
        data = dict(expression=old['Y'][:,keep]+10, coordinates=old['slocs'][keep],
            gene_names=old['gene_names'], cell_names=old['cell_names'][keep],
            group_names=labels[old['cell_id'][keep]], sample_names=np.array(['new-tissue']*sum(keep)),
            animal_names=np.array(['']*sum(keep)), source_row_indices=old['source_row_indices'][keep])
        metadata = dict(schema='bsfm.dataset.v1', dataset_id='new-dataset-fixture',
            animal_identity_known=False, coordinate_units='synthetic y,x', normalization=dict(
                response='uncentered_normalized', method='synthetic', units='synthetic',
                population='all cells', evidence='test fixture'))
        bundle = cls.base/'dataset'; prepared = cls.base/'prepared'; seeds = cls.base/'seeds'
        dataset.write_dataset(bundle,data,metadata,sources=[dict(path='synthetic',sha256='0'*64)])
        selection = dict(sample='new-tissue', groups=labels.tolist(), genes=data['gene_names'].tolist(),
                         training_cells=data['cell_names'].tolist(), heldout_cells=[])
        recipe = cls.base/'selection.json'; recipe.write_text(json.dumps(selection))
        with patch('sys.argv',['dataset','--dataset',str(bundle),'--manifest-sha256',dataset.file_hash(bundle/'dataset.json'),
                    '--selection',str(recipe),'--output',str(prepared),'--gpinit-contract']): dataset.main()
        # The local Windows BLAS runtime crashes with four threads, including
        # on unchanged GPINIT tests. This integration checks one-thread assembly,
        # not restoration of the accepted four-thread initialization environment.
        config = json.loads(gp.CONFIG.read_text(encoding='utf-8')); config['threads']=1
        config_path = cls.base/'gp-config.json'; config_path.write_text(json.dumps(config))
        with patch.object(gp,'CONFIG',config_path), \
             patch('sys.argv',['gp_svd','--input',str(prepared/'training.npz'),'--contract',str(prepared/'gpinit-input.json'),
                    '--output',str(seeds),'--factors','2','--nfit','8','--seed','41']): gp.main()
        with np.load(prepared/'training.npz') as z: cls.training = {k:z[k].copy() for k in z.files}
        geo = cls.base/'final-mesh'; geo.mkdir()
        vertices = np.array([[0.,0.],[1.,0.],[1.,1.],[0.,1.],[.5,.5]])
        triangles = np.array([[0,1,4],[1,2,4],[2,3,4],[3,0,4]],np.int64)
        projector = project(vertices,triangles,cls.training['slocs'])
        np.savetxt(geo/'mesh_loc.csv',vertices,delimiter=',',header='x,y',comments='')
        np.savetxt(geo/'mesh_tv.csv',triangles,delimiter=',',header='v1,v2,v3',comments='',fmt='%d')
        mmwrite(geo/'A_proj.mtx',projector)
        (geo/'geometry.json').write_text(json.dumps(dict(vertices=5,triangles=4,active=len(active(projector)),
            index_base=0,axis_order=['center_y','center_x'],units='source_native')))
        cls.geometry_files = {p.name:file_record(p) for p in geo.iterdir()}
        arrays = mesh.sampler_geometry(geo,locations=cls.training['slocs'],cell_ids=cls.training['cell_names'],
            source_rows=cls.training['source_row_indices'],expected_files=cls.geometry_files,coordinate_system=CHART)
        mass,stiffness,_ = mesh.fem_matrices(vertices,triangles)
        np.testing.assert_array_equal(arrays['terms'],np.stack(mesh.polynomial_fem(mass,stiffness)))
        np.testing.assert_array_equal(arrays['projector'],projector.toarray())
        np.savez_compressed(cls.base/'warp.npz',**arrays)
        shutil.copyfile(ROOT/'docs/sampler/s10-subset-smoke-20261103/L4_ell14_smoke.json',cls.base/'rule.json')
        cls.recipe = dict(schema='bsfm.dataset-run-inputs.v1',sample='new-tissue',coordinate_system=CHART,quadrature_order=4)

    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)/'copy'; shutil.copytree(self.base,self.root)
        paths = dict(prepared='prepared/training.npz',contract='prepared/gpinit-input.json',
            response_manifest='prepared/response.json',mesh='warp.npz',gpinit='seeds/gpinit.npz',
            certificate='seeds/certificate.json',rule='rule.json')
        self.files = {role:dict(path=str(self.root/name),**file_record(self.root/name)) for role,name in paths.items()}

    def test_preparation_initializer_mesh_and_sampler_connection(self):
        target,loading,eta,binding = load_inputs(self.files,('factor-a','factor-b'),dataset_recipe=self.recipe)
        self.assertEqual(loading.shape,(2,2,2)); self.assertEqual(eta.shape,(2,24))
        self.assertEqual(target.rule.arrays['omega'].shape,(32,2))
        for key,value in self.training.items(): np.testing.assert_array_equal(target.inputs.arrays[key],value)
        first,_ = initialize(target,loading,eta,seed=31)
        value,gradient,_ = target.value_grad(first.positions[0],first.state,state_factor_ids=target.factor_ids)
        self.assertTrue(np.isfinite(value)); self.assertTrue(np.isfinite(gradient).all())
        again,_ = initialize(target,loading,eta,seed=31)
        self.assertEqual(boundary(first,target),boundary(again,target))
        self.assertEqual(binding['dataset_recipe'],self.recipe)
        self.assertFalse(binding['primary_holdout_scoring_eligible'])

    def test_reject_mixed_certificates_and_geometry_identities(self):
        path = Path(self.files['certificate']['path']); report = json.loads(path.read_text())
        report['provenance']['input_sha256']='0'*64; path.write_text(json.dumps(report))
        self.files['certificate'].update(file_record(path))
        with self.assertRaisesRegex(ValueError,'certificate/preparation'):
            load_inputs(self.files,('a','b'),dataset_recipe=self.recipe)
        shutil.copyfile(self.base/'seeds/certificate.json',path); self.files['certificate'].update(file_record(path))
        path = Path(self.files['mesh']['path'])
        with np.load(path) as z: arrays = {k:z[k].copy() for k in z.files}
        arrays['cell_ids'] = arrays['cell_ids'][::-1].copy(); np.savez_compressed(path,**arrays)
        self.files['mesh'].update(file_record(path))
        with self.assertRaisesRegex(ValueError,'Prepared/mesh join'):
            load_inputs(self.files,('a','b'),dataset_recipe=self.recipe)

    def test_reject_changed_files_counts_chart_and_order(self):
        with self.assertRaisesRegex(ValueError,'certificate/preparation'):
            load_inputs(self.files,('a',),dataset_recipe=self.recipe)
        for key,value in [('coordinate_system','source_native'),('sample','wrong'),('quadrature_order',14)]:
            with self.subTest(key=key),self.assertRaises(ValueError):
                load_inputs(self.files,('a','b'),dataset_recipe=dict(self.recipe,**{key:value}))
        path=Path(self.files['prepared']['path']); path.write_bytes(path.read_bytes()+b'tamper')
        with self.assertRaisesRegex(ValueError,'Input file changed'):
            load_inputs(self.files,('a','b'),dataset_recipe=self.recipe)

    def test_final_mesh_output_pins_and_coordinate_alignment(self):
        kwargs=dict(locations=self.training['slocs'],cell_ids=self.training['cell_names'],
            source_rows=self.training['source_row_indices'],expected_files=self.geometry_files,coordinate_system=CHART)
        with self.assertRaises(ValueError):
            mesh.sampler_geometry(self.root/'final-mesh',**dict(kwargs,locations=kwargs['locations']+.1))
        (self.root/'final-mesh/mesh_loc.csv').write_text('changed')
        with self.assertRaisesRegex(ValueError,'Final geometry file changed'):
            mesh.sampler_geometry(self.root/'final-mesh',**kwargs)


if __name__ == '__main__': unittest.main()
