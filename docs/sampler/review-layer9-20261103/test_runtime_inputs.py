"""Synthetic NPZ registration joins; no canonical scientific input is generated."""
import copy,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]
import numpy as np
from sampler_layer3_support import system
from bsfm.sampler.run_inputs import load_inputs
from bsfm.sampler.run_storage import file_record
from bsfm.sampler.contracts import logical_hash
from bsfm.mesh.identities import logical

class InputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.target,cls.state,_=system()
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.files={}
        t=self.target;g=t.geometry.arrays;d=dict(t.inputs.arrays)
        self.mesh=dict(fem_C=g['terms'][0],mesh_vertices=g['vertices'],A_full=g['projector'],
            slocs=g['locations'],active_indices_full=g['active_indices'],source_rows=g['source_rows'],cell_type=d['cell_id'])
        self.mesh.update({f'fem_g{i}':g['terms'][i] for i in range(1,7)})
        self.put('prepared',d,True);self.put('mesh',self.mesh,True)
        seeds=dict(Lam_seed=self.state.loading,eta_seed=self.state.eta)
        self.put('gpinit',seeds,True)
        for role in ('response_manifest','response_validation'):self.put(role,dict(scope='synthetic test only'))
        identity=json.loads(t.inputs.identity_json)
        self.contract=dict(section='synthetic',producer=dict(generating_commit='a'*40,worktree_clean=True),
            source_sha256=self.files['prepared']['sha256'],arrays=identity['arrays'],
            upstream=dict(response_h5=dict(sha256=identity['response_sha256']),
                mesh_arrays={k:dict(sha256=logical(v)) for k,v in self.mesh.items()}))
        self.put('contract',self.contract)
        self.certificate=dict(input_identities=self.contract['arrays'],factors=2,
            provenance=dict(contract_sha256=self.files['contract']['sha256'],input_sha256=self.files['prepared']['sha256']),
            output_logical_hashes={k:logical_hash(v) for k,v in seeds.items()})
        self.put('certificate',self.certificate)
        self.registration=dict(status='clean_commit_regeneration_passed_registration_accepted',generating_commit='a'*40,
            prepared_npz=self.files['prepared'].copy(),prepared_contract=self.files['contract'].copy(),
            upstream={key:self.files[role].copy() for key,role in [('mesh','mesh'),('response_manifest','response_manifest'),('validation','response_validation')]},
            fits=[dict(output=self.files['gpinit'].copy(),certificate=self.files['certificate'].copy())])
        self.put('registration',self.registration)
    def put(self,name,value,npz=False):
        p=self.root/(name+('.npz' if npz else '.json'))
        if npz:np.savez(p,**value)
        else:p.write_text(json.dumps(value))
        self.files[name]=dict(path=str(p),**file_record(p))
    def load(self):return load_inputs(self.files,self.target.factor_ids)
    def test_npz_join_accepts_valid_synthetic_registration(self):
        target,loading,eta,binding=self.load()
        np.testing.assert_array_equal(target.inputs.arrays['Y'],self.target.inputs.arrays['Y'])
        np.testing.assert_array_equal(loading,self.state.loading);np.testing.assert_array_equal(eta,self.state.eta)
        self.assertFalse(binding['primary_holdout_scoring_eligible'])
    def test_file_mutation_rejected_before_loading(self):
        with Path(self.files['prepared']['path']).open('ab') as f:f.write(b'changed')
        with self.assertRaisesRegex(ValueError,'Input file changed'):self.load()
    def test_unregistered_seed_pair_rejected(self):
        self.put('gpinit',dict(Lam_seed=self.state.loading+1,eta_seed=self.state.eta),True)
        with self.assertRaisesRegex(ValueError,'Unregistered'):self.load()
    def test_self_consistent_certificate_file_cannot_break_input_join(self):
        self.certificate['input_identities']={}
        self.put('certificate',self.certificate)
        self.registration['fits'][0]['certificate']=self.files['certificate'].copy()
        self.put('registration',self.registration)
        with self.assertRaisesRegex(ValueError,'binding mismatch'):self.load()
    def test_reordered_mesh_rows_rejected_after_hashes_updated(self):
        self.mesh['source_rows']=self.mesh['source_rows'][::-1].copy()
        self.put('mesh',self.mesh,True)
        self.contract['upstream']['mesh_arrays']['source_rows']['sha256']=logical(self.mesh['source_rows'])
        self.put('contract',self.contract)
        self.certificate['provenance']['contract_sha256']=self.files['contract']['sha256']
        self.put('certificate',self.certificate)
        self.registration['prepared_contract']=self.files['contract'].copy()
        self.registration['upstream']['mesh']=self.files['mesh'].copy()
        self.registration['fits'][0]['certificate']=self.files['certificate'].copy()
        self.put('registration',self.registration)
        with self.assertRaisesRegex(ValueError,'Full population mesh join'):self.load()

if __name__=='__main__':
    result=unittest.TextTestRunner(stream=sys.stdout,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(InputTests))
    sys.exit(not result.wasSuccessful())
