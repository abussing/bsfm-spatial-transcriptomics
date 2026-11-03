"""Check variable dimensions, L16 numerical equivalence, and smoke rule identity."""
import ast
import copy
from dataclasses import asdict, replace
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
from bsfm.sampler import layer4
from bsfm.sampler.field_target import DirectWTarget
from bsfm.sampler.rule import FrozenRule, load_rule
from bsfm.sampler.contracts import logical_hash
from sampler_layer3_support import system
from sampler_layer4_support import positions
from smoke_rule import load_smoke_rule


def main():
    repo=Path(__file__).resolve().parents[3]
    args=['git','-c','safe.directory='+repo.as_posix(),'show','1aecadb6a95810d2182b3944694a5a9ae7b08854:src/bsfm/sampler/layer4.py']
    original=subprocess.check_output(args,cwd=repo,text=True)
    node=next(n for n in ast.parse(original).body if isinstance(n,ast.ClassDef) and n.name=='JointEtaConditional')
    namespace=dict(vars(layer4))
    exec(compile(ast.Module(body=[node],type_ignores=[]),'authenticated_previous_layer4','exec'),namespace)
    parent,state,p=system(12)
    ps=positions(parent,state,p)
    first,second=np.random.default_rng(901),np.random.default_rng(901)
    before=layer4.state_hashes(state)
    old=namespace['JointEtaConditional'](parent).draw(ps,state,first,state_factor_ids=parent.factor_ids)
    new=layer4.JointEtaConditional(parent).draw(ps,state,second,state_factor_ids=parent.factor_ids)
    assert np.array_equal(old[0],new[0]) and np.array_equal(old[1],new[1])
    assert asdict(old[2])==asdict(new[2]) and old[3]==new[3]
    assert first.bit_generator.state==second.bit_generator.state
    rule=load_smoke_rule();rule.validate()
    target=DirectWTarget(parent.inputs,parent.geometry,rule,factor_ids=parent.factor_ids)
    ps=positions(target,state,p)
    rng=np.random.default_rng(901)
    eta,beta,diagnostics,record=layer4.JointEtaConditional(target).draw(ps,state,rng,state_factor_ids=target.factor_ids)
    assert eta.shape==state.eta.shape and beta.shape==(len(ps),64) and diagnostics.converged
    assert layer4.state_hashes(state)==before
    value,gradient,_=target.value_grad(ps[0],state,state_factor_ids=target.factor_ids)
    assert np.isfinite(value) and np.isfinite(gradient).all()
    corrupted={k:v.copy() for k,v in rule.arrays.items()};corrupted['omega'][0,0]+=1
    try:replace(rule,arrays=corrupted).validate()
    except ValueError:pass
    else:raise AssertionError('Changed rule accepted')
    try:FrozenRule.authenticate(rule.arrays,json.loads(rule.identity_json))
    except (ValueError,AssertionError):pass
    else:raise AssertionError('Canonical L16 boundary accepted L4')
    result=dict(status='pass',canonical_L16_joint_draw_beta_diagnostics_audit_and_rng_exact=True,
        smoke_L4_feature_columns=64,finite_target_and_gradient=True,changed_rule_rejected=True,
        canonical_boundary_rejects_L4=True,state_unchanged=True,
        canonical_registry_sha256=__import__('hashlib').sha256((repo/'config/sampler/L16_ell14.json').read_bytes()).hexdigest())
    Path(sys.argv[1]).write_bytes((json.dumps(result,indent=2)+'\n').encode())
    print(json.dumps(result))


if __name__=='__main__':main()
