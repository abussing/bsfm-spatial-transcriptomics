"""Bounded storage/diagnostic gates; no production sampler loop."""
import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import jax

from bsfm.sampler import retained_archive as ra
from bsfm.sampler.retained_contract import build_retained_contract, RetainedContract, retain_at
from bsfm.sampler.retained_records import load_record, descriptor, STATE_ARRAYS
from bsfm.sampler.retained_diagnostics import encode, decode, diagnostics_for
from bsfm.sampler.checkpoint import save_checkpoint_atomic, load_checkpoint
from bsfm.sampler.checkpoint_contract import CheckpointContract, digest
from bsfm.sampler.checkpoint_rng import json_text, parse_json, stream_audit
from sampler_layer6_support import fixture_system, record_result

ROOT=Path(__file__).resolve().parents[1]
BASE='fb3b4f28b81605172eb9eeb2abbf321c4a1fa2f8'


class RetainedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.target,cls.state,cls.positions,cls.sweep,cls.tuning,cls.scale=fixture_system()
        np.random.seed(491)
        eta=np.random.default_rng(193);gauge=np.random.default_rng(307);key=jax.random.PRNGKey(419)
        cls.first=cls.sweep.sweep(cls.state,cls.positions,cls.tuning,eta_rng=eta,gauge_rng=gauge,
            master_key=key,state_factor_ids=cls.target.factor_ids,label='sweep_0001')
        cls.second=cls.sweep.sweep(cls.first.state,cls.first.positions,cls.tuning,eta_rng=eta,gauge_rng=gauge,
            master_key=cls.first.master_key,state_factor_ids=cls.target.factor_ids,label='sweep_0002')

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.contract=self.contract_for()
        self.archive=self.create('a')

    def contract_for(self,chain='chain-A',every=1,settling=0,final=None):
        software=dict(git_commit=BASE,clean_tree=False,
            run_config_sha256=digest(dict(purpose='synthetic retention gate')),
            environment_lock_sha256=hashlib.sha256((ROOT/'environment/sampler-layer5/source-lock.json').read_bytes()).hexdigest(),
            environment_identity='sampler-layer5-cpu-20261102:Windows-CPU')
        return build_retained_contract(self.target,b_sigma2=self.scale,software=software,
            expected_software_sha256=digest(software),chain_id=chain,save_every=every,
            settling_sweeps=settling,final_sweep=final)

    def create(self,name,contract=None):
        return ra.create_archive(self.root/name,target=self.target,contract=contract or self.contract,b_sigma2=self.scale)

    def append(self,archive=None,result=None,sweep=1,events=None):
        return (archive or self.archive).append(result or self.first,sweep=sweep,
            events=[] if events is None else events,elapsed_seconds=None)

    def path(self,sweep=1):return self.archive.root/'records'/f'{sweep:012d}'/'record.npz'

    def mutate(self,fn,rehash=False):
        p=self.path()
        with np.load(p,allow_pickle=False) as f:data={k:f[k].copy() for k in f.files}
        m=parse_json(str(data.pop('metadata')));fn(data,m)
        if rehash:
            m['arrays']={k:descriptor(v) for k,v in data.items()};m.pop('logical_sha256');m['logical_sha256']=digest(m)
        np.savez_compressed(p,**data,metadata=np.array(json_text(m)))

    def test_exact_retained_state_and_reconstruction(self):
        self.append();m,data,d=self.archive.read_retained(1)
        for n in STATE_ARRAYS:np.testing.assert_array_equal(data[n],getattr(self.first.state,n))
        np.testing.assert_array_equal(data['positions'],np.stack([p.values for p in self.first.positions]))
        self.assertEqual(m['diagnostics'],diagnostics_for(self.first,events=[],elapsed_seconds=None))
        self.assertEqual(d['sweep_audit'],self.first.audit)
        self.assertEqual(set(data),set(STATE_ARRAYS)|{'ell_eta','ell_U','sigma_U','W_cell','W_active','positions','permutation','sweep'})

    def test_exact_checkpoint_resume_archives(self):
        self.append();self.append(result=self.second,sweep=2)
        b=self.create('b')
        np.random.seed(491);eta=np.random.default_rng(193);gauge=np.random.default_rng(307);key=jax.random.PRNGKey(419)
        first=self.sweep.sweep(self.state,self.positions,self.tuning,eta_rng=eta,gauge_rng=gauge,
            master_key=key,state_factor_ids=self.target.factor_ids,label='sweep_0001')
        self.append(b,first)
        r=parse_json(self.contract.json)
        cc=CheckpointContract(json_text(r['continuation_contract']),r['continuation_sha256'])
        checkpoint=self.root/'checkpoint.npz'
        save_checkpoint_atomic(checkpoint,target=self.target,contract=cc,result=first,tuning=self.tuning,
            eta_rng=eta,gauge_rng=gauge,b_sigma2=self.scale,progress=dict(completed_local_sweep=1,
            settling_sweeps=0,completed_production_sweeps=1,checkpoint_type='complete',status='completed_sweep'))
        checkpoint_before=checkpoint.read_bytes()
        restored=load_checkpoint(checkpoint,target=self.target,contract=cc)
        b=ra.RetainedArchive(b.root,target=self.target,contract=self.contract,b_sigma2=self.scale)
        self.assertTrue(b.require_resume_boundary(restored))
        np.random.set_state(restored.numpy_global_state)
        second=self.sweep.sweep(restored.state,restored.positions,restored.tuning,eta_rng=restored.eta_rng,
            gauge_rng=restored.gauge_rng,master_key=restored.master_key,state_factor_ids=self.target.factor_ids,label='sweep_0002')
        self.append(b,second,sweep=2)
        self.assertEqual(record_result(second),record_result(self.second))
        self.assertEqual(self.archive.records,b.records)
        for i in (1,2):
            ma,aa,da=self.archive.read_retained(i);mb,ab,db=b.read_retained(i)
            self.assertEqual(ma,mb)
            for n in aa:np.testing.assert_array_equal(aa[n],ab[n])
        self.assertEqual(checkpoint.read_bytes(),checkpoint_before)
        with self.assertRaises(ValueError):b.require_resume_boundary(restored)
        type(self).continuation_receipt=dict(exact=True,retained_record_hashes=[m['logical_sha256'] for m in b.records],
            completed_sweeps=2,retained_draws=2,checkpoint_unchanged=True,
            complete_diagnostics_exact=True,four_rng_endpoints_exact=second.audit['rng_after']==self.second.audit['rng_after'])

    def test_failed_write_preserves_draws_and_attempt(self):
        self.append();before=self.path().read_bytes()
        def broken(path,data):Path(path).write_bytes(b'partial');raise OSError('interrupted')
        with patch.object(ra,'_write_npz',side_effect=broken),self.assertRaises(ra.ArchiveWriteError) as caught:
            self.append(result=self.second,sweep=2)
        self.assertTrue(caught.exception.attempt.exists());self.assertEqual(self.path().read_bytes(),before)
        self.assertEqual(self.archive.validate()['records'],1)

    def test_promotion_failure_preserves_existing(self):
        self.append();before=self.path().read_bytes()
        with patch.object(ra.os,'rename',side_effect=OSError('denied')),self.assertRaises(ra.ArchiveWriteError) as caught:
            self.append(result=self.second,sweep=2)
        self.assertTrue((caught.exception.attempt/'record.npz').exists())
        self.assertEqual(self.path().read_bytes(),before);self.assertEqual(self.archive.validate()['records'],1)

    def test_closed_candidate_validation_before_promotion(self):
        self.append();before=self.path().read_bytes()
        with patch.object(ra,'load_record',side_effect=ValueError('candidate invalid')),self.assertRaises(ra.ArchiveWriteError):
            self.append(result=self.second,sweep=2)
        self.assertEqual(self.path().read_bytes(),before)

    def test_duplicate_skipped_out_of_order_append(self):
        for i in (0,2,True):
            with self.assertRaises(ValueError):self.append(sweep=i)
        self.append()
        with self.assertRaises(ValueError):self.append()
        with self.assertRaises(FileExistsError):self.create('a')

    def test_missing_record_and_retained_gap(self):
        self.append();self.append(result=self.second,sweep=2)
        p=self.archive.root/'records'/'000000000001';p.rename(p.with_name('.attempt-hidden'))
        with self.assertRaises(ValueError):self.archive.validate()

    def test_rehashed_duplicate_retained_index(self):
        self.append();self.mutate(lambda a,m:m.update(retained_index=2),True)
        with self.assertRaises(ValueError):self.archive.validate()

    def test_changed_contract_identities(self):
        self.append()
        for key in ('chain_id','input_identity','geometry_identity','rule_identity','target_identity','factor_ids','git_commit','environment_lock_sha256','run_config_sha256'):
            r=parse_json(self.contract.json)
            if key=='chain_id':r[key]='another'
            elif key in ('git_commit','environment_lock_sha256','run_config_sha256'):r['continuation_contract']['software'][key]='0'*(40 if key=='git_commit' else 64)
            else:r['continuation_contract'][key]=['foreign'] if key=='factor_ids' else '{}'
            c=RetainedContract(json_text(r),digest(r))
            with self.subTest(key=key),self.assertRaises(ValueError):
                ra.RetainedArchive(self.archive.root,target=self.target,contract=c,b_sigma2=self.scale)

    def test_corrupted_arrays_and_metadata(self):
        self.append();original=self.path().read_bytes()
        for action in [lambda a,m:a['eta'].__setitem__((0,0),a['eta'][0,0]+1),lambda a,m:m.update(sweep=12),
                       lambda a,m:m.update(unknown=True),lambda a,m:a.pop('phi')]:
            self.path().write_bytes(original);self.mutate(action)
            with self.assertRaises(ValueError):self.archive.validate()

    def test_rehashed_bad_shapes_dtypes_and_coordinates(self):
        self.append();original=self.path().read_bytes()
        for action in [lambda a,m:a.update(eta=a['eta'].astype(np.float32)),lambda a,m:a.update(eta=a['eta'][:,:-1]),
                       lambda a,m:a['W_cell'].__setitem__((0,0,0),a['W_cell'][0,0,0]+1),
                       lambda a,m:a['positions'].__setitem__((0,4),a['positions'][0,4]+1)]:
            self.path().write_bytes(original);self.mutate(action,True)
            with self.assertRaises(ValueError):self.archive.validate()

    def test_object_and_truncated_npz(self):
        self.append();original=self.path().read_bytes()
        self.path().write_bytes(original[:100])
        with self.assertRaises(Exception):self.archive.validate()
        self.path().write_bytes(original)
        self.mutate(lambda a,m:a.update(eta=np.array([object()],object)))
        with self.assertRaises(ValueError):self.archive.validate()

    def test_warning_divergence_and_nonfinite_energy_preserved(self):
        result=copy.deepcopy(self.first);f=result.factor_diagnostics[0];info=f['transition'].info
        replacement=info._replace(is_divergent=np.array(True),block_divergent=np.array([True,False]),
            energy=np.array(np.inf),block_energy=np.array([np.inf,float(info.block_energy[1])]))
        f['transition']=replace(f['transition'],info=replacement)
        events=[dict(severity='warning',code='synthetic',message='visible test warning')]
        self.append(result=result,events=events)
        _,_,d=self.archive.read_retained(1)
        self.assertTrue(np.isinf(d['factors'][0]['info']['block_energy'][0]))
        self.assertEqual(d['events'],events)
        agg=ra.aggregate_archives([self.archive])['chains']['chain-A']
        self.assertGreaterEqual(agg['divergence_counts'][0],1);self.assertEqual(agg['events'][0]['code'],'synthetic')

    def test_failure_never_becomes_success(self):
        self.append()
        self.archive.record_failure(attempted_sweep=2,events=[dict(severity='failure',code='PCG',message='synthetic failure')],partial_diagnostics={'iterations':80})
        self.assertEqual(self.archive.validate()['status'],'failed')
        self.assertEqual(ra.aggregate_archives([self.archive])['chains']['chain-A']['status'],'failed')
        with self.assertRaises(ValueError):self.append(result=self.second,sweep=3)
        b=self.create('b')
        with self.assertRaises(ra.ArchiveWriteError) as caught:self.append(b,events=[dict(severity='failure',code='x',message='not success')])
        self.assertIsInstance(caught.exception.__cause__,ValueError)

    def test_no_mutation_or_rng_consumption(self):
        eta=np.random.default_rng(2);gauge=np.random.default_rng(3);key=jax.random.PRNGKey(4)
        before=stream_audit(eta,gauge,key,np.random.get_state());state_before=record_result(self.first)
        self.append();self.archive.validate();self.archive.read_retained(1);ra.aggregate_archives([self.archive])
        self.assertEqual(before,stream_audit(eta,gauge,key,np.random.get_state()))
        self.assertEqual(state_before,record_result(self.first))
        _,a,_=self.archive.read_retained(1);a['eta'][0,0]+=1
        self.assertEqual(state_before,record_result(self.first))

    def test_multichain_order_independent_and_duplicate_rejected(self):
        self.append();b=self.create('b',self.contract_for('chain-B'));self.append(b)
        self.append(result=self.second,sweep=2);self.append(b,self.second,2)
        expected=ra.aggregate_archives([self.archive,b])
        original=Path.iterdir
        with patch.object(Path,'iterdir',lambda p:iter(reversed(list(original(p))))):
            self.assertEqual(expected,ra.aggregate_archives([b,self.archive]))
        with self.assertRaises(ValueError):ra.aggregate_archives([self.archive,self.archive])

    def test_configurable_cadence_bounded_storage(self):
        sparse=self.create('sparse',self.contract_for(every=3,settling=1,final=None))
        self.append();self.append(result=self.second,sweep=2)
        self.append(sparse);self.append(sparse,self.second,2)
        self.assertEqual(sparse.validate()['retained'],0);self.assertEqual(self.archive.validate()['retained'],2)
        for i in (1,2):
            with np.load(sparse.root/'records'/f'{i:012d}'/'record.npz',allow_pickle=False) as f:self.assertEqual(f.files,['metadata'])
        self.assertLess(sum(p.stat().st_size for p in sparse.root.rglob('*.npz')),sum(p.stat().st_size for p in self.archive.root.rglob('*.npz')))
        p=parse_json(self.contract_for(every=3,settling=1,final=4).json)
        self.assertEqual([i for i in range(1,5) if retain_at(p,i)],[3,4])

    def test_logical_content_deterministic(self):
        self.append();b=self.create('b');self.append(b)
        self.assertEqual(self.archive.records,b.records)

    def test_stale_handle_rejected(self):
        other=ra.RetainedArchive(self.archive.root,target=self.target,contract=self.contract,b_sigma2=self.scale)
        self.append()
        with self.assertRaises(ValueError):self.append(other)

    def test_no_false_fidelity_or_convergence_claim(self):
        self.append();a=ra.aggregate_archives([self.archive])
        self.assertEqual(a['convergence_status'],'not_assessed')
        self.assertEqual(a['chains']['chain-A']['fidelity_status'],'not_evaluated_by_layers_1_to_8')

    def test_aggregate_finite_energy_semantics(self):
        self.append()
        aggregate=ra.aggregate_archives([self.archive])
        rows=aggregate['chains']['chain-A']['block_energy']
        for row, direct in zip(rows,self.first.factor_diagnostics):
            self.assertEqual(row['factor_id'],direct['factor_id'])
            self.assertEqual(row['block_order'],['field','hyper'])
            self.assertIsInstance(row['block_energy'],list)
            self.assertTrue(all(type(v) is float for v in row['block_energy']))
            np.testing.assert_array_equal(decode(row['block_energy']),np.asarray(direct['transition'].info.block_energy))
            self.assertNotIn('_array',json.dumps(row['block_energy'],allow_nan=False))
        serialized=json.dumps(aggregate,sort_keys=True,allow_nan=False)
        self.assertEqual(json.loads(serialized),aggregate)
        self.assertEqual(aggregate['logical_sha256'],digest({k:v for k,v in aggregate.items() if k!='logical_sha256'}))
        self.assertEqual(aggregate,ra.aggregate_archives([self.archive]))
        type(self).finite_energy_example=rows[0]

    def test_aggregate_divergent_nonfinite_energy_semantics(self):
        examples=[]
        for block in (0,1):
            for j,value in enumerate((np.inf,-np.inf,np.nan)):
                archive=self.create(f'nonfinite-{block}-{j}')
                result=copy.deepcopy(self.first);factor=result.factor_diagnostics[0];info=factor['transition'].info
                energies=np.array(info.block_energy,copy=True);energies[block]=value
                divergent=np.asarray(info.block_divergent).copy();divergent[block]=True
                factor['transition']=replace(factor['transition'],info=info._replace(
                    block_energy=energies,block_divergent=divergent,is_divergent=np.array(True),energy=energies[0]))
                self.append(archive,result)
                aggregate=ra.aggregate_archives([archive]);row=aggregate['chains']['chain-A']['block_energy'][0]
                self.assertEqual(row['block_order'],['field','hyper'])
                self.assertIsInstance(row['block_energy'],list)
                self.assertEqual(row['block_energy'][block],{'_nonfinite':str(float(value))})
                np.testing.assert_array_equal(decode(row['block_energy']),energies)
                text=json.dumps(aggregate,sort_keys=True,allow_nan=False)
                self.assertNotIn('_array',json.dumps(row['block_energy'],allow_nan=False))
                self.assertNotIn('Infinity',text);self.assertNotIn('NaN',text)
                self.assertEqual(aggregate,ra.aggregate_archives([archive]))
                self.assertEqual(aggregate['logical_sha256'],digest({k:v for k,v in aggregate.items() if k!='logical_sha256'}))
                examples.append(row)
        type(self).divergent_energy_examples=examples

    def test_state_rng_discontinuity_rejected(self):
        self.append()
        with self.assertRaises(ra.ArchiveWriteError):self.append(result=self.first,sweep=2)
        self.assertEqual(self.archive.validate()['records'],1)

    def test_new_diagnostic_unknown_field_rejected(self):
        self.append()
        self.mutate(lambda a,m:m['diagnostics'].update(unknown=True),True)
        with self.assertRaises(ValueError):self.archive.validate()

    def test_accepted_strict_w_bound_and_descriptor_types(self):
        result=copy.deepcopy(self.first);f=result.factor_diagnostics[0]
        f['transition']=replace(f['transition'],info=f['transition'].info._replace(hyper_W_relative_error=np.array(2e-8)))
        with self.assertRaises(ra.ArchiveWriteError):self.append(result=result)
        self.append()
        def alter(a,m):
            m['arrays']['eta']['shape'][0]=float(m['arrays']['eta']['shape'][0])
            m.pop('logical_sha256');m['logical_sha256']=digest(m)
        self.mutate(alter)
        with self.assertRaises(ValueError):self.archive.validate()


if __name__=='__main__':unittest.main()
