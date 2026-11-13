"""Run a frozen dataset recipe through the existing periodic controllers.

No scheduler submission, preprocessing, or environment installation. Each phase
after the first retunes from its completed parent; only the final phase is the
production result. Repeating the command resumes the same immutable run.
"""
import argparse
import copy
import json
import math
import os
from pathlib import Path
import re
import subprocess


def validate_checkpoint_source(source):
    # Keep recipe validation free of JAX imports: main configures the backend
    # only after validation and before importing numerical modules.
    roles={'spec','inputs','genesis','genesis_receipt','boundary_receipt'}
    if not isinstance(source,dict) or set(source)!=roles:
        raise ValueError('Checkpoint fork requires five pinned source records')
    for record in source.values():
        if not isinstance(record,dict) or set(record)!={'path','bytes','sha256'}:
            raise ValueError('Pinned checkpoint source record required')


def validate_field_step_scales(scales, factor_ids):
    """Explicit reviewed reductions; no backend imports or adaptive policy."""
    if (not isinstance(scales,dict) or set(scales)!=set(factor_ids)
            or any(type(v) not in (int,float) or not math.isfinite(v) or not 0<v<=1
                   for v in scales.values())):
        raise ValueError('One finite field step scale in (0,1] per factor required')


def validate_recipe(recipe):
    required={'schema','backend','model','chain_id','factor_ids','seed','files',
              'dataset_recipe','gpu_runtime','phases'}
    if not required <= set(recipe) or set(recipe)-required-{'pcg_maximum_iterations','initial_endpoint','initial_checkpoint','checkpoint_field_step_scales','diagnostics','flat_range_prior'} or recipe['schema']!='bsfm.sampler-run.v1':
        raise ValueError('Exact sampler run recipe fields required')
    if 'diagnostics' in recipe and recipe['diagnostics']!='adaptation_study_v1':
        raise ValueError('Unknown diagnostic policy')
    if 'initial_checkpoint' in recipe:
        validate_checkpoint_source(recipe['initial_checkpoint'])
        if 'initial_endpoint' in recipe:raise ValueError('Choose one source endpoint')
    if 'pcg_maximum_iterations' in recipe:
        cap=recipe['pcg_maximum_iterations']
        if type(cap) is not int or not 1 <= cap <= 4096:raise ValueError('Invalid PCG iteration budget')
    if 'initial_endpoint' in recipe:
        r=recipe['initial_endpoint']
        if not isinstance(r,dict) or set(r)!={'path','bytes','sha256'}:raise ValueError('Pinned initial endpoint required')
    if recipe['backend'] not in ('cpu','gpu') or recipe['model'] not in ('deep','flat'):
        raise ValueError('Explicit CPU/GPU backend and deep/flat model required')
    if 'flat_range_prior' in recipe:
        from .range_spec import validate_range_prior
        if recipe['model'] != 'flat':
            raise ValueError('Flat range prior is only supported for the flat model')
        validate_range_prior(recipe['flat_range_prior'])
    if (recipe['backend']=='gpu') != isinstance(recipe['gpu_runtime'],dict):
        raise ValueError('GPU requires an explicit runtime recipe; CPU requires null')
    if recipe['backend']=='cpu' and recipe['gpu_runtime'] is not None:
        raise ValueError('CPU runtime recipe must be null')
    if recipe['backend']=='gpu':
        threads=recipe['gpu_runtime'].get('blas_threads')
        if type(threads) is not int or threads not in (1,4):raise ValueError('Explicit validated GPU BLAS thread count required')
    ids=recipe['factor_ids']
    if not isinstance(ids,list) or not ids or any(not isinstance(x,str) or not x for x in ids) or len(set(ids))!=len(ids):
        raise ValueError('Explicit ordered unique factor IDs required')
    if 'checkpoint_field_step_scales' in recipe:
        if 'initial_checkpoint' not in recipe:
            raise ValueError('Reviewed field step reduction requires initial_checkpoint')
        validate_field_step_scales(recipe['checkpoint_field_step_scales'],ids)
    if type(recipe['seed']) is not int or not 0<=recipe['seed']<=2**32-3004:
        raise ValueError('Seed and sampler offsets must fit uint32')
    phases=recipe['phases']
    if not isinstance(phases,list) or not phases:raise ValueError('At least one explicit phase required')
    names=[]
    for index,phase in enumerate(phases):
        if set(phase)!={'run_id','warmup_steps','sweeps','save_every'}:
            raise ValueError('Explicit phase identity, tuning, sweep and save counts required')
        names.append(phase['run_id'])
        inherited=index==0 and 'initial_checkpoint' in recipe
        if inherited and phase['warmup_steps']!=0:raise ValueError('Checkpoint fork must first inherit tuning with zero warmup')
        for key,minimum in [('warmup_steps',0 if inherited else 20),('sweeps',1),('save_every',1)]:
            if type(phase[key]) is not int or phase[key]<minimum:raise ValueError('Invalid phase '+key)
    for name in names+[recipe['chain_id']]:
        if not isinstance(name,str) or not re.fullmatch('[A-Za-z0-9_-]+',name):raise ValueError('Safe run/chain identities required')
    if len(set(names))!=len(names):raise ValueError('Phase run IDs must be unique')


