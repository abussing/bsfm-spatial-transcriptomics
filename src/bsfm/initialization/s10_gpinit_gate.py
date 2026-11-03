"""Bounded full-cell S10 GPINIT execution/readback with accepted fitting code.

Mechanical K=20/nfit=250/seed=2026102610 only, not production defaults.
The already accepted GP implementation and its numerical settings are unchanged.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from .preparation_environment import REPO, authenticate, record, require, sha

SETTINGS = dict(factors=20,nfit=250,seed=2026102610)
IMPLEMENTATION_SHA = '26be9b43ba03908934e3a3d9ebddf0bd6422a7fa5331412266073660a57797c1'
CONFIG_SHA = '63589c3fb02847d7971f3d39753d08be483c7c9ff2f7acc74a2481bf356062d2'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path,value):
    with Path(path).open('x',encoding='utf-8',newline='\n') as f:
        json.dump(value,f,indent=2,allow_nan=False); f.write('\n')


def load_prepared(root):
    import numpy as np
    from . import gp_svd as gp
    from .s10_preparation import validate_model
    require(sha(gp.__file__) == IMPLEMENTATION_SHA,'Accepted GP implementation changed')
    require(sha(gp.CONFIG) == CONFIG_SHA,'Accepted GP configuration changed')
    c = read(root/'input-contract.json')
    v = read(root/'preparation-validation.json')
    require(v['contract']['sha256'] == sha(root/'input-contract.json')
            and v['npz']['sha256'] == sha(root/'model-input.npz'), 'Preparation readback binding')
    require(c['section'] == 'S10__WT5' and c['gpinit_gate'] == SETTINGS, 'S10 gate settings')
    require(c['upstream']['join']['cells'] == 9422 and c['upstream']['join']['modes'] == 371
            and c['upstream']['join']['active_vertices'] == 168
            and not c['upstream']['join']['historical_subset_used'], 'Full-population mesh binding')
    for name in ('response_manifest','validation','response_h5','mesh','registry','panel'):
        r = c['upstream'][name]
        require(sha(r['path']) == r['sha256'] and Path(r['path']).stat().st_size == r['bytes'], 'Upstream drift: '+name)
    data = gp.load_input(root/'model-input.npz',c)
    genes = read(REPO/'config/preprocessing/modeling-panel.json')['genes']
    validate_model(data,c['arrays'],genes)
    require(gp.identities(data) == c['arrays'], 'Preparation/GP hash encoding disagreement')
    return data,c


def validate_provenance(cert,contract,environment):
    """Bind saved producer/environment claims to independent expected evidence."""
    p=cert['provenance']
    require(p['config_sha256'] == CONFIG_SHA, 'Recorded GP configuration')
    require(p['environment'] == environment, 'Recorded GP environment differs from fresh authentication')
    require(p['accepted_code_commit'] == contract['producer']['baseline_commit'], 'Recorded GP code commit')
    require(p['preparation_producer'] == contract['producer'], 'Recorded preparation producer')
    commit=p['accepted_code_commit']
    for path,expected in [('src/bsfm/initialization/gp_svd.py',IMPLEMENTATION_SHA),
                          ('config/initialization/c3-gp-svd.json',CONFIG_SHA)]:
        value=subprocess.check_output(['git','show',commit+':'+path],cwd=REPO)
        require(hashlib.sha256(value).hexdigest() == expected,'Committed GP producer bytes')


def validate_output(directory,root,*,environment=None):
    import numpy as np
    from . import gp_svd as gp
    data,c = load_prepared(root)
    cert = read(directory/'certificate.json')
    require(cert['dimensions'] == dict(types=3,genes=91,cells=9422), 'Canonical full-cell GPINIT dimensions')
    require(cert['status'] == 'pass' and all(cert[k] == v for k,v in SETTINGS.items()), 'GPINIT status/settings')
    validate_provenance(cert,c,authenticate('gpinit') if environment is None else environment)
    require(cert['input_identities'] == c['arrays'], 'Output/input identities')
    require(cert['provenance']['input_sha256'] == sha(root/'model-input.npz')
            and cert['provenance']['contract_sha256'] == sha(root/'input-contract.json'), 'Output input binding')
    require(cert['provenance']['implementation_sha256'] == IMPLEMENTATION_SHA, 'Output implementation')
    require(cert['output_sha256'] == sha(directory/'gpinit.npz'), 'GPINIT bytes')
    with np.load(directory/'gpinit.npz',allow_pickle=False) as z:
        a = {k:z[k].copy() for k in z.files}
    require(set(a) == set(cert['output_logical_hashes']), 'Output field set')
    for name,value in a.items():
        require(np.isfinite(value).all(), 'Nonfinite GPINIT output: '+name)
        require(gp.logical(value) == cert['output_logical_hashes'][name], 'Output logical hash: '+name)
    require(a['Lam_seed'].shape == (3,91,20) and a['eta_seed'].shape == (20,9422), 'Seed axes')
    choices,rng = gp.fitting_points(data['cell_id'],250,2026102610)
    require([ix.tolist() for ix in choices] == cert['fitting_indices'], 'Fitting-point identity/order')
    require(rng.choice(9422,400,replace=False).tolist() == cert['diagnostic_fitting_indices'], 'Diagnostic RNG chronology')
    u = a['Lam_seed'].reshape(273,20); eta = a['eta_seed']; singular = a['singular_values']
    orth = float(np.max(abs(u.T@u-np.eye(20))))
    eta_mean = float(np.max(abs(eta.mean(axis=1))))
    require(orth < 1e-13 and eta_mean < 1e-13, 'Accepted orthogonality/centering checks')
    # Numerical identities of the saved rank-20 factorization, independent of
    # the reporting computations in gp.fit. No historical-population comparison.
    s = np.asarray(cert['all_singular_values'])
    require(np.array_equal(s[:20],singular), 'Leading singular values')
    gram_error = float(np.linalg.norm(eta@eta.T-np.diag(singular**2))/np.linalg.norm(singular**2))
    product_norm = float(np.linalg.norm(u@eta))
    norm_error = abs(product_norm-float(np.linalg.norm(singular)))/float(np.linalg.norm(singular))
    tail_error = abs(cert['truncation_error']-float(np.linalg.norm(s[20:])))/max(1.,cert['surface_norm'])
    require(max(gram_error,norm_error,tail_error) < 1e-12, 'Saved SVD reconstruction identity')
    require(gp.identities(data) == c['arrays'], 'Validation mutated input')
    return dict(status='pass',settings=SETTINGS,dimensions=cert['dimensions'],
                output=record(directory/'gpinit.npz'),certificate=record(directory/'certificate.json'),
                input=record(root/'model-input.npz'),contract=record(root/'input-contract.json'),
                output_logical_hashes=cert['output_logical_hashes'],
                loading_orthogonality_max=orth,eta_mean_max=eta_mean,
                eta_gram_relative_error=gram_error,product_norm_relative_error=norm_error,
                truncation_identity_relative_error=tail_error,
                thresholds=dict(orthogonality_atol=1e-13,eta_mean_atol=1e-13,svd_identity_rtol=1e-12),
                fitting_points=[len(ix) for ix in choices], input_unchanged=True,
                committed_GP_code_and_config_verified=True,recorded_environment_matches_fresh=True)


def compare(first,second):
    import numpy as np
    c1=read(first/'certificate.json');c2=read(second/'certificate.json')
    with np.load(first/'gpinit.npz',allow_pickle=False) as a,np.load(second/'gpinit.npz',allow_pickle=False) as b:
        require(set(a.files) == set(b.files),'Repeat output fields')
        require(all(np.array_equal(a[k],b[k]) for k in a.files),'Repeat logical values differ')
    keys=('input_identities','fitting_indices','diagnostic_fitting_indices','centered_surface_sha256',
          'all_singular_values','surface_norm','surface_mean_max','truncation_error',
          'loading_orthogonality_max','eta_mean_max','eta_sd','maximum_input_recentering_mean',
          'warnings','output_logical_hashes')
    require(all(c1[k] == c2[k] for k in keys),'Repeat numerical diagnostic mismatch')
    return dict(status='pass',all_output_arrays_exact=True,diagnostics_exact=list(keys),
                file_bytes_equal=sha(first/'gpinit.npz') == sha(second/'gpinit.npz'),
                timing_excluded=True,no_historical_output_equality_expected=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepared',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--validate-only',action='store_true')
    p.add_argument('--compare',type=Path)
    args=p.parse_args()
    env=authenticate('gpinit')
    data,c=load_prepared(args.prepared)
    from . import gp_svd as gp
    if args.validate_only:
        result=validate_output(args.output,args.prepared,environment=env)
        if args.compare:result['repeat']=compare(args.output,args.compare)
        print(json.dumps(result,indent=2));return
    require(not args.output.exists(),'Fresh fit directory required')
    require(not args.output.resolve().is_relative_to(REPO),'Fit artifacts outside Git')
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()
    arrays,report=gp.fit(data,**SETTINGS)
    provenance=dict(input=str(args.prepared/'model-input.npz'),input_sha256=sha(args.prepared/'model-input.npz'),
                    contract_sha256=sha(args.prepared/'input-contract.json'),config_sha256=sha(gp.CONFIG),
                    implementation_sha256=sha(gp.__file__),accepted_code_commit=commit,
                    gate_source=record(__file__),gate_status=c['producer']['status'],
                    environment=env,preparation_producer=c['producer'])
    gp.save(args.output,arrays,report,provenance=provenance)
    result=validate_output(args.output,args.prepared,environment=env)
    write(args.output/'independent-validation.json',result)
    print(json.dumps(dict(status='pass',output=str(args.output),elapsed_seconds=report['elapsed_seconds'],
                          dimensions=report['dimensions'],metrics=result),indent=2))


if __name__=='__main__':main()
