"""Fork a published periodic boundary without completing or editing its parent.

The source chain is checked under its original contracts. The new lineage keeps
state and every RNG stream, with an optional explicit field-step reduction.
It performs no initialization or adaptation and may subsequently feed the
existing readaptation controller.
"""
import copy
from dataclasses import replace
from pathlib import Path
from .checkpoint_contract import digest
from .run_genesis import load_genesis, boundary
from .run_initialization import Endpoint
from .run_inputs import authenticate_files
from .run_periodic import PeriodicRunController
from .run_storage import file_record, read_json, safe, writer
from .run_transactions import tuning_identity
from .run import validate_checkpoint_source as validate_source, validate_field_step_scales, validate_runtime_migration
from .migration_boundary import migration_chart_validation


def source_endpoint(source,target,loading,eta,*,seed,environment_identity,output,runtime_migration=None):
    """Read only the authenticated published prefix ending at the pinned receipt."""
    validate_source(source);authenticate_files(source)
    paths={k:safe(safe(v['path']).resolve()) for k,v in source.items()}
    root=paths['spec'].parent
    if root.is_relative_to(Path(output).resolve()) or Path(output).resolve().is_relative_to(root):
        raise ValueError('Checkpoint fork requires disjoint source and output roots')
    spec=read_json(paths['spec']);inputs=read_json(paths['inputs'])
    expected_environment=environment_identity
    if runtime_migration is not None:
        validate_runtime_migration(runtime_migration)
        if runtime_migration['destination_environment_identity']!=environment_identity:
            raise ValueError('Runtime migration destination identity mismatch')
        expected_environment=runtime_migration['source_environment_identity']
    if spec['seed']!=seed or spec['software']['environment_identity']!=expected_environment:
        raise ValueError('Checkpoint fork seed or runtime/device identity mismatch')
    segment=root/'segments'/spec['segment_id']
    selected=read_json(paths['boundary_receipt'])['sweep']
    if type(selected) is not int or not 1<=selected<=spec['final_sweep']:
        raise ValueError('Invalid source sweep')
    expected=dict(spec=root/'run-spec.json',inputs=root/'input-receipt.json',
        genesis=segment/'genesis/endpoint.npz',genesis_receipt=segment/'genesis/receipt.json',
        boundary_receipt=segment/'boundaries'/f'{selected:012d}'/'receipt.json')
    if paths!=expected:raise ValueError('Checkpoint source files do not belong to one published run')
    parent=PeriodicRunController(root,target,loading,eta,spec,inputs,authenticate=lambda:authenticate_files(source))
    warp_audit=[] if runtime_migration is not None else None
    boundary_audit=[] if runtime_migration is not None else None
    chart_audit=[] if runtime_migration is not None else None
    with writer(root), migration_chart_validation(chart_audit):
        authenticate_files(source)
        genesis,logical=load_genesis(paths['genesis'],target,parent.cp,migration_boundary_audit=boundary_audit)
        if (genesis.evidence['adaptation_steps']!=spec['warmup_steps']
                or genesis.evidence['initialization']['seed']!=spec['seed']):
            raise ValueError('Source genesis schedule/seed mismatch')
        receipt=read_json(paths['genesis_receipt'])
        expected_receipt=dict(schema='bsfm.genesis.v1',spec_sha256=parent.store.spec_hash,
            input_sha256=spec['input_sha256'],endpoint=file_record(paths['genesis']),logical_sha256=logical)
        if receipt!=expected_receipt:raise ValueError('Source genesis receipt mismatch')
        chain=parent._start(genesis,digest(receipt))
        for path in sorted((segment/'boundaries').iterdir()):
            if not path.name.isdigit() or len(path.name)!=12:raise ValueError('Unexpected source boundary path')
            if int(path.name)>selected:break
            chain=parent._read_boundary(path,chain,migration_warp_audit=warp_audit,migration_boundary_audit=boundary_audit)
        if chain['n']!=selected:raise ValueError('Selected source boundary missing')
        authenticate_files(source)
    binding=dict(schema='bsfm.checkpoint-fork-source.v1',records=copy.deepcopy(source),
        spec_sha256=parent.store.spec_hash,head=chain['head'],completed_sweep=selected,
        checkpoint_logical_sha256=chain['endpoint'].logical_sha256,
        pooling='source draws excluded; source run is not declared complete')
    if runtime_migration is not None:
        binding['runtime_migration']=copy.deepcopy(runtime_migration)
        binding['physical_warp_reconstruction']=warp_audit
        binding['fitted_value_reconstruction']=boundary_audit
        binding['physical_parameter_reconstruction']=chart_audit
        binding['replay']='State, tuning and RNG imported exactly; subsequent cross-runtime trajectories need not be bitwise identical'
    return copy.deepcopy(chain['endpoint']),binding


