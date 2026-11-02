"""Authenticate and compare saved S10 seeds. No GP import, fit, or artifact rewrite.

Run from the repository in the pinned GPINIT environment, with four BLAS threads.
Only the small representation-comparison.json audit in this directory is written.
"""
import hashlib
import io
import json
from pathlib import Path
import tarfile

import numpy as np
from scipy.linalg import subspace_angles
from threadpoolctl import threadpool_limits

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))


def logical(a):
    # Encoding of the executed builder; copied definition is identity metadata,
    # not another fitting implementation. No import of GP fitting code is needed.
    if a.dtype.kind=='U':
        value=json.dumps(a.tolist(),ensure_ascii=False,separators=(',',':')).encode('utf-8');dtype='utf8'
    else:
        dtype=a.dtype.newbyteorder('<').str;value=np.asarray(a,dtype=dtype).tobytes(order='C')
    header=json.dumps({'shape':list(a.shape),'dtype':dtype},sort_keys=True).encode()+b'\n'
    return hashlib.sha256(header+value).hexdigest()


def subspace(a,b):
    """Column-space diagnostics; compute projector distance without dense N x N."""
    ranks=[int(np.linalg.matrix_rank(x)) for x in (a,b)]
    if ranks != [a.shape[1],b.shape[1]] or a.shape[1]!=b.shape[1]:
        return {'well_defined_full_column_rank':False,'ranks':ranks}
    qa=np.linalg.qr(a,mode='reduced')[0];qb=np.linalg.qr(b,mode='reduced')[0]
    cross=qa.T@qb
    # Avoid catastrophic cancellation of 2*K - 2*||Qa.T Qb||_F^2 near equality.
    ea=qa-qb@cross.T;eb=qb-qa@cross
    distance=float(np.hypot(np.linalg.norm(ea),np.linalg.norm(eb)))
    angles=subspace_angles(qa,qb)
    return {'well_defined_full_column_rank':True,'ranks':ranks,
        'projector_difference_frobenius':distance,
        'projector_difference_relative_frobenius':distance/np.sqrt(a.shape[1]),
        'principal_angles_radians':angles.tolist(),'max_principal_angle_radians':float(angles.max())}


