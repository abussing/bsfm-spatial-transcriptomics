"""Run only the review store's inherited fault suite, with an external receipt."""
import argparse,hashlib,json,os,sys,time,unittest
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
p.add_argument('--reuse-template',type=Path);p.add_argument('--case');a=p.parse_args()
repo=Path(__file__).resolve().parents[3];sys.path[:0]=[str(repo/'src'),str(repo/'tests')]
os.environ['PYTHONPATH']=os.pathsep.join([str(repo/'src'),str(repo/'tests')])
assert not a.output.exists()
import test_sampler_incremental
if a.reuse_template:
    if a.case!='test_fresh_process_kill_and_recovery':
        raise ValueError('Template reuse is limited to the failed fresh-process case')
    from unittest.mock import patch
    from sampler_layer9_support import controller
    from bsfm.sampler.run_genesis import load_genesis
    from bsfm.sampler.run_storage import read_json
    from bsfm.sampler.checkpoint_contract import digest
    from bsfm.sampler.retained_archive import RetainedArchive
    from bsfm.sampler.run_incremental import IncrementalTransactions
    def reuse(cls):
        switch=patch('bsfm.sampler.run_controller.Transactions',IncrementalTransactions)
        switch.start();cls.addClassCleanup(switch.stop)
        cls.template=a.reuse_template;c=controller(cls.template)
        cls.genesis,_=load_genesis(c.store.segment/'genesis/endpoint.npz',c.target,c.cp)
        cls.reference_chain=c.store.scan(cls.genesis,digest(read_json(c.store.segment/'genesis/receipt.json')))
        archive=RetainedArchive(c.store.segment/'archive',target=c.target,contract=c.rc,b_sigma2=c.scale)
        archive.require_resume_boundary(cls.reference_chain['endpoint'])
        cls.complete=read_json(c.store.segment/'completion.json')
        assert cls.complete['head']==cls.reference_chain['head'] and cls.complete['completed']==2
        cls.reference_sources=None
    test_sampler_incremental.IncrementalTests.setUpClass=classmethod(reuse)
start=time.monotonic()
suite=(unittest.TestSuite([test_sampler_incremental.IncrementalTests(a.case)]) if a.case else
       unittest.defaultTestLoader.loadTestsFromTestCase(test_sampler_incremental.IncrementalTests))
result=unittest.TextTestRunner(verbosity=2).run(suite)
receipt={'scope':'Local CPU synthetic incremental orchestration candidate; no HPC deployment',
 'tests_run':result.testsRun,'failures':[(str(t),e) for t,e in result.failures],
 'errors':[(str(t),e) for t,e in result.errors],'skipped':[(str(t),e) for t,e in result.skipped],
 'elapsed_seconds':time.monotonic()-start,'status':'PASS' if result.wasSuccessful() else 'FAIL',
 'selected_case':a.case,'reused_template':str(a.reuse_template) if a.reuse_template else None,
 'source_hashes':{str(f.relative_to(repo)):hashlib.sha256(f.read_bytes()).hexdigest()
  for f in [repo/'src/bsfm/sampler/run_incremental.py',repo/'tests/test_sampler_incremental.py']}}
a.output.write_text(json.dumps(receipt,indent=2)+'\n')
sys.exit(0 if result.wasSuccessful() else 1)
