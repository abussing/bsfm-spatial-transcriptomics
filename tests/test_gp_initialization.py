"""Bounded tests of the recovered cold-start recipe, not GP alternatives."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from bsfm.initialization import gp_svd as gp


def fixture():
    n=36
    t=np.arange(n,dtype=np.int32)%3
    x=np.column_stack((np.linspace(0,1,n),np.sin(np.arange(n)*.7)*.1+.2))
    y=np.stack((np.sin(4*x[:,0]),np.cos(3*x[:,0])+.1*x[:,1]))
    for c in range(3):y[:,t==c]-=y[:,t==c].mean(axis=1,keepdims=True)
    return dict(Y=y,slocs=x,cell_id=t,cell_names=np.array([f'cell-{i}' for i in range(n)]),
        source_row_indices=np.arange(n,dtype=np.int64)*2,gene_names=np.array(['gene-a','gene-b']),
        cell_type_names=np.array(['MIC','AST','OGC']))


class GPInitializationTests(unittest.TestCase):
    def test_generic_preparation_cli_to_existing_initializer(self):
        from bsfm.preprocessing import dataset
        original=fixture()
        labels=np.array(['group-one','group-two','group-three'])
        data=dict(expression=original['Y']+10,coordinates=original['slocs'],
            gene_names=original['gene_names'],cell_names=original['cell_names'],
            group_names=labels[original['cell_id']],sample_names=np.array(['new-sample']*36),
            animal_names=np.array(['']*36),source_row_indices=original['source_row_indices'])
        metadata=dict(schema='bsfm.dataset.v1',dataset_id='integration-fixture',
            animal_identity_known=False,coordinate_units='synthetic',normalization=dict(
                response='uncentered_normalized',method='synthetic',units='synthetic',
                population='all declared cells',evidence='test fixture'))
        selection=dict(sample='new-sample',groups=labels.tolist(),genes=original['gene_names'].tolist(),
            training_cells=original['cell_names'].tolist(),heldout_cells=[])
        direct,_,_=dataset.prepare_response(data,metadata,**selection)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);bundle=root/'dataset';prepared=root/'prepared';out=root/'seeds'
            dataset.write_dataset(bundle,data,metadata,sources=[dict(path='synthetic',sha256='0'*64)])
            recipe=root/'selection.json';recipe.write_text(json.dumps(selection))
            argv=['dataset','--dataset',str(bundle),'--manifest-sha256',dataset.file_hash(bundle/'dataset.json'),
                  '--selection',str(recipe),'--output',str(prepared),'--gpinit-contract']
            with patch('sys.argv',argv):dataset.main()
            contract=json.loads((prepared/'gpinit-input.json').read_text())
            loaded=gp.load_input(prepared/'training.npz',contract)
            for key in direct:np.testing.assert_array_equal(direct[key],loaded[key])
            receipt=json.loads((prepared/'response.json').read_text())
            self.assertEqual(receipt['files']['gpinit-input.json'],gp.sha(prepared/'gpinit-input.json'))
            expected,_=gp.fit(direct,factors=2,nfit=8,seed=41)
            with patch('sys.argv',['gp_svd','--input',str(prepared/'training.npz'),
                '--contract',str(prepared/'gpinit-input.json'),'--output',str(out),
                '--factors','2','--nfit','8','--seed','41']):gp.main()
            with np.load(out/'gpinit.npz',allow_pickle=False) as bank:
                for key in expected:np.testing.assert_array_equal(expected[key],bank[key])
            contract['arrays']['gene_names']='0'*64
            with self.assertRaises(ValueError):gp.load_input(prepared/'training.npz',contract)

    @classmethod
    def setUpClass(cls):
        cls.data=fixture()
        cls.arrays,cls.report=gp.fit(cls.data,factors=2,nfit=8,seed=41)

    def test_no_input_mutation_or_response_export(self):
        expected=fixture()
        for k in expected:np.testing.assert_array_equal(expected[k],self.data[k])
        self.assertNotIn('Y',self.arrays)
        self.assertLess(self.report['maximum_input_recentering_mean'],1e-14)

    def test_exact_legacy_selection_order_and_within_type(self):
        a,rng=gp.fitting_points(self.data['cell_id'],8,41)
        reference=np.random.RandomState(41)
        for c,ix in enumerate(a):
            np.testing.assert_array_equal(ix,reference.choice(np.flatnonzero(self.data['cell_id']==c),8,replace=False))
            self.assertTrue(np.all(self.data['cell_id'][ix]==c))
        np.testing.assert_array_equal(rng.choice(36,10,replace=False),reference.choice(36,10,replace=False))

    def test_nfit_caps_at_type_population(self):
        choices,_=gp.fitting_points(self.data['cell_id'],250,41)
        self.assertEqual([len(x) for x in choices],[12,12,12])

    def test_predicted_fields_at_all_locations_and_centered(self):
        self.assertLess(self.report['surface_mean_max'],1e-14)
        self.assertEqual(len(self.report['all_singular_values']),6)
        self.assertEqual(self.arrays['eta_seed'].shape,(2,36))
        self.assertGreater(float(self.arrays['seed_vs_smoothed_correlation']),.8)

    def test_actual_GP_inputs_and_all_cell_predictions(self):
        fitted=[];predicted=[]
        original_fit=gp.GaussianProcessRegressor.fit
        original_predict=gp.GaussianProcessRegressor.predict
        def record_fit(model,x,y):
            fitted.append((x.copy(),y.copy()))
            return original_fit(model,x,y)
        def record_predict(model,x):
            predicted.append(x.copy())
            return original_predict(model,x)
        with patch.object(gp.GaussianProcessRegressor,'fit',record_fit),patch.object(gp.GaussianProcessRegressor,'predict',record_predict):
            gp.fit(self.data,factors=2,nfit=8,seed=41)
        choices,_=gp.fitting_points(self.data['cell_id'],8,41)
        for c,ix in enumerate(choices):
            centered=self.data['Y'][:,self.data['cell_id']==c].mean(axis=1)
            for g in range(2):
                np.testing.assert_array_equal(fitted[c*2+g][0],self.data['slocs'][ix])
                np.testing.assert_array_equal(fitted[c*2+g][1],self.data['Y'][g,ix]-centered[g])
                np.testing.assert_array_equal(predicted[c*2+g],self.data['slocs'])

    def test_repeat_determinism(self):
        arrays,report=gp.fit(self.data,factors=2,nfit=8,seed=41)
        for k in arrays:np.testing.assert_array_equal(arrays[k],self.arrays[k])
        self.assertEqual(report['fitting_indices'],self.report['fitting_indices'])
        self.assertEqual(report['centered_surface_sha256'],self.report['centered_surface_sha256'])

    def test_svd_dimensions_reconstruction_and_unchanged_backend_signs(self):
        fields=np.random.RandomState(5).normal(size=(3,2,36))
        original=fields.copy()
        stacked,s,lam,eta=gp.svd_seeds(fields,6,1e-12)
        u,ref_s,v=np.linalg.svd(stacked,full_matrices=False)
        np.testing.assert_array_equal(s,ref_s)
        np.testing.assert_allclose(lam.reshape(6,6)@eta,stacked,atol=1e-13)
        for k in range(6):
            raw=u[:,k]*ref_s[k];norm=np.linalg.norm(raw)
            np.testing.assert_array_equal(lam[:,:,k].ravel(),raw/norm)
            np.testing.assert_array_equal(eta[k],v[k]*norm)
        np.testing.assert_array_equal(fields,original)

    def test_loading_gauge_and_eta_centering(self):
        lam=self.arrays['Lam_seed'].reshape(6,2)
        np.testing.assert_allclose(lam.T@lam,np.eye(2),atol=1e-13)
        self.assertLess(self.report['eta_mean_max'],1e-13)
        self.assertEqual(self.arrays['Lam_seed'].shape,(3,2,2))

    def test_invalid_K_nfit_seed(self):
        for k,n,s in [(0,8,1),(7,8,1),(2,0,1),(2,8,-1),(True,8,1),(2,8,2**32),(2,1.5,1)]:
            with self.subTest(values=(k,n,s)),self.assertRaises(ValueError):gp.fit(self.data,factors=k,nfit=n,seed=s)

    def test_missing_type_nonfinite_and_duplicates(self):
        for key,mutate in [('cell_id',lambda a:np.zeros_like(a)),('Y',lambda a:np.full_like(a,np.nan)),
                           ('cell_names',lambda a:np.repeat(a[0],len(a))),('source_row_indices',lambda a:np.zeros_like(a))]:
            data=copy.deepcopy(self.data);data[key]=mutate(data[key])
            with self.subTest(key=key),self.assertRaises(ValueError):gp.validate(data,2,8,41)

    def test_authenticated_identity_and_order_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'input.npz';np.savez_compressed(p,**self.data)
            contract=dict(schema='bsfm.gpinit-input.v1',response='final_centered_Y',
                source_sha256=gp.sha(p),arrays=gp.identities(self.data))
            gp.load_input(p,contract)
            for key in ['gene_names','cell_names','cell_id','slocs','source_row_indices']:
                changed=copy.deepcopy(self.data);changed[key]=changed[key][::-1]
                np.savez_compressed(p,**changed);contract['source_sha256']=gp.sha(p)
                with self.subTest(key=key),self.assertRaisesRegex(ValueError,'identity/order'):gp.load_input(p,contract)

    def test_saved_pickle_free_readback_and_fresh_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest=Path(tmp)/'out'
            gp.save(dest,self.arrays,self.report,provenance={'synthetic':True})
            with np.load(dest/'gpinit.npz',allow_pickle=False) as z:
                for k in z.files:
                    self.assertFalse(z[k].dtype.hasobject)
                    np.testing.assert_array_equal(z[k],self.arrays[k])
            with self.assertRaises(FileExistsError):gp.save(dest,self.arrays,self.report,provenance={})

    def test_fit_failure_is_not_replaced_by_a_new_method(self):
        with patch.object(gp.GaussianProcessRegressor,'fit',side_effect=RuntimeError('deliberate fit failure')):
            with self.assertRaisesRegex(RuntimeError,'deliberate fit failure'):gp.fit(self.data,factors=2,nfit=8,seed=41)
