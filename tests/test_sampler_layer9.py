"""Actual synthetic warmup/sweeps plus isolated transaction fault injection."""
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
import numpy as np
from bsfm.sampler.run_initialization import initialize,adapt
from bsfm.sampler.run_genesis import load_genesis,save_genesis,boundary
from bsfm.sampler.run_controller import validate_spec
from bsfm.sampler.run_storage import read_json,write_json,file_record,writer
from bsfm.sampler.checkpoint_rng import stream_audit,json_text
from bsfm.sampler.checkpoint_contract import digest
from bsfm.sampler.layer4 import STATE_ARRAYS,state_hashes
from bsfm.sampler.retained_diagnostics import decode
from sampler_layer9_support import controller,literal_initialization,ROOT


class Interrupt(BaseException):pass


class Layer9Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        artifact_root=os.environ.get('BSFM_LAYER9_ARTIFACTS')
        if artifact_root:
            cache=Path(artifact_root);cache.mkdir(parents=True,exist_ok=False)
        else:
            cls.cache=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.cache.cleanup)
            cache=Path(cls.cache.name)
        cls.template=cache/'template';c=controller(cls.template)
        # Real historical-sequence initialization, 20-step adaptation per factor,
        # and two complete real Layer-6 sweeps. Never a section/production fit.
        cls.complete=c.run()
        cls.genesis,_=load_genesis(c.store.segment/'genesis/endpoint.npz',c.target,c.cp)
        cls.reference_chain=c.store.scan(cls.genesis,digest(read_json(c.store.segment/'genesis/receipt.json')))
        cls.reference_sources=None

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'run';self.saved=np.random.get_state();self.addCleanup(np.random.set_state,self.saved)

    def copy_prefix(self,sweeps=0):
        # Synthetic test setup only. No scientific v1/v2 artifacts reused.
        shutil.copytree(self.template,self.root)
        seg=self.root/'segments/segment'
        for directory in ('transactions','checkpoints','archive','attempts'):
            shutil.rmtree(seg/directory);(seg/directory).mkdir()
        (seg/'archive').rmdir()
        for name in ('completion.json','run-ledger.json'):
            (seg/name).unlink(missing_ok=True)
        for i in range(1,sweeps+1):
            shutil.copytree(self.template/'segments/segment/transactions'/f'{i:012d}',seg/'transactions'/f'{i:012d}')
        return controller(self.root)

    def no_reinitialize(self):
        return patch('bsfm.sampler.run_controller.initialize',side_effect=AssertionError('Genesis replay'))

    def test_initialization_literal_source_and_four_rngs_exact(self):
        c=controller(self.root);e,keys=initialize(c.target,c.loading,c.eta,seed=491)
        before=stream_audit(e.eta_rng,e.gauge_rng,e.master_key,e.numpy_global_state)
        ns,source=literal_initialization(c.target,c.loading,c.eta,491)
        for n in STATE_ARRAYS:np.testing.assert_array_equal(getattr(e.state,n),ns[n])
        for a,b in zip(e.positions,ns['positions']):np.testing.assert_array_equal(a.values,b)
        for a,b in zip(keys,ns['warm_keys']):np.testing.assert_array_equal(a,b)
        self.assertEqual(before,stream_audit(ns['rng'],ns['gauge_rng'],ns['master_key'],np.random.get_state()))
        type(self).reference_sources=source

    def test_sequential_adaptation_endpoint_and_rng_chronology(self):
        c=controller(self.root);e,keys=initialize(c.target,c.loading,c.eta,seed=491)
        other=adapt(c.target,e,keys,steps=20,split=c.layer.split)
        self.assertEqual(boundary(other,c.target),boundary(self.genesis,c.target))
        self.assertEqual(other.evidence,self.genesis.evidence)
        for row in other.evidence['factors']:
            self.assertEqual(row['endpoint_audit']['context']['u_sha256'],row['eta_audit']['u_sha256'])

    def test_genesis_roundtrip_is_not_checkpoint_zero(self):
        c=controller(self.root);p=Path(self.tmp.name)/'e.npz';e=copy.deepcopy(self.genesis)
        a=save_genesis(p,e,c.target,c.cp);b=load_genesis(p,c.target,c.cp)
        self.assertEqual(a[1],b[1]);self.assertEqual(boundary(e,c.target),boundary(b[0],c.target))
        with np.load(p,allow_pickle=False) as z:self.assertEqual(json.loads(str(z['metadata']))['schema'],'bsfm.pre-sweep-endpoint.v1')

    def test_genesis_missing_history_rejected(self):
        c=controller(self.root);e=copy.deepcopy(self.genesis);e.evidence['factors'].pop()
        with self.assertRaises(ValueError):save_genesis(Path(self.tmp.name)/'e.npz',e,c.target,c.cp)

    def test_genesis_spectral_corruption_rejected(self):
        c=self.copy_prefix();p=c.store.segment/'genesis/endpoint.npz'
        with np.load(p,allow_pickle=False) as z:d={k:z[k].copy() for k in z.files}
        d['spectral_U'][0,0]+=1e-8;np.savez_compressed(p,**d)
        with self.assertRaises(ValueError):c.run()

    def test_actual_exact_two_arm_continuation(self):
        c=self.copy_prefix();c.run(stop_after=1)
        with self.no_reinitialize():result=controller(self.root).run()
        self.assertEqual(result,self.complete)
        for i in (1,2):
            a=read_json(c.store.segment/'transactions'/f'{i:012d}'/'prepared.json')
            b=read_json(self.template/'segments/segment/transactions'/f'{i:012d}'/'prepared.json')
            self.assertEqual(a,b)
        self.assertEqual(c.store.scan(self.genesis,digest(read_json(c.store.segment/'genesis/receipt.json')))['endpoint'].boundary,self.reference_chain['endpoint'].boundary)

    def test_commit_non_replay_and_projection_repair(self):
        c=self.copy_prefix(2)
        with self.no_reinitialize(),patch.object(c.layer,'sweep',side_effect=AssertionError('Committed sweep replay')):
            self.assertEqual(c.run(),self.complete)
            (c.store.segment/'archive/records/000000000002/record.npz').unlink()
            (c.store.segment/'archive/records/000000000002').rmdir()
            (c.store.segment/'checkpoints/000000000002.npz').unlink()
            (c.store.segment/'run-ledger.json').write_text('torn')
            self.assertEqual(c.run(),self.complete)

    def test_all_interruption_boundaries(self):
        stages=['before_sweep','after_sweep','after_checkpoint_candidate','after_record_candidate',
                'before_transaction_publish','after_transaction_publish','after_record_projection','after_checkpoint_projection']
        for stage in stages:
            with self.subTest(stage=stage):
                if self.root.exists():shutil.rmtree(self.root)
                c=self.copy_prefix();hit=[]
                def fault(s):
                    # Initial empty projection repair is not the sweep fault.
                    if s==stage and (s not in ('after_record_projection','after_checkpoint_projection') or list((c.store.segment/'transactions').iterdir())):
                        hit.append(s);raise Interrupt(s)
                with self.assertRaises(Interrupt):c.run(stop_after=1,fault=fault)
                self.assertEqual(hit,[stage])
                # Completed pairs must publish without executing the sweep again.
                paired=stage in ('after_record_candidate','before_transaction_publish','after_transaction_publish','after_record_projection','after_checkpoint_projection')
                with self.no_reinitialize():
                    if paired:
                        with patch.object(c.layer,'sweep',side_effect=AssertionError('Completed pair replay')):c.run(stop_after=1)
                    else:c.run(stop_after=1)
                self.assertEqual(read_json(c.store.segment/'transactions/000000000001/prepared.json'),read_json(self.template/'segments/segment/transactions/000000000001/prepared.json'))

    def test_fresh_process_kill_and_recovery(self):
        for stage in ('after_checkpoint_candidate','after_record_candidate','after_transaction_publish','after_record_projection','before_ledger'):
            with self.subTest(stage=stage):
                if self.root.exists():shutil.rmtree(self.root)
                c=self.copy_prefix()
                child=subprocess.run([sys.executable,'-B',str(ROOT/'tests/layer9_crash_worker.py'),str(self.root),stage],capture_output=True,text=True)
                self.assertEqual(child.returncode,91,child.stderr)
                with self.no_reinitialize():c.run(stop_after=1)
                self.assertEqual(read_json(c.store.segment/'transactions/000000000001/prepared.json'),read_json(self.template/'segments/segment/transactions/000000000001/prepared.json'))

    def test_genesis_publish_interruption_no_readaptation(self):
        c=self.copy_prefix();seg=c.store.segment
        dest=seg/'attempts/prepared/genesis';dest.parent.mkdir();os.rename(seg/'genesis',dest)
        with self.no_reinitialize():c.run(stop_after=0)
        self.assertTrue((seg/'genesis/receipt.json').exists())

    def test_conflicting_projections_rejected(self):
        c=self.copy_prefix(1);c.run(stop_after=1)
        (c.store.segment/'archive/records/000000000001/record.npz').write_bytes(b'corrupt')
        with self.assertRaises(ValueError):c.run()

    def test_orphan_projection_rejected(self):
        c=self.copy_prefix();c.run(stop_after=0)
        (c.store.segment/'archive/records/000000000001').mkdir()
        with self.assertRaises(ValueError):c.run()

    def test_corrupt_committed_transaction_never_replayed(self):
        c=self.copy_prefix(1);(c.store.segment/'transactions/000000000001/checkpoint.npz').write_bytes(b'bad')
        with patch.object(c.layer,'sweep',side_effect=AssertionError('Replay')):
            with self.assertRaises((ValueError,EOFError)):c.run()

    def test_identity_and_run_length_drift_rejected(self):
        c=self.copy_prefix();c.spec['seed']+=1
        with self.assertRaises(ValueError):c.run()

    def test_readaptation_rejected(self):
        c=controller(self.root);c.spec['mode']='readapt'
        with self.assertRaises(ValueError):validate_spec(c.spec)

    def test_known_numerical_failure_is_terminal(self):
        c=self.copy_prefix()
        with patch.object(c.layer,'sweep',side_effect=RuntimeError('synthetic failed invariant')):
            with self.assertRaises(RuntimeError):c.run()
        with self.assertRaisesRegex(ValueError,'terminal'):c.run()

    def test_nonretained_records_and_cadence_greater_than_one(self):
        for every in (2,3,5):
            with self.subTest(every=every):
                path=Path(self.tmp.name)/str(every);c=controller(path,every=every,settling=1)
                with patch('bsfm.sampler.run_controller.initialize',return_value=(None,None)),patch('bsfm.sampler.run_controller.adapt',return_value=copy.deepcopy(self.genesis)):
                    c.run(stop_after=1)
                self.assertEqual(list((c.store.segment/'checkpoints').iterdir()),[])
                with self.no_reinitialize():c.run()
                self.assertTrue((c.store.segment/'checkpoints/000000000002.npz').exists())
                a=read_json(c.store.segment/'completion.json');self.assertEqual(a['retained'],1)

    def test_writer_lock_excludes_second_writer(self):
        with writer(self.root):
            with self.assertRaises(RuntimeError):
                with writer(self.root):pass

    def test_interrupted_sweep_discards_advanced_rng(self):
        c=self.copy_prefix()
        def interrupted(*args,**kwargs):
            np.random.standard_normal(7);kwargs['eta_rng'].normal(size=5);kwargs['gauge_rng'].normal(size=4)
            raise Interrupt('process died during uncommitted work')
        with patch.object(c.layer,'sweep',side_effect=interrupted):
            with self.assertRaises(Interrupt):c.run(stop_after=1)
        c.run(stop_after=1)
        self.assertEqual(read_json(c.store.segment/'transactions/000000000001/prepared.json'),read_json(self.template/'segments/segment/transactions/000000000001/prepared.json'))

    def test_record_only_attempt_recomputed_not_invented(self):
        c=self.copy_prefix();c.run(stop_after=0)
        gid=digest(read_json(c.store.segment/'genesis/receipt.json'));chain=c.store.scan(self.genesis,gid)
        a=c.store.segment/'attempts/record-only';(a/'transaction').mkdir(parents=True)
        write_json(a/'intent.json',dict(sweep=1,previous_sha256=chain['head'],spec_sha256=c.store.spec_hash))
        shutil.copyfile(self.template/'segments/segment/transactions/000000000001/record.npz',a/'transaction/record.npz')
        c.run(stop_after=1)
        self.assertFalse((a/'transaction/checkpoint.npz').exists())
        self.assertTrue((a/'transaction/record.npz').exists())

    def test_interrupted_record_write_preserved_and_recomputed(self):
        c=self.copy_prefix()
        def fault(stage):
            if stage=='after_checkpoint_candidate':raise Interrupt(stage)
        with self.assertRaises(Interrupt):c.run(stop_after=1,fault=fault)
        attempt=next(p for p in (c.store.segment/'attempts').iterdir() if (p/'intent.json').exists())
        partial=attempt/'transaction/record.npz';partial.write_bytes(b'PK\x03\x04')
        c.run(stop_after=1)
        self.assertEqual(partial.read_bytes(),b'PK\x03\x04')
        self.assertEqual(read_json(c.store.segment/'transactions/000000000001/prepared.json'),
                         read_json(self.template/'segments/segment/transactions/000000000001/prepared.json'))

    def test_initialization_to_warmup_binding_rejected(self):
        c=controller(self.root);e=copy.deepcopy(self.genesis)
        e.evidence['initialization']['after_PX']['eta']='0'*64
        with self.assertRaisesRegex(ValueError,'Initialization/warmup'):
            save_genesis(Path(self.tmp.name)/'bad.npz',e,c.target,c.cp)

    def test_saved_chart_restoration_without_eigensolve(self):
        from bsfm.sampler.run_chart import geometry_from_genesis
        from bsfm.sampler.field_target import DirectWTarget
        c=controller(self.root);g=c.target.geometry
        path=self.template/'segments/segment/genesis/endpoint.npz'
        with patch('scipy.linalg.eigh',side_effect=AssertionError('Eigensystem recomputed')):
            restored=geometry_from_genesis(g.arrays,json.loads(g.identity_json),path)
            target=DirectWTarget(c.target.inputs,restored,c.target.rule,factor_ids=c.target.factor_ids)
            endpoint,_=load_genesis(path,target,c.cp)
        self.assertEqual(boundary(self.genesis,c.target),boundary(endpoint,target))
        self.assertEqual(restored.spectral_identity,g.spectral_identity)

    def test_interrupted_prepared_receipt_recovers_without_sweep(self):
        c=self.copy_prefix();partial=[]
        def torn(path,value):
            path.write_bytes(b'{"schema":');partial.append(path);raise Interrupt()
        with patch('bsfm.sampler.run_receipts.write_json',side_effect=torn):
            with self.assertRaises(Interrupt):c.run(stop_after=1)
        self.assertEqual(len(partial),1)
        with patch.object(c.layer,'sweep',side_effect=AssertionError('Prepared sweep replay')):
            c.run(stop_after=1)
        self.assertEqual(partial[0].read_bytes(),b'{"schema":')
        self.assertEqual(read_json(c.store.segment/'transactions/000000000001/prepared.json'),
                         read_json(self.template/'segments/segment/transactions/000000000001/prepared.json'))

    def test_genesis_seed_must_match_immutable_spec(self):
        c=self.copy_prefix();seg=c.store.segment
        e=copy.deepcopy(self.genesis);e.evidence['initialization']['seed']+=1
        (seg/'genesis/endpoint.npz').unlink();(seg/'genesis/receipt.json').unlink()
        from bsfm.sampler.run_storage import file_record
        _,h=save_genesis(seg/'genesis/endpoint.npz',e,c.target,c.cp)
        write_json(seg/'genesis/receipt.json',dict(schema='bsfm.genesis.v1',spec_sha256=c.store.spec_hash,
            input_sha256=c.spec['input_sha256'],endpoint=file_record(seg/'genesis/endpoint.npz'),logical_sha256=h))
        with self.assertRaisesRegex(ValueError,'differs from run specification'):c.run()

    def test_multiple_prepared_pairs_fail_closed(self):
        c=self.copy_prefix();c.run(stop_after=0)
        chain=c.store.scan(self.genesis,digest(read_json(c.store.segment/'genesis/receipt.json')))
        for name in ('one','two'):
            a=c.store.segment/'attempts'/name;a.mkdir()
            write_json(a/'intent.json',dict(sweep=1,previous_sha256=chain['head'],spec_sha256=c.store.spec_hash))
            shutil.copytree(self.template/'segments/segment/transactions/000000000001',a/'transaction')
        with patch.object(c.layer,'sweep',side_effect=AssertionError('Replay')):
            with self.assertRaisesRegex(ValueError,'Multiple prepared'):c.run()

    def test_checkpoint_projection_only_repaired(self):
        c=self.copy_prefix(2)
        shutil.copyfile(c.store.segment/'transactions/000000000002/checkpoint.npz',c.store.segment/'checkpoints/000000000002.npz')
        with patch.object(c.layer,'sweep',side_effect=AssertionError('Replay')):self.assertEqual(c.run(),self.complete)

    def test_environment_authentication(self):
        from bsfm.sampler.run_inputs import authenticate_environment
        r=authenticate_environment();self.assertTrue(r['cpu'] and r['x64']);self.assertGreater(r['installed_record_files'],100)

    def test_file_identity_rejects_mutation(self):
        from bsfm.sampler.run_inputs import authenticate_files
        p=Path(self.tmp.name)/'binding';p.write_bytes(b'bound')
        records={'input':dict(path=str(p),**file_record(p))};authenticate_files(records)
        p.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'Input file changed'):authenticate_files(records)

    def test_no_hdf5_runtime_dependency(self):
        import ast
        for p in (ROOT/'src/bsfm/sampler').glob('run_*.py'):
            for n in ast.walk(ast.parse(p.read_text())):
                if isinstance(n,ast.Import):self.assertFalse(any(a.name in ('h5py','sklearn') for a in n.names))
                if isinstance(n,ast.ImportFrom):self.assertNotIn(n.module,('h5py','sklearn'))

    @classmethod
    def tearDownClass(cls):
        out=os.environ.get('BSFM_LAYER9_RECEIPT')
        if out:
            p=Path(out);p.parent.mkdir(parents=True,exist_ok=True)
            p.write_text(json.dumps(dict(scope='synthetic '+sys.platform+' CPU only',completion=cls.complete,
                boundary=cls.reference_chain['endpoint'].boundary,historical_initialization_reference=cls.reference_sources,
                target_acceptance=.9,warmup_steps_per_factor=20,real_sweeps_per_arm=2),indent=2,allow_nan=False)+'\n',encoding='utf-8')


if __name__=='__main__':unittest.main()
