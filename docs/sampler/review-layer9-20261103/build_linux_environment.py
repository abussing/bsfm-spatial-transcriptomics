"""Proposed isolated Linux CPU environment build; no sampler or data processing."""
import argparse,hashlib,importlib.metadata,json,os,platform,subprocess,sys,urllib.request,venv
from pathlib import Path

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root',type=Path,required=True)
    ap.add_argument('--expected-commit',required=True)
    args=ap.parse_args()
    repo=Path(__file__).resolve().parents[3]
    if platform.system()!='Linux' or platform.machine()!='x86_64' or platform.python_version()!='3.11.14':
        raise RuntimeError('Requires the specified Linux x86_64 Python 3.11.14 base runtime')
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
    if head!=args.expected_commit or subprocess.check_output(['git','status','--porcelain'],cwd=repo,text=True).strip():
        raise RuntimeError('Clean exact committed source required')
    root=args.root.absolute()
    if not root.is_relative_to('/work/abussing/bsfm-consolidation/environments') or root.exists():
        raise RuntimeError('Fresh isolated environment root required under the nominated HPC directory')
    root.mkdir(parents=True,exist_ok=False)
    lockpath=Path(__file__).with_name('LINUX_ENVIRONMENT_PROPOSAL.json')
    lock=json.loads(lockpath.read_text());cache=root/'wheels';cache.mkdir()
    report=dict(schema='bsfm.linux-environment-build.v1',status='incomplete',git_commit=head,
        script_sha256=sha(__file__),lock_sha256=sha(lockpath),scope='Environment restoration only; no numerical/scientific validation',
        base_runtime=dict(executable=sys.executable,sha256=sha(sys.executable),version=sys.version,
                          prefix=sys.prefix,platform=platform.platform()),archives=[])
    log=root/'build.log'
    def run(command):
        with log.open('a') as f:
            f.write(json.dumps(command)+'\n');f.flush()
            subprocess.run(command,stdout=f,stderr=subprocess.STDOUT,check=True,env=dict(os.environ,
                PYTHONNOUSERSITE='1',JAX_PLATFORMS='cpu',JAX_ENABLE_X64='true',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1'))
    try:
        requirements=[]
        for row in lock['packages']:
            p=cache/row['url'].rsplit('/',1)[-1]
            with urllib.request.urlopen(row['url'],timeout=120) as source,p.open('xb') as target:
                while block:=source.read(1024*1024):target.write(block)
            if sha(p)!=row['sha256']:raise RuntimeError('Wheel hash mismatch: '+p.name)
            report['archives'].append(dict(name=p.name,bytes=p.stat().st_size,sha256=sha(p)))
            requirements.append(f"{row['name']}=={row['version']} --hash=sha256:{row['sha256']}")
        req=root/'requirements.lock.txt';req.write_text('\n'.join(requirements)+'\n')
        venv.create(root/'python',with_pip=True,symlinks=False,system_site_packages=False)
        python=str(root/'python/bin/python')
        run([python,'-I','-m','pip','install','--no-index','--no-deps','--require-hashes','--find-links',str(cache),'-r',str(req)])
        run([python,'-I','-m','pip','check'])
        probe="""import importlib.metadata as m,json,site,sys,pathlib
from threadpoolctl import threadpool_info
import numpy,scipy,jax,jaxlib,blackjax
assert not site.ENABLE_USER_SITE
assert jax.default_backend()=='cpu' and jax.config.x64_enabled
mods={n:str(pathlib.Path(v.__file__).resolve()) for n,v in [('numpy',numpy),('scipy',scipy),('jax',jax),('jaxlib',jaxlib),('blackjax',blackjax)]}
assert all(pathlib.Path(p).is_relative_to(pathlib.Path(sys.prefix)) for p in mods.values())
packages={d.metadata['Name'].lower().replace('_','-'):d.version for d in m.distributions()}
expected=json.loads(pathlib.Path(sys.argv[1]).read_text())['packages']
assert all(packages[r['name'].lower().replace('_','-')]==r['version'] for r in expected)
pathlib.Path(sys.argv[2]).write_text(json.dumps(dict(packages=packages,module_paths=mods,executable=sys.executable,base_prefix=sys.base_prefix,cpu=True,x64=True,blas=threadpool_info()),indent=2)+'\\n')
"""
        run([python,'-I','-c',probe,str(lockpath),str(root/'package-validation.json')])
        report['status']='environment_restored_numerical_validation_pending'
        report['package_report_sha256']=sha(root/'package-validation.json')
    finally:
        (root/'build-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status=report['status'],root=str(root))))

if __name__=='__main__':main()
