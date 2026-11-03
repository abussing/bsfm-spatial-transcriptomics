"""Approved hole fits with compact periodic saving; original sampler chronology."""
import copy
import json
from pathlib import Path
import sys
from experiment import controllers, CONFIGS
from gpu_run import authenticate_gpu_environment
from bsfm.sampler.checkpoint_contract import digest
from bsfm.sampler.flat_control import FlatTransition
from bsfm.sampler.run_periodic import PeriodicRunController, PeriodicReadaptationController
from bsfm.sampler.run_readaptation import parent_endpoint


def periodic_controllers(config,prepared,output,model,commit):
    base,binding,base_spec=controllers(config,prepared,output,model,commit,runtime_auth=authenticate_gpu_environment)
    def spec(run_id,warmup,sweeps,bind):
        s=base_spec(run_id,warmup,sweeps,bind)
        s.update(save_every=10,checkpoint_every=10)
        s['software']['run_config_sha256']=digest(dict(
            configuration={k:v for k,v in s.items() if k!='software'},storage='periodic_compact_v1'))
        return s
    parent=PeriodicRunController(base.store.root,base.target,base.loading,base.eta,
        spec('bridge_'+config+'_'+model,50,50,binding),binding,authenticate=base.authenticate)
    if model=='flat':parent.layer.split=FlatTransition(parent.target)
    return parent,binding,spec


def run(config,prepared,output,model,commit):
    parent,binding,spec=periodic_controllers(config,prepared,output,model,commit)
    print('PERIODIC GPU RUN',config,model,'K12 L14; save first, every 10, final',flush=True)
    parent.run()
    _,receipt=parent_endpoint(parent)
    binding=dict(binding,readaptation_parent=receipt)
    child=PeriodicReadaptationController(Path(output)/model/'production',parent.target,parent.loading,parent.eta,
        spec('production_'+config+'_'+model,100,1000,binding),binding,authenticate=parent.authenticate,parent=parent)
    if model=='flat':child.layer.split=FlatTransition(parent.target)
    print('PHASE retuning 100/factor then production 1000 sweeps',flush=True)
    print(json.dumps(child.run()),flush=True)


if __name__=='__main__':
    config,prepared,output,model,commit=sys.argv[1:]
    if config not in CONFIGS or model not in ('deep','flat'):raise ValueError('Unknown configuration/model')
    run(config,Path(prepared),Path(output),model,commit)
