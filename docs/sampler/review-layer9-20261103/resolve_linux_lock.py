"""Resolve platform wheels for already frozen versions; never install or run jobs."""
import concurrent.futures,hashlib,json,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
source=ROOT/'environment/sampler-layer5/source-lock.json'
original=json.loads(source.read_text())

def resolve(row):
    if row['url'].endswith('-none-any.whl'):
        return dict(row,selection='Same platform-independent wheel as accepted lock')
    url=f"https://pypi.org/pypi/{row['name']}/{row['version']}/json"
    with urllib.request.urlopen(url,timeout=30) as response:metadata=json.load(response)
    wheels=[f for f in metadata['urls'] if f['packagetype']=='bdist_wheel'
            and '-cp311-cp311-' in f['filename'] and 'manylinux' in f['filename']
            and f['filename'].endswith('x86_64.whl') and not f.get('yanked')]
    if len(wheels)!=1:raise ValueError('Ambiguous or missing locked Linux wheel: '+row['name'])
    f=wheels[0]
    return dict(name=row['name'],version=row['version'],url=f['url'],sha256=f['digests']['sha256'],
                bytes=f['size'],requires_python=f.get('requires_python'),
                requires_dist=metadata['info'].get('requires_dist'),
                selection='Exact-version CPython 3.11 Linux x86_64 wheel from official PyPI release metadata',
                metadata_url=url)

if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(resolve,original['packages']))
    result=dict(schema='bsfm.proposed-linux-layer9-environment.v1',status='resolved_only_not_installed_or_validated',
        python='3.11.14',platform='Linux x86_64 CPU',
        accepted_version_source=str(source.relative_to(ROOT)),
        accepted_version_source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),packages=rows,
        limitations=['Wheel hashes from official release metadata; archive bytes not downloaded or hashed here',
                     'Runtime/base-environment authentication and Linux dependency/isolation tests required',
                     'No accepted Windows lock changed; no scientific or scheduler job submitted'])
    path=Path(__file__).with_name('LINUX_ENVIRONMENT_PROPOSAL.json')
    path.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(packages=len(rows),output=str(path),status=result['status'])))
