"""Complete checkpoint identity, atomic failures and exact continuation."""
import copy
import csv
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
import warnings
import unittest
from unittest.mock import patch
import zipfile

import jax
import numpy as np
from threadpoolctl import threadpool_limits

from bsfm.sampler import checkpoint as cp
from bsfm.sampler.checkpoint_contract import (CheckpointContract, digest, validate_progress)
from bsfm.sampler.checkpoint_rng import (json_text, parse_json, generator_record, restore_generator,
                                       stream_audit, key_record, restore_key)
from bsfm.sampler.layer4 import STATE_ARRAYS, state_hashes
from sampler_layer6_support import fixture_system, record_result
from sampler_layer7_support import contract_for, progress, cheap_boundary, tuning_record, all_hashes, ROOT


class CheckpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.threads=threadpool_limits(limits=1);cls.threads.__enter__()
        cls.target,cls.state,cls.positions,cls.layer,cls.tuning,cls.scale=fixture_system()
        cls.contract=contract_for(cls.target,cls.scale)

    @classmethod
    def tearDownClass(cls):cls.threads.__exit__(None,None,None)

    def setUp(self):
        self.saved_global=np.random.get_state();np.random.seed(491)
        np.random.standard_normal()  # nonempty cached-normal state must survive
        self.eta=np.random.default_rng(193);self.gauge=np.random.default_rng(307)
        self.key=jax.random.PRNGKey(419)
        self.result=cheap_boundary(self.target,self.state,self.positions,self.key,self.scale,self.eta,self.gauge)
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'checkpoint.npz'

    def tearDown(self):np.random.set_state(self.saved_global)

    def save(self,path=None,**kwargs):
        args=dict(target=self.target,contract=self.contract,result=self.result,tuning=self.tuning,
                  eta_rng=self.eta,gauge_rng=self.gauge,b_sigma2=self.scale,progress=progress())
        args.update(kwargs)
        return cp.save_checkpoint_atomic(path or self.path,**args)

    def load(self,path=None,**kwargs):
        args=dict(target=self.target,contract=self.contract);args.update(kwargs)
        return cp.load_checkpoint(path or self.path,**args)

    def mutate(self,action,rehash=False):
        with np.load(self.path,allow_pickle=False) as f:data={k:f[k].copy() for k in f.files}
        meta=parse_json(str(data['metadata']));action(data,meta)
        if rehash:
            meta['arrays']={k:cp._descriptor(v) for k,v in data.items() if k!='metadata'}
            meta['logical_sha256']=digest({k:v for k,v in meta.items() if k!='logical_sha256'})
        data['metadata']=np.array(json_text(meta))
        np.savez_compressed(self.path,**data)

    def test_roundtrip_no_alias_and_no_stream_mutation(self):
        before=stream_audit(self.eta,self.gauge,self.key,np.random.get_state())
        receipt=self.save();loaded=self.load()
        self.assertEqual(before,stream_audit(self.eta,self.gauge,self.key,np.random.get_state()))
        self.assertEqual(before,stream_audit(loaded.eta_rng,loaded.gauge_rng,loaded.master_key,loaded.numpy_global_state))
        self.assertEqual(loaded.numpy_global_state[3],1)
        self.assertEqual(receipt['logical_sha256'],loaded.logical_sha256)
        self.assertEqual(tuning_record(loaded.tuning),tuning_record(self.tuning))
        for n in STATE_ARRAYS:
            np.testing.assert_array_equal(getattr(loaded.state,n),getattr(self.result.state,n))
            self.assertFalse(np.shares_memory(getattr(loaded.state,n),getattr(self.result.state,n)))
        for p,q in zip(loaded.positions,self.positions):
            self.assertFalse(np.shares_memory(p.values,q.values));np.testing.assert_array_equal(p.values,q.values)
        for a,b in zip(loaded.tuning,self.tuning):self.assertFalse(np.shares_memory(a.inverse_mass_matrix,b.inverse_mass_matrix))
        self.assertIsNot(loaded.eta_rng,self.eta);self.assertIsNot(loaded.gauge_rng,self.gauge)
        self.assertFalse(np.shares_memory(loaded.b_sigma2,self.scale))

    def test_logical_writes_deterministic(self):
        a=self.save();b=self.save(Path(self.tmp.name)/'second.npz')
        self.assertEqual(a['logical_sha256'],b['logical_sha256'])
        self.assertEqual(self.load().boundary,self.load(Path(self.tmp.name)/'second.npz').boundary)

    def test_atomic_write_failure_preserves_existing_and_reports_attempt(self):
        self.save();before=self.path.read_bytes()
        def broken(stream,**data):stream.write(b'interrupted');raise OSError('synthetic disk failure')
        with patch.object(cp.np,'savez_compressed',side_effect=broken):
            with self.assertRaises(cp.CheckpointWriteError) as caught:self.save()
        self.assertEqual(before,self.path.read_bytes())
        self.assertEqual(caught.exception.temporary_path.read_bytes(),b'interrupted')
        self.load()

    def test_replace_failure_preserves_existing_and_valid_attempt(self):
        self.save();before=self.path.read_bytes()
        with patch.object(cp.os,'replace',side_effect=OSError('synthetic replace failure')):
            with self.assertRaises(cp.CheckpointWriteError) as caught:self.save()
        self.assertEqual(before,self.path.read_bytes());self.load(caught.exception.temporary_path)

    def test_closed_temporary_validated_before_promotion(self):
        real=cp.os.replace;events=[]
        def promote(src,dst):
            self.load(src);events.append('validated closed file');return real(src,dst)
        with patch.object(cp.os,'replace',side_effect=promote):self.save()
        self.assertEqual(events,['validated closed file'])
        self.assertEqual(list(Path(self.tmp.name).glob('.*.attempt-*.npz')),[])

    def test_truncated_or_corrupted_archive_rejected(self):
        self.save();data=self.path.read_bytes()
        for bad in (data[:len(data)//2],b'not an NPZ',data[:40]+b'broken'+data[46:]):
            self.path.write_bytes(bad)
            with self.assertRaises((ValueError,OSError,zipfile.BadZipFile,EOFError)):self.load()

    def test_changed_value_and_dtype_rejected(self):
        for edit in ('value','dtype'):
            self.save()
            def action(d,m):
                if edit=='value':d['eta'][0,0]+=.01
                else:d['eta']=d['eta'].astype(np.float32)
            self.mutate(action)
            with self.assertRaises(ValueError):self.load()

    def test_missing_extra_and_object_arrays_rejected(self):
        for edit in ('missing','extra','object'):
            self.save()
            def action(d,m):
                if edit=='missing':del d['phi']
                elif edit=='extra':d['unapproved']=np.ones(1)
                else:d['eta']=np.array(['pickle'],dtype=object)
            self.mutate(action)
            with self.assertRaises(ValueError):self.load()

    def test_unknown_metadata_schema_and_fields_rejected(self):
        for edit in ('schema','extra','missing'):
            self.save()
            def action(d,m):
                if edit=='schema':m['schema']='bsfm.complete-checkpoint.v999'
                elif edit=='extra':m['unknown']=True
                else:del m['boundary']
            self.mutate(action,rehash=True)
            with self.assertRaises(ValueError):self.load()

    def test_wrong_software_run_and_environment_rejected(self):
        self.save()
        for name,value in [('git_commit','0'*40),('environment_lock_sha256','1'*64),('run_config_sha256','2'*64)]:
            r=parse_json(self.contract.json);r['software'][name]=value;r['software_sha256']=digest(r['software'])
            wrong=CheckpointContract(json_text(r),digest(r))
            with self.subTest(name=name),self.assertRaises(ValueError):self.load(contract=wrong)

    def test_wrong_target_input_mesh_rule_order_rejected(self):
        self.save()
        for name in ('target_identity','input_identity','geometry_identity','rule_identity','factor_ids'):
            r=parse_json(self.contract.json)
            if name=='factor_ids':r[name]=list(reversed(r[name]))
            else:r[name]+=' '
            wrong=CheckpointContract(json_text(r),digest(r))
            with self.subTest(name=name),self.assertRaises(ValueError):self.load(contract=wrong)
        self.mutate(lambda d,m:d.update(factor_ids=d['factor_ids'][::-1]),rehash=True)
        with self.assertRaises(ValueError):self.load()

    def test_spectral_corruption_never_replaces_target(self):
        self.save();before=self.target.geometry.spectral_identity
        self.mutate(lambda d,m:d['spectral_U'].__setitem__((0,0),d['spectral_U'][0,0]+.01),rehash=True)
        with self.assertRaisesRegex(ValueError,'Spectral'):self.load()
        self.assertEqual(before,self.target.geometry.spectral_identity);self.target.geometry.validate()

    def test_changed_scale_rejected(self):
        self.save();self.mutate(lambda d,m:d.update(b_sigma2=d['b_sigma2']*2),rehash=True)
        with self.assertRaises(ValueError):self.load()

    def test_malformed_progress_rejected(self):
        for name,value in [('completed_local_sweep',0),('settling_sweeps',-1),
                           ('completed_production_sweeps',True),('completed_production_sweeps',2),
                           ('checkpoint_type','legacy'),('status','incomplete')]:
            self.save();self.mutate(lambda d,m:m['progress'].__setitem__(name,value),rehash=True)
            with self.subTest(name=name),self.assertRaises(ValueError):self.load()
        self.assertEqual(validate_progress(progress(1,3))['completed_production_sweeps'],0)

    def test_invalid_rng_type_state_and_cached_normal(self):
        for edit in ('type','state','global','key'):
            self.save()
            def action(d,m):
                if edit=='type':m['rng']['eta']['type']='untrusted-module.Class'
                elif edit=='state':m['rng']['gauge']['state']['extra']=1
                elif edit=='global':m['rng']['numpy_global']['has_gauss']=2
                else:m['rng']['jax']['implementation']='rbg'
            self.mutate(action,rehash=True)
            before=stream_audit(self.eta,self.gauge,self.key,np.random.get_state())
            with self.assertRaises(ValueError):self.load()
            self.assertEqual(before,stream_audit(self.eta,self.gauge,self.key,np.random.get_state()))

    def test_supported_rng_types_and_typed_key_lossless(self):
        for name in ('PCG64','PCG64DXSM','MT19937','Philox','SFC64'):
            rng=np.random.Generator(getattr(np.random,name)(45));rng.standard_normal(3)
            restored=restore_generator(generator_record(rng))
            np.testing.assert_array_equal(rng.standard_normal(17),restored.standard_normal(17))
        key=jax.random.key(13);record,data=key_record(key);restored=restore_key(record,data)
        self.assertEqual(record,key_record(restored)[0]);np.testing.assert_array_equal(data,key_record(restored)[1])

    def test_failed_load_never_mutates_state_tuning_or_generators(self):
        self.save();before=state_hashes(self.state);tunes=tuning_record(self.tuning)
        streams=stream_audit(self.eta,self.gauge,self.key,np.random.get_state())
        self.mutate(lambda d,m:d['loading'].__setitem__((0,0,0),np.nan))
        with self.assertRaises(ValueError):self.load()
        self.assertEqual(before,state_hashes(self.state));self.assertEqual(tunes,tuning_record(self.tuning))
        self.assertEqual(streams,stream_audit(self.eta,self.gauge,self.key,np.random.get_state()))

    def test_stale_rng_or_incoherent_boundary_cannot_be_saved(self):
        self.eta.standard_normal()
        with self.assertRaises(ValueError):self.save()
        self.assertFalse(self.path.exists())
        result=replace(self.result,fitted_Y=self.result.fitted_Y+.01)
        with self.assertRaises(ValueError):self.save(result=result)

    def test_temporary_validation_failure_preserves_final(self):
        self.save();before=self.path.read_bytes()
        with patch.object(cp,'load_checkpoint',side_effect=ValueError('synthetic validation failure')):
            with self.assertRaises(cp.CheckpointWriteError) as caught:self.save()
        self.assertEqual(before,self.path.read_bytes());self.load(caught.exception.temporary_path)

    def test_rehashed_invalid_shapes_domains_and_tuning(self):
        for edit in ('dtype','shape','nan','domain','step','mass','binding'):
            self.save()
            def action(d,m):
                if edit=='dtype':d['eta']=d['eta'].astype(np.float32)
                elif edit=='shape':d['eta']=d['eta'][:,:-1]
                elif edit=='nan':d['sigma2'][0]=np.nan
                elif edit=='domain':d['zeta'][0]=1.
                elif edit=='step':d['hyper_steps'][0]=0.
                elif edit=='mass':d['inverse_mass'][0,0]=-1.
                else:m['tuning_bindings'][0]['target_identity']='foreign'
            self.mutate(action,rehash=True)
            with self.subTest(edit=edit),self.assertRaises(ValueError):self.load()

    def test_duplicate_json_and_archive_fields_rejected(self):
        self.save()
        self.mutate(lambda d,m:m['progress'].update(unknown=True),rehash=True)
        with self.assertRaises(ValueError):self.load()
        self.save()
        with np.load(self.path,allow_pickle=False) as f:data={k:f[k].copy() for k in f.files}
        text=str(data['metadata']);data['metadata']=np.array('{"schema":"extra",'+text[1:])
        np.savez_compressed(self.path,**data)
        with self.assertRaisesRegex(ValueError,'Duplicate JSON'):self.load()
        self.save()
        with warnings.catch_warnings():
            warnings.simplefilter('ignore',UserWarning)
            with zipfile.ZipFile(self.path,'a') as f:f.writestr('eta.npy',f.read('eta.npy'))
        with self.assertRaisesRegex(ValueError,'Duplicate archive'):self.load()

    def test_binding_and_spectral_audit_unknown_fields_rejected(self):
        for field in ('position_bindings','tuning_bindings','spectral_audit'):
            self.save()
            def action(d,m):
                if field=='spectral_audit':m[field]['unapproved']=1
                else:m[field][0]['unapproved']=1
            self.mutate(action,rehash=True)
            with self.subTest(field=field),self.assertRaises(ValueError):self.load()

    def test_typed_key_and_other_generator_checkpoint_roundtrip(self):
        eta=np.random.Generator(np.random.MT19937(21));gauge=np.random.Generator(np.random.Philox(23))
        key=jax.random.key(41)
        result=cheap_boundary(self.target,self.state,self.positions,key,self.scale,eta,gauge)
        self.save(result=result,eta_rng=eta,gauge_rng=gauge)
        restored=self.load()
        self.assertEqual(key_record(restored.master_key)[0]['representation'],'typed')
        self.assertEqual(generator_record(eta),generator_record(restored.eta_rng))
        self.assertEqual(generator_record(gauge),generator_record(restored.gauge_rng))

    def test_source_map_schema_and_no_legacy_conversion(self):
        with (ROOT/'docs/sampler/LAYER7_SOURCE_MAP.csv').open(newline='') as f:rows=list(csv.DictReader(f))
        self.assertEqual(len(rows),7)
        for row in rows:
            self.assertEqual(row['source_sha256'],'943a934c35a862bbc8b2d7dd80bc81ea98987e8ef10d9e7cfb152d485094b111')
            self.assertEqual(int(row['source_bytes']),6593)
            self.assertEqual(hashlib.sha256((ROOT/row['port_path']).read_bytes()).hexdigest(),row['port_file_sha256'])
        schema=json.loads((ROOT/'config/sampler/checkpoint-v1.schema.json').read_text())
        self.save()
        with np.load(self.path,allow_pickle=False) as f:meta=parse_json(str(f['metadata']))
        self.assertEqual(set(schema['required']),set(meta))
        self.assertFalse(schema['additionalProperties'])
        self.assertFalse(hasattr(cp,'load_legacy'))

    def test_exact_two_arm_continuation(self):
        def start():
            np.random.seed(491)
            return np.random.default_rng(193),np.random.default_rng(307),jax.random.PRNGKey(419)
        def sweep(state,ps,tunes,eta,gauge,key,label):
            return self.layer.sweep(state,ps,tunes,eta_rng=eta,gauge_rng=gauge,master_key=key,
                                   state_factor_ids=self.target.factor_ids,label=label)
        eta,gauge,key=start()
        a1=sweep(self.state,self.positions,self.tuning,eta,gauge,key,'sweep_0001')
        a2=sweep(a1.state,a1.positions,self.tuning,eta,gauge,a1.master_key,'sweep_0002')
        a_streams=stream_audit(eta,gauge,a2.master_key,np.random.get_state())
        eta,gauge,key=start()
        b1=sweep(self.state,self.positions,self.tuning,eta,gauge,key,'sweep_0001')
        self.assertEqual(record_result(a1),record_result(b1));self.assertEqual(a1.audit,b1.audit)
        receipt=self.save(result=b1,eta_rng=eta,gauge_rng=gauge)
        global_before=np.random.get_state()
        restored=self.load()
        self.assertEqual(stream_audit(eta,gauge,b1.master_key,np.random.get_state()),
                         stream_audit(eta,gauge,b1.master_key,global_before))
        np.random.set_state(restored.numpy_global_state)  # caller's explicit action
        b2=sweep(restored.state,restored.positions,restored.tuning,restored.eta_rng,restored.gauge_rng,
                 restored.master_key,'sweep_0002')
        self.assertEqual(record_result(a2),record_result(b2));self.assertEqual(a2.audit,b2.audit)
        self.assertEqual(tuning_record(self.tuning),tuning_record(restored.tuning))
        self.assertEqual(a_streams,stream_audit(restored.eta_rng,restored.gauge_rng,b2.master_key,np.random.get_state()))
        type(self).continuation_receipt=dict(status='PASS',same_environment_exact=True,
            uninterrupted=all_hashes(a2),restarted=all_hashes(b2),checkpoint_logical_sha256=receipt['logical_sha256'],
            checkpoint_bytes=receipt['bytes'],tuning=tuning_record(restored.tuning),
            all_state_positions_diagnostics_and_audits_exact=True,all_four_rng_endpoints_exact=True,
            caller_installed_global_state=True,software=parse_json(self.contract.json)['software'],
            limitations=['Windows CPU synthetic K=2; not a production runner or scientific fit',
                         'Software declaration identifies the clean baseline plus uncommitted review code (clean_tree=false)'])


if __name__=='__main__':unittest.main()