def check_repository(recipe_path,commit):
    from .run_inputs import REPO
    recipe_path=Path(recipe_path).resolve()
    if not recipe_path.is_file():raise ValueError('Run recipe file required')
    def git(*args):
        return subprocess.check_output(['git',*args],cwd=REPO,text=True).strip()
    if git('rev-parse','HEAD')!=commit or git('status','--porcelain'):
        raise ValueError('Clean exact generating commit required')
    if recipe_path.is_relative_to(REPO.resolve()):
        git('ls-files','--error-unmatch','--',recipe_path.relative_to(REPO.resolve()).as_posix())


def run_recipe(path,output,*,commit):
    """Authenticate one frozen recipe and run/resume its ordered phases."""
    from . import run_inputs
    from .checkpoint_contract import digest
    from .run_storage import file_record,read_json,safe
    from .run_periodic import PeriodicRunController,PeriodicReadaptationController
    from .run_readaptation import parent_endpoint
    path=Path(path).resolve(); output=safe(output)
    if output.is_relative_to(run_inputs.REPO.resolve()):
        raise ValueError('Sampler outputs must stay outside the source checkout')
    check_repository(path,commit)
    recipe=read_json(path);validate_recipe(recipe); recipe_record=file_record(path)
    # Relative deployment paths are relative to the frozen recipe, not cwd.
    def resolve(value):return str((path.parent/Path(value)).resolve())
    files=copy.deepcopy(recipe['files'])
    for record in files.values():record['path']=resolve(record['path'])
    gpu=copy.deepcopy(recipe['gpu_runtime'])
    if gpu is not None:
        for key in ('receipt','prefix','site_packages','libdevice','p100_receipt',
                    'installation','validation','validation_plan'):
            if gpu.get(key) is not None:gpu[key]=resolve(gpu[key])
    env=run_inputs.authenticate_environment(gpu_runtime=gpu)
    if recipe['backend']=='gpu':
        from .run_gpu_environment import preflight_gpu_callback
        preflight_gpu_callback()
    first=recipe['phases'][0]
    genesis=output/first['run_id']/'segments/segment/genesis/endpoint.npz'
    source=copy.deepcopy(recipe.get('initial_endpoint'))
    checkpoint=copy.deepcopy(recipe.get('initial_checkpoint'))
    if checkpoint is not None:
        for record in checkpoint.values():record['path']=resolve(record['path'])
        run_inputs.authenticate_files(checkpoint)
    if source is not None:
        source['path']=resolve(source['path'])
        if Path(source['path']).is_relative_to(output):raise ValueError('Imported endpoint must be outside new output root')
        run_inputs.authenticate_files({'initial_endpoint':source})
    target,loading,eta,binding=run_inputs.load_inputs(files,recipe['factor_ids'],
        genesis_path=genesis if genesis.exists() else (checkpoint['genesis']['path'] if checkpoint else (source['path'] if source else None)),dataset_recipe=recipe['dataset_recipe'])
    if recipe['model']=='flat':
        from .flat_control import FlatTarget,FlatTransition
        target=FlatTarget(target.inputs,target.geometry,target.rule,factor_ids=target.factor_ids,
                          range_prior=recipe.get('flat_range_prior'))
    binding=dict(binding,launcher_recipe=recipe_record,model=recipe['model'],target_identity=target.identity)
    if source is not None:binding['initial_endpoint']=source
    if checkpoint is not None:binding['initial_checkpoint']=checkpoint
    if 'checkpoint_field_step_scales' in recipe:
        binding['checkpoint_field_step_scales']=copy.deepcopy(recipe['checkpoint_field_step_scales'])
    if 'diagnostics' in recipe:binding['diagnostics']=recipe['diagnostics']
    if 'pcg_maximum_iterations' in recipe:binding['pcg_maximum_iterations']=recipe['pcg_maximum_iterations']
    def authenticate():
        check_repository(path,commit)
        if file_record(path)!=recipe_record:raise ValueError('Run recipe changed')
        run_inputs.authenticate_files(files)
        if source is not None:run_inputs.authenticate_files({'initial_endpoint':source})
        if checkpoint is not None:run_inputs.authenticate_files(checkpoint)
        if run_inputs.authenticate_environment(gpu_runtime=gpu)!=env:raise ValueError('Environment changed')
        target._validate_identities()
    parent=None;results=[]
    for phase in recipe['phases']:
        phase_binding=copy.deepcopy(binding)
        if parent is not None:
            _,phase_binding['readaptation_parent']=parent_endpoint(parent)
        spec=dict(schema='bsfm.local-run.v1',run_id=phase['run_id'],segment_id='segment',
            chain_id=recipe['chain_id'],factor_ids=recipe['factor_ids'],seed=recipe['seed'],
            warmup_steps=phase['warmup_steps'],settling_sweeps=0,production_sweeps=phase['sweeps'],
            final_sweep=phase['sweeps'],save_every=phase['save_every'],checkpoint_every=phase['save_every'],
            mode='exact_resume',input_sha256=digest(phase_binding))
        spec['software']=dict(git_commit=commit,clean_tree=True,run_config_sha256=digest(spec),
            environment_lock_sha256=env['lock']['sha256'],environment_identity=digest(env))
        cls=PeriodicRunController if parent is None else PeriodicReadaptationController
        if parent is None and source is not None:
            from .run_continuation import ImportedEndpointController
            cls=ImportedEndpointController
        if parent is None and checkpoint is not None:
            from .run_checkpoint_fork import CheckpointForkController
            cls=CheckpointForkController
        controller=cls(output/phase['run_id'],target,loading,eta,spec,phase_binding,
                       authenticate=authenticate,**({} if parent is None else dict(parent=parent)))
        if 'pcg_maximum_iterations' in recipe:
            from .layer4 import JointEtaConditional
            controller.layer.joint_eta=JointEtaConditional(target,maximum_iterations=recipe['pcg_maximum_iterations'])
        if recipe['model']=='flat':controller.layer.split=FlatTransition(target)
        print('PHASE',phase['run_id'],recipe['model'],recipe['backend'],flush=True)
        results.append(dict(run_id=phase['run_id'],result=controller.run()))
        if results[-1]['result'].get('status')=='review_required':
            return dict(schema='bsfm.recipe-review.v1',status='review_required',phases=results,
                        convergence='not_assessed',action='preserve checkpoints; no automatic retuning')
        parent=controller
    return dict(schema='bsfm.recipe-completion.v1',phases=results,
                production_run_id=recipe['phases'][-1]['run_id'],
                pooling='Earlier phase draws excluded from final production',convergence='not_assessed')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recipe',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--commit',required=True)
    args=parser.parse_args()
    recipe=json.loads(args.recipe.read_text(encoding='utf-8'));validate_recipe(recipe)
    # Configure before importing JAX; GPU keeps CPU available for host callbacks.
    os.environ['JAX_PLATFORMS']='cuda,cpu' if recipe['backend']=='gpu' else 'cpu'
    os.environ['JAX_ENABLE_X64']='true'
    if recipe['backend']=='gpu':os.environ['BSFM_EXPERIMENTAL_CUDA']='1'
    threads=recipe['gpu_runtime']['blas_threads'] if recipe['backend']=='gpu' else 1
    for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[name]=str(threads)
    result=run_recipe(args.recipe,args.output,commit=args.commit)
    print(json.dumps(result,sort_keys=True),flush=True)
    if result.get('status')=='review_required':raise SystemExit(42)


if __name__=='__main__':main()
