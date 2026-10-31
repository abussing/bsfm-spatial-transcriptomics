"""Orchestration fault injection uses synthetic bundle stubs, never real SCT fits."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from contextlib import ExitStack
from unittest.mock import patch

from bsfm.preprocessing import production_run as pr
from bsfm.preprocessing import source_attestation as sa
from bsfm.preprocessing import production_state as state
from bsfm.preprocessing.raw_preflight import ContractError
from bsfm.preprocessing.response_contract import (load_json, file_record, CONFIG, contract,
    require_clean_code, code_identity)


class SourceAndDurabilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.source = self.root/'raw'
        self.source.write_bytes(b'authenticated fixture')
        self.expected = {'bytes':self.source.stat().st_size,'sha256':hashlib.sha256(self.source.read_bytes()).hexdigest()}

    def test_attestation_in_process_only_expires_and_final_rehash(self):
        with patch.object(sa,'sha256_file',wraps=sa.sha256_file) as hash_file:
            with sa.source_session(self.source,self.expected) as (token,start):
                for _ in range(19): sa.check_attestation(token,self.source,self.expected)
                self.assertEqual(hash_file.call_count,1)
                with self.assertRaises(ContractError): sa.check_attestation(token.record(),self.source,self.expected)
                with self.assertRaises(ContractError): sa.check_attestation(token,self.root/'elsewhere',self.expected)
                with patch.object(sa.os,'getpid',return_value=-1),self.assertRaises(ContractError):
                    sa.check_attestation(token,self.source,self.expected)
                sa.final_authentication(token,self.source,self.expected)
                self.assertEqual(hash_file.call_count,2)
            with self.assertRaises(ContractError): sa.check_attestation(token,self.source,self.expected)

    def test_stat_changes_and_final_hash_change_fail(self):
        with sa.source_session(self.source,self.expected) as (token,start):
            with patch.object(sa,'sha256_file',return_value='0'*64),self.assertRaises(ContractError):
                sa.final_authentication(token,self.source,self.expected)
            self.source.write_bytes(b'changed')
            with self.assertRaises(ContractError): sa.check_attestation(token,self.source,self.expected)

    def test_wrong_expected_fingerprint_rejected(self):
        with self.assertRaises(ContractError),sa.source_session(self.source,{**self.expected,'sha256':'0'*64}): pass

    def test_atomic_file_fsynced_before_replace(self):
        target=self.root/'ledger.json'; state.atomic_json(target,{'generation':1})
        original_replace=state.os.replace; events=[]
        def replace(a,b):
            self.assertIn('fsync',events);self.assertEqual(load_json(target),{'generation':1})
            events.append('replace');original_replace(a,b)
        original_fsync=state.os.fsync
        def sync(fd): events.append('fsync');original_fsync(fd)
        with patch.object(state.os,'fsync',side_effect=sync),patch.object(state.os,'replace',side_effect=replace):
            state.atomic_json(target,{'generation':2})
        self.assertEqual(load_json(target),{'generation':2});self.assertEqual(events[-1],'fsync')
        with patch.object(state.os,'replace',side_effect=OSError('power loss')):
            with self.assertRaises(OSError):state.atomic_json(target,{'generation':3})
        self.assertEqual(load_json(target),{'generation':2})

    def test_cleanup_containment_and_failed_retention(self):
        root=state.layout(self.root/'run'); attempt=state.new_attempt(root,'section')
        (attempt/'payload').write_text('fixture')
        with self.assertRaises(ContractError):state.cleanup_attempt(root,root/'sections')
        outside=self.root/'.attempt-outside';outside.mkdir()
        with self.assertRaises(ContractError):state.cleanup_attempt(root,outside)
        (attempt/'failure.json').write_text('{}')
        with self.assertRaises(ContractError):state.cleanup_attempt(root,attempt)
        self.assertTrue((attempt/'payload').exists())
        (attempt/'failure.json').unlink()
        self.assertEqual(state.cleanup_attempt(root,attempt),'removed')
        self.assertEqual(state.cleanup_attempt(root,attempt),'already_absent')

    def test_cleanup_refuses_linked_descendant(self):
        root=state.layout(self.root/'run');attempt=state.new_attempt(root,'section')
        # Simulate a detected reparse point portably, without requiring link privileges.
        child=attempt/'linked';child.mkdir()
        original=Path.is_symlink
        with patch.object(Path,'is_symlink',lambda p: p==child or original(p)):
            with self.assertRaises(ContractError):state.cleanup_attempt(root,attempt)
        self.assertTrue(child.exists())

    @unittest.skipUnless(os.name == 'nt', 'Windows sharing-violation behavior')
    def test_transient_replace_failure_retries_atomic_rename(self):
        target=self.root/'ledger.json';state.atomic_json(target,{'generation':1})
        real=state.os.replace;calls=[]
        def replace(a,b):
            calls.append(1)
            if len(calls)==1:
                error=PermissionError('scanner holds file');error.winerror=32;raise error
            real(a,b)
        with patch.object(state.os,'replace',side_effect=replace),patch.object(state.time,'sleep'):
            state.atomic_json(target,{'generation':2})
        self.assertEqual(len(calls),2);self.assertEqual(load_json(target),{'generation':2})

    def test_clean_git_enforcement_with_actual_temporary_repository(self):
        repo=self.root/'repo';repo.mkdir();(repo/'tracked.txt').write_text('committed')
        subprocess.run(['git','init','-q',str(repo)],check=True)
        subprocess.run(['git','-C',str(repo),'add','tracked.txt'],check=True)
        subprocess.run(['git','-C',str(repo),'-c','user.name=Fixture','-c','user.email=fixture@example.invalid',
                        'commit','-qm','fixture'],check=True)
        commit=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
        fake={'commit':commit,'source_files':{'tracked.txt':hashlib.sha256(b'committed').hexdigest()}}
        with patch('bsfm.preprocessing.response_contract.REPO',repo),patch('bsfm.preprocessing.response_contract.code_identity',return_value=fake):
            self.assertEqual(require_clean_code(),fake)
            (repo/'untracked.txt').write_text('dirty')
            with self.assertRaises(ContractError):require_clean_code()
            (repo/'untracked.txt').unlink();(repo/'tracked.txt').write_text('dirty')
            with self.assertRaises(ContractError):require_clean_code()


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name);self.root=self.base/'run';self.raw=self.base/'raw'
        self.raw.write_bytes(b'raw fixture');self.env=self.base/'environment';self.env.mkdir()
        self.expected={'bytes':self.raw.stat().st_size,'sha256':hashlib.sha256(self.raw.read_bytes()).hexdigest()}
        self.code=code_identity();self.ids={k:'a'*64 for k in ['panel_registry_sha256','panel_order_sha256',
            'section_registry_sha256','bundle_spec_sha256','run_spec_sha256','environment_source_lock_sha256','renv_lock_sha256']}
        self.order=[s['section'] for s in contract()[3]['sections']];self.called=[]
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        original_load=pr.load_json
        def load(p):
            if str(p).replace('\\','/').endswith('20261030_raw/manifest.json'):return {'source':self.expected}
            return original_load(p)
        self.stack.enter_context(patch.object(pr,'load_json',side_effect=load))
        self.stack.enter_context(patch.object(pr,'require_clean_code',return_value=self.code))
        self.stack.enter_context(patch.object(pr,'identities',return_value=self.ids))
        self.resources=self.stack.enter_context(patch.object(pr,'resource_observation',return_value={
            'observed_at':'fixture','available_ram_bytes':16*1024**3,'free_disk_bytes':100*1024**3}))
        self.fit=self.stack.enter_context(patch.object(pr,'run_section',side_effect=self.stub_section))
        self.fast=self.stack.enter_context(patch.object(pr,'fast_validate_bundle',side_effect=self.stub_fast))

    def stub_section(self,section,source,env,config,root,*,attestation,run_spec_sha256,attempt):
        self.called.append(section);sa.check_attestation(attestation,source,self.expected)
        (attempt/'intermediate').write_text('temporary fixture')
        final=root/'sections'/section;self.assertFalse(final.exists());final.mkdir()
        for name in ['response.h5','fit.rds','session.txt','validation.json']:(final/name).write_text('synthetic stub, no scientific fit')
        state.atomic_json(final/'execution.json',{'attempt_id':attempt.name,'run_spec_sha256':run_spec_sha256})
        state.atomic_json(final/'manifest.json',{'section':section,'files':{p.name:file_record(p) for p in final.iterdir()}})
        return {'section':section,'attempt_id':attempt.name,'validation':'deep_saved_model_recorrection'}

    def stub_fast(self,bundle,section,source,env,config,digest):
        m=load_json(bundle/'manifest.json');e=load_json(bundle/'execution.json')
        if e['run_spec_sha256']!=digest:raise ContractError('incompatible fixture')
        for n,r in m['files'].items():
            if file_record(bundle/n)!=r:raise ContractError('corrupt fixture')
        return {'section':section,'manifest':file_record(bundle/'manifest.json'),'attempt_id':e['attempt_id'],
                'validation':'fast_closed_file_schema_hash_provenance','original_deep_validation':'pass'}

    def execute(self):return pr.execute(self.root,self.raw,self.env)
    def ledger(self):return load_json(self.root/'run-ledger.json')

    def test_all_19_order_shared_root_and_durable_cleanup(self):
        self.root.mkdir();result=self.execute()
        self.assertEqual(self.called,self.order);self.assertEqual(result['section_order'],self.order)
        self.assertEqual(len(result['sections']),19);self.assertEqual(self.ledger()['status'],'complete')
        self.assertEqual(list((self.root/'attempts').iterdir()),[])
        events=[e['event'] for e in self.ledger()['events']]
        self.assertLess(events.index('promoted'),events.index('cleanup_intent'))
        self.assertLess(events.index('cleanup_intent'),events.index('cleanup_complete'))
        self.assertEqual(result['source_start']['sha256'],result['source_final']['sha256'])

    def test_complete_resume_does_not_refit_or_replace_final_manifest(self):
        self.execute();before=(self.root/'run-manifest.json').read_bytes();self.called.clear()
        self.execute();self.assertEqual(self.called,[])
        self.assertEqual((self.root/'run-manifest.json').read_bytes(),before)

    def test_failure_stops_retains_and_fresh_resume_attempt(self):
        original=self.stub_section
        def fail(section,*args,**kwargs):
            if section==self.order[1]:
                (kwargs['attempt']/'failure.json').write_text('{}');raise RuntimeError('fit failed')
            return original(section,*args,**kwargs)
        self.fit.side_effect=fail
        with self.assertRaisesRegex(RuntimeError,'fit failed'):self.execute()
        self.assertFalse((self.root/'run-manifest.json').exists())
        self.assertEqual(self.called,[self.order[0]])
        failed=self.ledger()['sections'][self.order[1]]['attempts'][0]['id']
        self.fit.side_effect=self.stub_section;self.execute()
        self.assertTrue((self.root/'attempts'/failed/'failure.json').exists())
        self.assertEqual(len(self.ledger()['sections'][self.order[1]]['attempts']),2)

    def test_interruption_after_promotion_resumes_without_overwrite(self):
        def fail(section,*args,**kwargs):
            self.stub_section(section,*args,**kwargs);raise KeyboardInterrupt('after promotion')
        self.fit.side_effect=fail
        with self.assertRaises(KeyboardInterrupt):self.execute()
        before=(self.root/'sections'/self.order[0]/'manifest.json').read_bytes()
        self.fit.side_effect=self.stub_section;self.execute()
        self.assertEqual(self.called.count(self.order[0]),1)
        self.assertEqual((self.root/'sections'/self.order[0]/'manifest.json').read_bytes(),before)
        # Explicit failed attempts are kept, even if their final bundle is recovered.
        attempt=self.ledger()['sections'][self.order[0]]['attempts'][0]
        self.assertTrue((self.root/'attempts'/attempt['id']).exists())

    def test_incompatible_resume_and_corrupted_bundle(self):
        self.execute();spec=self.root/'run-specification.json';value=load_json(spec)
        value['policy']['concurrency']=2;state.atomic_json(spec,value)
        with self.assertRaisesRegex(ContractError,'Incompatible'):self.execute()

    def test_changed_commit_or_environment_rejects_resume(self):
        self.execute();self.called.clear()
        with patch.object(pr,'require_clean_code',return_value={**self.code,'commit':'f'*40}):
            with self.assertRaisesRegex(ContractError,'Incompatible'):self.execute()
        with patch.object(pr,'identities',return_value={**self.ids,'renv_lock_sha256':'f'*64}):
            with self.assertRaisesRegex(ContractError,'Incompatible'):self.execute()
        self.assertEqual(self.called,[])

    def test_power_loss_after_promotion_before_ledger_is_reconciled(self):
        def stop(section,*args,**kwargs):
            self.stub_section(section,*args,**kwargs);raise KeyboardInterrupt()
        self.fit.side_effect=stop
        with self.assertRaises(KeyboardInterrupt):self.execute()
        # Restore the last pre-promotion durable checkpoint as an abrupt process death would leave it.
        ledger=self.ledger();entry=ledger['sections'][self.order[0]]
        entry['state']='running';entry['attempts'][0]['state']='started'
        state.atomic_json(self.root/'run-ledger.json',ledger)
        self.fit.side_effect=self.stub_section;self.execute()
        self.assertEqual(self.called.count(self.order[0]),1)
        self.assertEqual(self.ledger()['sections'][self.order[0]]['attempts'][0]['cleanup'],'removed')

    def test_foreign_or_unlisted_final_directory_prevents_completion(self):
        def add_extra(section,*args,**kwargs):
            receipt=self.stub_section(section,*args,**kwargs)
            if section==self.order[-1]:(self.root/'sections'/'foreign').mkdir()
            return receipt
        self.fit.side_effect=add_extra
        with self.assertRaisesRegex(ContractError,'exactly all 19'):self.execute()
        self.assertFalse((self.root/'run-manifest.json').exists())

    def test_corrupt_completed_file_and_missing_final_are_not_refit(self):
        self.execute();self.called.clear();p=self.root/'sections'/self.order[0]/'fit.rds';p.write_text('corrupt')
        with self.assertRaises(ContractError):self.execute()
        self.assertEqual(self.called,[])

    def test_resource_floor_stops_before_fitting(self):
        for field in ['available_ram_bytes','free_disk_bytes']:
            with self.subTest(field=field):
                self.resources.return_value={'observed_at':'fixture','available_ram_bytes':20*1024**3,'free_disk_bytes':100*1024**3,field:0}
                with self.assertRaises(ContractError):self.execute()
                self.assertEqual(self.called,[]);self.assertFalse((self.root/'run-manifest.json').exists())
                self.assertEqual(self.ledger()['status'],'failed')

    def test_final_authentication_failure_cannot_complete(self):
        with patch.object(pr,'final_authentication',side_effect=ContractError('source changed')):
            with self.assertRaises(ContractError):self.execute()
        self.assertEqual(len(self.called),19);self.assertFalse((self.root/'run-manifest.json').exists())
        self.assertEqual(self.ledger()['status'],'failed')

    def test_all_19_required_even_if_ledger_claims_complete(self):
        self.execute();missing=self.root/'sections'/self.order[-1]
        for p in missing.iterdir():p.unlink()
        missing.rmdir();self.called.clear()
        with self.assertRaisesRegex(ContractError,'missing'):self.execute()
        self.assertEqual(self.called,[])

    def test_dirty_git_stops_before_artifacts(self):
        with patch.object(pr,'require_clean_code',side_effect=ContractError('dirty')):
            with self.assertRaises(ContractError):self.execute()
        self.assertFalse(self.root.exists());self.assertEqual(self.called,[])

    def test_cleanup_only_after_durable_promotion_checkpoint(self):
        original=pr.checkpoint
        def checkpoint(root,ledger,event,section=None):
            if event=='promoted':raise OSError('durability failure')
            return original(root,ledger,event,section)
        with patch.object(pr,'checkpoint',side_effect=checkpoint),patch.object(pr,'cleanup_attempt') as cleanup:
            with self.assertRaises(OSError):self.execute()
            cleanup.assert_not_called()
        self.assertTrue(any((self.root/'attempts').iterdir()))


if __name__=='__main__':unittest.main()