class CheckpointForkController(PeriodicRunController):
    def run(self, **kwargs):
        audit=[] if 'checkpoint_runtime_migration' in self.store.input_receipt else None
        with migration_chart_validation(audit):
            return super().run(**kwargs)

    def _adapt_endpoint(self,fault):
        if self.spec['warmup_steps']!=0:raise ValueError('Checkpoint inheritance must not retune implicitly')
        inputs=self.store.input_receipt
        authenticate_files(inputs['initial_checkpoint'])
        source_policy=read_json(inputs['initial_checkpoint']['inputs']['path']).get('transition_policy')
        if source_policy!=inputs.get('transition_policy'):
            raise ValueError('Changed tuning coordinates require explicit checkpoint retuning')
        source,binding=source_endpoint(self.store.input_receipt['initial_checkpoint'],
            self.target,self.loading,self.eta,seed=self.spec['seed'],
            environment_identity=self.spec['software']['environment_identity'],output=self.store.root,
            runtime_migration=self.store.input_receipt.get('checkpoint_runtime_migration'))
        evidence=dict(schema='bsfm.inherited-endpoint.v1',initialization=dict(seed=self.spec['seed']),
            adaptation_steps=0,source_boundary=boundary(source,self.target),
            source_tuning=tuning_identity(source.tuning),source=binding)
        tuning=source.tuning
        scales=self.store.input_receipt.get('checkpoint_field_step_scales')
        if scales is not None:
            validate_field_step_scales(scales,self.target.factor_ids)
            tuning=tuple(replace(t,step_size=t.step_size*scales[t.factor_id]) for t in tuning)
            evidence['field_step_scales']=copy.deepcopy(scales)
        return Endpoint(source.state,source.positions,tuning,source.eta_rng,source.gauge_rng,
            source.master_key,source.numpy_global_state,source.b_sigma2,evidence)

    def _genesis(self,fault):
        audit=[] if 'checkpoint_runtime_migration' in self.store.input_receipt else None
        with migration_chart_validation(audit):
            return self._migration_genesis(fault)

    def _migration_genesis(self,fault):
        endpoint,identity=super()._genesis(fault)
        # Even an already published child genesis cannot silently change its parent.
        expected=self._adapt_endpoint(fault)
        if endpoint.evidence!=expected.evidence:
            raise ValueError('Checkpoint fork source binding changed')
        return endpoint,identity


class CheckpointRetuningController(CheckpointForkController):
    """Explicit new lineage: retune before any sweep, never inherit a foreign mass."""
    def _source(self):
        if (self.store.input_receipt.get('checkpoint_retune') is not True
                or self.spec['warmup_steps'] < 20
                or 'checkpoint_field_step_scales' in self.store.input_receipt):
            raise ValueError('Explicit checkpoint retuning and >=20 warmup steps required')
        return source_endpoint(self.store.input_receipt['initial_checkpoint'],
            self.target,self.loading,self.eta,seed=self.spec['seed'],
            environment_identity=self.spec['software']['environment_identity'],output=self.store.root,
            runtime_migration=self.store.input_receipt.get('checkpoint_runtime_migration'))

    def _adapt_endpoint(self,fault):
        from .run_readaptation import adapt_from_endpoint
        source,binding=self._source()
        return adapt_from_endpoint(self,source,binding,fault)

    def _migration_genesis(self,fault):
        # Bypass inheritance's evidence reconstruction: never repeat adaptation
        # when validating a published or prepared genesis after interruption.
        endpoint,identity=PeriodicRunController._genesis(self,fault)
        _,binding=self._source()
        if endpoint.evidence['initialization'].get('parent')!=binding:
            raise ValueError('Retuned checkpoint source binding changed')
        return endpoint,identity
