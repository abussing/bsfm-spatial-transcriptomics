"""Read-only equivalence gate against authenticated accepted validation artifacts.

Writes its own fresh external evidence directory. Does not fit or edit either run.
"""
import argparse
from pathlib import Path

import h5py
import numpy as np

from bsfm.preprocessing.raw_preflight import require, sha256_file
from bsfm.preprocessing.response_contract import (REPO, load_json, raw_section,
    readback, save_json, file_record, payload_hash)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('bundle','raw-source','environment','config','work-dir'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    require(not a.work_dir.resolve().is_relative_to(REPO), 'Evidence must stay outside Git')
    accepted=load_json(REPO/'docs/preprocessing/audits/20261031_sct_smoke/manifest.json')
    reference=accepted['run_evidence']['runs']['S00-full']
    old=Path(reference['output'])
    require(a.bundle.name=='S00__Trem2_5xFAD4', 'This accepted-equivalence gate is S00 only')
    records={r['name']:r for r in reference['report']['artifacts']}
    for name in ('fit.rds','corrected-counts.rds','log1p-response.rds'):
        require(file_record(old/name)=={'path':name,'bytes':records[name]['bytes'],'sha256':records[name]['sha256']}, 'Accepted artifact changed: '+name)
    raw=raw_section(a.raw_source.resolve(),a.bundle.name,a.config)
    arrays,rr=readback(a.environment.resolve(),raw,a.bundle/'fit.rds',a.work_dir,124,accepted=old)
    require(rr['report']['semantic_sha256']==reference['report']['semantic_sha256'], 'Accepted R semantic signatures differ')
    payloads={}
    with h5py.File(a.bundle/'response.h5','r') as f:
        for dataset,key in [('/all/corrected_counts','corrected'),('/all/log1p_response','response')]:
            require(np.array_equal(f[dataset][:],arrays[key]),'HDF5 logical payload differs')
            payloads[dataset]=payload_hash(arrays[key],'float64')
        require(list(f['/axes/genes300/ids'].asstr()[:])==list(raw['genes']), 'Gene IDs/order differ')
        require(list(f['/axes/cells_all/ids'].asstr()[:])==list(raw['cells']), 'Cell IDs/order differ')
    result={'schema':'bsfm.accepted-sct-equivalence.v1','status':'pass',
            'accepted_review_manifest_sha256':sha256_file(REPO/'docs/preprocessing/audits/20261031_sct_smoke/manifest.json'),
            'bundle_manifest':file_record(a.bundle/'manifest.json'),
            'accepted_artifact_path':str(old), 'accepted_semantic_sha256':reference['report']['semantic_sha256'],
            'canonical_payload_sha256':payloads, 'exact_equivalence':rr['report']['accepted_equivalence'],
            'readback':rr, 'serialization_limit':'HDF5 file bytes are not compared with RDS file bytes. Logical values/order, effective arguments and unchanged R semantic hashes are compared exactly.'}
    save_json(a.work_dir/'equivalence.json',result)
    print(result['status'],payloads)


if __name__=='__main__': main()