def main():
    review=read(HERE/'review.json');strict=read(HERE/'comparison.json')
    strict_hash=sha(HERE/'comparison.json')
    policy=read(REPO/'config/initialization/historical-regression.json')
    root=Path(review['review_root_machine_local'])
    candidate=root/'port/gpinit.npz';certificate=root/'port/certificate.json'
    assert sha(candidate)==review['output_sha256']==strict['output_gpinit_sha256']
    assert sha(certificate)==review['certificate_sha256']
    cert=read(certificate);contract=read(HERE/'input-contract.json')
    source=Path(cert['provenance']['source'])
    assert sha(source)==cert['provenance']['source_sha256']==contract['source_sha256']==strict['source_sha256']
    assert sha(REPO/'src/bsfm/initialization/gp_svd.py')==review['source_sha256']==cert['provenance']['implementation_sha256']
    executed=read(HERE/'executed-config.json')
    assert sha(HERE/'executed-config.json')==review['config_sha256']==cert['provenance']['configuration_sha256']
    current=read(REPO/'config/initialization/c3-gp-svd.json')
    assert {k:v for k,v in current.items() if k!='status'}=={k:v for k,v in executed.items() if k!='status'}
    package=source.parents[2]
    archive=package.with_name(package.name+'_READY.tar.gz')
    assert sha(archive)==strict['archive_sha256']
    expected_source='f5b1545072c462cf772cd3caf44a398da8cf5558b4a2dd3133922c8cd8143f94'
    assert sha(package/'code/sampler/build_gpinit_from_truth_npz.py')==expected_source==current['source_sha256']
    assert sha(package/'prepare_cpu.sh')=='2713f6f120fff645f4161d487f4ba6240e29df812cb8b21de17df9df376af7d8'
    assert sha(package/'SECTIONS.json')=='0bb354335d887ed10c2f1c694ed17a2ad85f6a1a84fa368de2bcd78d05b386b9'
    index=read(package/'SECTIONS.json').index('S10__WT5')
    assert cert['seed']==contract['configuration']['seed']==2026102600+index
    members={}
    names=['inputs/S10__WT5/gpinit/gpinit.npz','inputs/S10__WT5/gpinit/CERTIFICATE.json']
    manifest=read(REPO/'docs/recovery/evidence/adaptive_mesh_m2/historical_bundle_manifest.json')
    with tarfile.open(archive,'r|gz') as tar:
        for entry in tar:
            rel=entry.name.removeprefix('./').removeprefix(package.name+'/')
            if rel in names:
                data=tar.extractfile(entry).read()
                assert hashlib.sha256(data).hexdigest()==manifest[rel]
                members[rel]=data
    old_cert=json.loads(members[names[1]])
    assert old_cert['source_sha256']==contract['source_sha256']
    for old_key,key in [('factors','factors'),('nfit_per_cell_type','nfit')]:
        assert old_cert[old_key]==cert[key]==contract['configuration'][key]
    with np.load(io.BytesIO(members[names[0]]),allow_pickle=False) as z:old={k:z[k] for k in z.files}
    with np.load(candidate,allow_pickle=False) as z:new={k:z[k] for k in z.files}
    assert old.keys()==new.keys()
    assert all(old[k].shape==new[k].shape for k in old)
    assert {k:logical(v) for k,v in new.items()}==cert['output_logical_hashes']
    with np.load(source,allow_pickle=False) as z:
        assert {k:logical(z[k]) for k in contract['arrays']}==contract['arrays']==cert['input_identities']
        types=z['cell_id'];rng=np.random.RandomState(cert['seed'])
        selections=[rng.choice(ix,min(cert['nfit'],len(ix)),replace=False).tolist()
                    for ix in [np.flatnonzero(types==t) for t in range(3)]]
        assert selections==cert['fitting_indices']
        assert rng.choice(len(types),min(400,len(types)),replace=False).tolist()==cert['diagnostic_fitting_indices']
    k=cert['factors'];a=old['Lam_seed'].reshape(-1,k);b=new['Lam_seed'].reshape(-1,k)
    with threadpool_limits(limits=4):
        reference=a@old['eta_seed'];actual=b@new['eta_seed']
        relative=float(np.linalg.norm(actual-reference)/np.linalg.norm(reference))
        singular_relative=float(np.linalg.norm(new['singular_values']-old['singular_values'])/np.linalg.norm(old['singular_values']))
        loading=subspace(a,b);eta=subspace(old['eta_seed'].T,new['eta_seed'].T)
    signs=np.where(np.sum(a*b,axis=0)<0,-1,1).tolist()
    assert not strict['arrays']['Lam_seed']['exact'] and not strict['arrays']['eta_seed']['exact']
    assert not strict['arrays']['Lam_seed']['allclose_rtol_1e-8_atol_1e-10']
    assert not strict['arrays']['eta_seed']['allclose_rtol_1e-8_atol_1e-10']
    assert strict['reconstructed_field_relative_error']==5.4445910829792996e-8
    passed=relative<=policy['reconstructed_field_relative_frobenius_max'] and singular_relative<=policy['singular_values_relative_l2_max']
    result={'schema':'bsfm.gpinit-historical-equivalence.v1','status':'pass' if passed else 'fail',
        'authority':policy['authority'],'scope':policy['scope'],'no_refit':True,
        'strict_comparison_unchanged_sha256':strict_hash,'strict_loading_eta_checks_remain_failed':True,
        'original_reconstructed_relative_error':strict['reconstructed_field_relative_error'],
        'reconstructed_field_relative_frobenius':relative,'singular_value_relative_l2':singular_relative,
        'limits':{'reconstructed':policy['reconstructed_field_relative_frobenius_max'],'singular_values':policy['singular_values_relative_l2_max']},
        'loading_column_space':loading,'eta_row_space':eta,'sign_comparison':signs,
        'identity_checks':{'input_file_sha256':contract['source_sha256'],'dimensions':cert['dimensions'],
            'ordered_input_arrays':contract['arrays'],'saved_output_hashes_authenticated':True,
            'factors':cert['factors'],'nfit':cert['nfit'],'seed':cert['seed'],'same_algorithm_and_kernel_settings':True,
            'seed_provenance':'Exact authenticated wrapper formula; historical certificate did not separately record seed.',
            'ordering_provenance':'Same authenticated observation bytes and preserved builder ordering; historical seeds lack separate identity axes.',
            'configuration_change_since_execution':'status label only','fitting_indices_match_recovered_rng':True},
        'equality_policy':{'historical':'user-approved cold-start equivalence only','same_environment':'exact','saved_readback':'exact'},
        'source_and_outputs_unchanged':{'input_sha256':sha(source),'output_sha256':sha(candidate),'certificate_sha256':sha(certificate)}}
    assert sha(HERE/'comparison.json')==strict_hash
    assert passed
    (HERE/'representation-comparison.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
