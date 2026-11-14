"""Real transitions: interrupted parent -> frozen settling -> retuning child."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from test_meeting_extensions import setup
from bsfm.sampler.run_periodic import PeriodicRunController,PeriodicReadaptationController
from bsfm.sampler.run_checkpoint_fork import CheckpointForkController,source_endpoint
from bsfm.sampler.run_genesis import load_genesis,boundary
from bsfm.sampler.run_storage import file_record,read_json
from bsfm.sampler.run_readaptation import parent_endpoint
from bsfm.sampler.checkpoint_contract import digest
from bsfm.sampler.compact_checkpoint import load_compact
from bsfm.sampler.run_health import review_windows


class Stop(BaseException):pass


class ForkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup)
        cls.root=Path(cls.tmp.name);base=setup(cls.root/'parent','deep')
        spec=copy.deepcopy(base.spec);spec.update(final_sweep=3,production_sweeps=3)
        spec['software']['environment_identity']='a'*64
        cls.parent=PeriodicRunController(base.store.root,base.target,base.loading,base.eta,spec,
            base.store.input_receipt,authenticate=base.authenticate)
        cls.parent.run(stop_after=1)
        c=cls.parent;s=c.store.segment
        paths=dict(spec=c.store.root/'run-spec.json',inputs=c.store.root/'input-receipt.json',
            genesis=s/'genesis/endpoint.npz',genesis_receipt=s/'genesis/receipt.json',
            boundary_receipt=s/'boundaries/000000000001/receipt.json')
        cls.source={k:dict(path=str(p),**file_record(p)) for k,p in paths.items()}

    def make(self,name,diagnostics=False,scales=None):
        p=self.parent;spec=copy.deepcopy(p.spec)
        spec.update(run_id='settle',warmup_steps=0,final_sweep=2,production_sweeps=2)
        binding=dict(p.store.input_receipt,initial_checkpoint=self.source)
        if diagnostics:binding['diagnostics']='adaptation_study_v1'
        if scales is not None:binding['checkpoint_field_step_scales']=scales
        spec['input_sha256']=digest(binding)
        return CheckpointForkController(self.root/name,p.target,p.loading,p.eta,spec,binding,authenticate=p.authenticate)

    def test_incomplete_parent_and_exact_rng_then_retuning(self):
        self.assertFalse((self.parent.store.segment/'completion.json').exists())
        c=self.make('child')
        with patch('bsfm.sampler.run_controller.initialize',side_effect=AssertionError('Reinitialize')), \
             patch('bsfm.sampler.run_controller.adapt',side_effect=AssertionError('Retune')):
            c.run()
        inherited,_=load_genesis(c.store.segment/'genesis/endpoint.npz',c.target,c.cp)
        original=load_compact(self.parent.store.segment/'boundaries/000000000001/checkpoint.npz',target=c.target,contract=self.parent.cp)
        self.assertEqual(boundary(inherited,c.target),boundary(original,c.target))
        self.assertEqual(inherited.evidence['adaptation_steps'],0)
        self.parent.run()
        expected=load_compact(self.parent.store.segment/'boundaries/000000000003/checkpoint.npz',target=c.target,contract=self.parent.cp)
        actual,binding=parent_endpoint(c)
        self.assertEqual(boundary(actual,c.target),boundary(expected,c.target))
        child_spec=copy.deepcopy(c.spec);child_spec.update(run_id='retune',warmup_steps=20,final_sweep=1,production_sweeps=1)
        child_binding=dict(c.store.input_receipt,readaptation_parent=binding,diagnostics='adaptation_study_v1')
        child_spec['input_sha256']=digest(child_binding)
        retune=PeriodicReadaptationController(self.root/'retune',c.target,c.loading,c.eta,child_spec,child_binding,authenticate=c.authenticate,parent=c)
        retune.run()
        e,_=load_genesis(retune.store.segment/'genesis/endpoint.npz',c.target,retune.cp)
        self.assertIn('conditional_replay',e.evidence['factors'][0])
        self.assertEqual(e.evidence['initialization']['parent'],binding)

    def test_interrupted_fork_recovery_and_nonreplay(self):
        reference=self.make('reference');reference.run()
        for stage in ('before_genesis_publish','after_sweep','before_boundary_publish','after_boundary_publish'):
            c=self.make(stage)
            def stop(s):
                if s==stage:raise Stop()
            with self.assertRaises(Stop):c.run(fault=stop)
            c=self.make(stage);c.run()
            for n in (1,2):
                p=f'boundaries/{n:012d}/receipt.json'
                self.assertEqual(read_json(c.store.segment/p),read_json(reference.store.segment/p))
            with patch.object(c.layer,'sweep',side_effect=AssertionError('Replay')):c.run()

    def test_source_tamper_runtime_and_containment_rejected(self):
        p=self.parent;args=dict(seed=p.spec['seed'],environment_identity=p.spec['software']['environment_identity'],output=self.root/'reject')
        for changes in (dict(seed=492),dict(environment_identity='other-device'),dict(output=p.store.root/'child')):
            with self.assertRaises(ValueError):source_endpoint(self.source,p.target,p.loading,p.eta,**dict(args,**changes))
        record=Path(self.source['boundary_receipt']['path']);raw=record.read_bytes()
        try:
            record.write_bytes(raw+b' ')
            with self.assertRaises(ValueError):source_endpoint(self.source,p.target,p.loading,p.eta,**args)
        finally:record.write_bytes(raw)

    def test_diagnostic_recording_preserves_numerical_endpoint(self):
        a=self.make('plain');b=self.make('diagnostic',True);a.run();b.run()
        ae,_=parent_endpoint(a);be,_=parent_endpoint(b)
        self.assertEqual(boundary(ae,a.target),boundary(be,b.target))
        row=read_json(b.store.segment/'boundaries/000000000002/diagnostics.json')[0]
        self.assertEqual(len(row['measurements']['factors']),len(b.target.factor_ids))

    def test_explicit_runtime_migration_preserves_import_and_destination_restart(self):
        migration=dict(schema='bsfm.checkpoint-runtime-migration.v1',
            source_environment_identity='a'*64,destination_environment_identity='b'*64)
        base=self.make('migration-base')
        spec=copy.deepcopy(base.spec);spec['software']['environment_identity']='b'*64
        binding=dict(base.store.input_receipt,checkpoint_runtime_migration=migration)
        spec['input_sha256']=digest(binding)
        def make(name):
            return CheckpointForkController(self.root/name,base.target,base.loading,base.eta,
                spec,binding,authenticate=base.authenticate)
        reference=make('migration-reference');reference.run()
        c=make('migration-interrupted')
        def stop(stage):
            if stage=='after_sweep':raise Stop()
        with self.assertRaises(Stop):c.run(fault=stop)
        c=make('migration-interrupted');c.run()
        inherited,_=load_genesis(c.store.segment/'genesis/endpoint.npz',c.target,c.cp)
        original=load_compact(self.parent.store.segment/'boundaries/000000000001/checkpoint.npz',
            target=c.target,contract=self.parent.cp)
        self.assertEqual(boundary(inherited,c.target),boundary(original,c.target))
        from bsfm.sampler.run_transactions import tuning_identity
        self.assertEqual(tuning_identity(inherited.tuning),tuning_identity(original.tuning))
        self.assertEqual(inherited.evidence['source']['runtime_migration'],migration)
        self.assertEqual(boundary(parent_endpoint(c)[0],c.target),
                         boundary(parent_endpoint(reference)[0],c.target))
        with patch.object(c.layer,'sweep',side_effect=AssertionError('Replay')):c.run()
        args=dict(seed=c.spec['seed'],environment_identity='b'*64,output=self.root/'reject-migration')
        for changed in (dict(migration,source_environment_identity='c'*64),
                        dict(migration,destination_environment_identity='c'*64)):
            with self.assertRaises(ValueError):
                source_endpoint(self.source,c.target,c.loading,c.eta,**args,runtime_migration=changed)

    def test_migration_only_bounds_derived_warp_roundoff(self):
        from bsfm.sampler.retained_records import physical_arrays
        p=self.parent
        args=dict(seed=p.spec['seed'],environment_identity='a'*64,output=self.root/'roundoff')
        migration=dict(schema='bsfm.checkpoint-runtime-migration.v1',
            source_environment_identity='a'*64,destination_environment_identity='b'*64)
        def shifted(amount):
            def evaluate(*values):return tuple(v+amount for v in physical_arrays(*values))
            return evaluate
        with patch('bsfm.sampler.retained_records.physical_arrays',side_effect=shifted(1e-12)):
            with self.assertRaisesRegex(ValueError,'Physical warp reconstruction'):
                source_endpoint(self.source,p.target,p.loading,p.eta,**args)
            _,binding=source_endpoint(self.source,p.target,p.loading,p.eta,
                **dict(args,environment_identity='b'*64),runtime_migration=migration)
            error=binding['physical_warp_reconstruction'][0]['max_absolute_error']
            self.assertGreater(error,0);self.assertLess(error,2e-10)
        with patch('bsfm.sampler.retained_records.physical_arrays',side_effect=shifted(1e-7)):
            with self.assertRaisesRegex(ValueError,'exceeds 2e-10'):
                source_endpoint(self.source,p.target,p.loading,p.eta,
                    **dict(args,environment_identity='b'*64),runtime_migration=migration)

    def test_migration_audits_derived_fitted_digest_but_keeps_state_exact(self):
        from contextlib import ExitStack
        from bsfm.sampler.conjugate import compute_Yhat
        p=self.parent
        args=dict(seed=p.spec['seed'],environment_identity='a'*64,output=self.root/'fitted-roundoff')
        migration=dict(schema='bsfm.checkpoint-runtime-migration.v1',
            source_environment_identity='a'*64,destination_environment_identity='b'*64)
        def shifted(*values):return compute_Yhat(*values)+1e-15
        with ExitStack() as stack:
            for module in ['run_genesis','checkpoint','retained_records']:
                stack.enter_context(patch('bsfm.sampler.'+module+'.compute_Yhat',side_effect=shifted))
            with self.assertRaisesRegex(ValueError,'Genesis boundary changed'):
                source_endpoint(self.source,p.target,p.loading,p.eta,**args)
            migrated,binding=source_endpoint(self.source,p.target,p.loading,p.eta,
                **dict(args,environment_identity='b'*64),runtime_migration=migration)
        original=load_compact(p.store.segment/'boundaries/000000000001/checkpoint.npz',target=p.target,contract=p.cp)
        self.assertEqual(boundary(migrated,p.target),boundary(original,p.target))
        self.assertEqual(migrated.boundary,original.boundary)
        audit=binding['fitted_value_reconstruction']
        self.assertEqual(len(audit),3)
        self.assertTrue(all(not row['equal'] for row in audit))
        from bsfm.sampler.migration_boundary import same_boundary
        saved=boundary(original,p.target);changed=dict(saved,rng_after={'bad':'rng'})
        self.assertFalse(same_boundary(changed,saved,migration_audit=[]))
        changed=dict(saved,state_after={'bad':'state'})
        self.assertFalse(same_boundary(changed,saved,migration_audit=[]))
        with patch('bsfm.sampler.run_genesis.descriptor',return_value={}):
            with self.assertRaisesRegex(ValueError,'array hash mismatch'):
                source_endpoint(self.source,p.target,p.loading,p.eta,
                    **dict(args,environment_identity='b'*64),runtime_migration=migration)

    def test_reviewed_reduction_preserves_state_rng_and_resumes_once(self):
        scales={fid:(.5 if i==0 else 1.) for i,fid in enumerate(self.parent.target.factor_ids)}
        reference=self.make('scaled-reference',True,scales);reference.run()
        c=self.make('scaled-interrupted',True,scales)
        def stop(stage):
            if stage=='after_boundary_publish':raise Stop()
        with self.assertRaises(Stop):c.run(fault=stop)
        c=self.make('scaled-interrupted',True,scales);c.run()
        inherited,_=load_genesis(c.store.segment/'genesis/endpoint.npz',c.target,c.cp)
        original=load_compact(self.parent.store.segment/'boundaries/000000000001/checkpoint.npz',target=c.target,contract=self.parent.cp)
        self.assertEqual(boundary(inherited,c.target),boundary(original,c.target))
        for old,new in zip(original.tuning,inherited.tuning):
            self.assertEqual(new.step_size,old.step_size*scales[old.factor_id])
            self.assertEqual(new.hyper_step_size,old.hyper_step_size)
            np.testing.assert_array_equal(new.inverse_mass_matrix,old.inverse_mass_matrix)
        for n in (1,2):
            # Instrumentation includes real elapsed seconds, so receipts differ.
            # The scientific state and all RNG streams must still agree exactly.
            path=f'boundaries/{n:012d}/checkpoint.npz'
            actual=load_compact(c.store.segment/path,target=c.target,contract=c.cp)
            expected=load_compact(reference.store.segment/path,target=c.target,contract=reference.cp)
            self.assertEqual(boundary(actual,c.target),boundary(expected,c.target))
        with patch.object(c.layer,'sweep',side_effect=AssertionError('Replay')):c.run()
        # Published adjusted genesis remains usable as an authenticated source.
        source={key:dict(path=str(path),**file_record(path)) for key,path in dict(
            spec=c.store.root/'run-spec.json',inputs=c.store.root/'input-receipt.json',
            genesis=c.store.segment/'genesis/endpoint.npz',genesis_receipt=c.store.segment/'genesis/receipt.json',
            boundary_receipt=c.store.segment/'boundaries/000000000002/receipt.json').items()}
        endpoint,_=source_endpoint(source,c.target,c.loading,c.eta,seed=c.spec['seed'],
            environment_identity=c.spec['software']['environment_identity'],output=self.root/'next-source-check')
        self.assertEqual(boundary(endpoint,c.target),boundary(parent_endpoint(c)[0],c.target))
        changed=dict(scales);changed[c.target.factor_ids[0]]=.25
        with self.assertRaises(ValueError):self.make('scaled-interrupted',True,changed).run()

    def test_warmup_context_capture_preserves_endpoint_and_streams(self):
        from bsfm.sampler.run_initialization import initialize,adapt
        from bsfm.sampler.run_transactions import tuning_identity
        p=self.parent
        initial,keys=initialize(p.target,p.loading,p.eta,seed=p.spec['seed'])
        a=adapt(p.target,copy.deepcopy(initial),keys,steps=20,split=p.layer.split)
        b=adapt(p.target,copy.deepcopy(initial),keys,steps=20,split=p.layer.split,record_context=True)
        self.assertEqual(boundary(a,p.target),boundary(b,p.target))
        self.assertEqual(tuning_identity(a.tuning),tuning_identity(b.tuning))
        from bsfm.sampler.retained_diagnostics import decode
        for row in b.evidence['factors']:
            context=decode(row['conditional_replay'])
            self.assertTrue(np.isfinite(context['u']).all())
            self.assertTrue(np.isfinite(context['ct']).all())


class HealthTests(unittest.TestCase):
    def test_runtime_migration_recipe_requires_validated_destination_and_pinned_source(self):
        import json
        from bsfm.sampler.run import validate_recipe
        root=Path(__file__).resolve().parents[1]
        recipe=json.loads((root/'config/sampler/shared-command-gpu-deep-validation.json').read_text())
        recipe['gpu_runtime']={'schema':'bsfm.validated-gpu-runtime.v1','blas_threads':1}
        recipe['initial_checkpoint']={k:dict(path='/source/'+k,bytes=1,sha256='c'*64)
            for k in ('spec','inputs','genesis','genesis_receipt','boundary_receipt')}
        recipe['phases'][0]['warmup_steps']=0
        recipe['checkpoint_runtime_migration']=dict(schema='bsfm.checkpoint-runtime-migration.v1',
            source_environment_identity='a'*64,destination_environment_identity='b'*64)
        validate_recipe(recipe)
        for field,value in [('initial_checkpoint',None),('gpu_runtime',{'blas_threads':1}),
                            ('checkpoint_runtime_migration',{'source_environment_identity':'a'*64})]:
            bad=copy.deepcopy(recipe)
            if value is None:bad.pop(field)
            else:bad[field]=value
            with self.assertRaises(ValueError):validate_recipe(bad)

    def test_periodic_health_selects_blocks_from_model(self):
        from types import SimpleNamespace
        from bsfm.sampler.flat_control import FlatTarget
        from bsfm.sampler.run_periodic import PeriodicMixin
        from bsfm.sampler.run_storage import write_json
        rows=[dict(factors=[dict(index=0,acceptance=[.9,0.],
                    divergent=[False,False],leapfrogs=[7,0])]) for _ in range(50)]
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);segment=root/'segments/segment'
            dest=segment/'boundaries/000000000050';dest.mkdir(parents=True)
            write_json(dest/'diagnostics.json',rows)
            controller=PeriodicMixin()
            controller.store=SimpleNamespace(input_receipt={'diagnostics':'adaptation_study_v1'},
                                              root=root,segment=segment)
            controller.target=object.__new__(FlatTarget)
            self.assertIsNone(controller._health({'n':50,'head':'test'}))
            controller.target=object()
            self.assertEqual(controller._health({'n':50,'head':'test'})['flags'][0]['block'],'hyper')

    def test_flat_placeholder_is_ignored_but_active_failures_still_stop(self):
        rows=[dict(factors=[dict(index=0,acceptance=[.9,0.],
                    divergent=[False,False],leapfrogs=[7,0])]) for _ in range(50)]
        result=review_windows(rows,active_blocks=('field',))
        self.assertEqual(result['status'],'no_persistent_guard_failure')
        self.assertEqual([v['block'] for v in result['windows']],['field'])
        # Deep still checks both blocks; a zero-step block is not auto-disabled.
        self.assertEqual(review_windows(rows)['flags'][0]['block'],'hyper')
        for row in rows:row['factors'][0]['acceptance'][0]=.2
        self.assertEqual(review_windows(rows,active_blocks=('field',))['flags'][0]['reasons'],
                         ['persistent_low_acceptance'])
        for row in rows:
            row['factors'][0]['acceptance'][0]=.9
            row['factors'][0]['divergent'][0]=True
        self.assertEqual(review_windows(rows,active_blocks=('field',))['flags'][0]['reasons'],
                         ['persistent_divergences'])
        for blocks in [(),('unused',),('field','field')]:
            with self.assertRaises(ValueError):review_windows(rows,active_blocks=blocks)

    def test_caps_warn_but_persistent_block_failures_stop(self):
        rows=[dict(factors=[dict(index=1,acceptance=[.99,.99],divergent=[False,False],leapfrogs=[1023,3]),
                           dict(index=0,acceptance=[.9,.9],divergent=[False,False],leapfrogs=[7,3])]) for _ in range(50)]
        self.assertEqual(review_windows(rows)['status'],'no_persistent_guard_failure')
        for row in rows:row['factors'].reverse()
        for row in rows[:25]:next(r for r in row['factors'] if r['index']==1)['acceptance'][0]=.4
        self.assertEqual(review_windows(rows)['status'],'no_persistent_guard_failure')
        for row in rows[25:]:next(r for r in row['factors'] if r['index']==1)['acceptance'][0]=.4
        r=review_windows(rows);self.assertEqual(r['status'],'review_required')
        self.assertEqual(r['flags'][0]['factor'],2)


if __name__=='__main__':unittest.main()
