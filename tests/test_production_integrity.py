"""Real fast validator against synthetic six-file bundles, separate from launcher stubs."""
import copy
import csv
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import test_response_bundle as fixtures
from bsfm.preprocessing.execution_evidence import embed_log
from bsfm.preprocessing.response_contract import CONFIG, code_identity, file_record
from bsfm.preprocessing.response_validate import fast_validate_bundle
from bsfm.preprocessing.response_run import run
from bsfm.preprocessing.raw_preflight import ContractError
from bsfm.preprocessing.raw_preflight import ordered_hash, sha256_file
from bsfm.preprocessing.response_contract import raw_section
from bsfm.preprocessing.source_attestation import source_session


class ProductionIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.ResponseBundleTests();self.fixture.setUp();self.addCleanup(self.fixture.tearDown)
        f=self.fixture;self.manifest,self.report=f.final_metadata();code=code_identity()
        self.ids=self.report['identities'];self.report['code_commit']=code['commit']
        self.report.update(schema='bsfm.response-validation.v1',status='pass',tolerances=f.cfg['tolerances'])
        process={'exit_code':0,'failure':None,'log':{**embed_log(b'clean'), 'path':str(f.root/'absent.log')}}
        fit={'status':'pass','effective_method':'glmGamPoi_offset','depth':124,'seed':1448145,
             'RNG':['Mersenne-Twister','Inversion','Rejection'],'input_cells':32,'fitting_cells':32,
             'input_genes':300,'gene_availability':{'modeled_by_SCT':300,'unavailable':[]},
             'versions':{'Seurat':'5.4.0','SeuratObject':'5.4.0','sctransform':'0.4.3','Matrix':'1.7-4','glmGamPoi':'1.22.0'},
             'R':'4.5.3','Bioconductor':'3.22','threads':{'OMP_NUM_THREADS':'1'},'semantic_sha256':{'synthetic':'a'*64}}
        self.report['independent_readback']['report']={'semantic_sha256':fit['semantic_sha256'],'effective_arguments':{'fixture':True}}
        self.execution={'schema':'bsfm.single-section-execution.v1','section':f.section,'identities':self.ids,
            'code':code,'source':self.report['source'],'run_configuration':f.cfg,'environment_root':str(f.root.resolve()),
            'normalization':{'report':fit,'process':process},
            'transport_readback':{'process':process,'report':{'warnings':[],'effective_arguments':{'fixture':True}}},
            'production_run_spec_sha256':'b'*64,'attempt_id':'.attempt-fixture'}
        self.manifest['code_commit']=code['commit'];self.write()

    def write(self):
        f=self.fixture
        (f.bundle/'execution.json').write_text(json.dumps(self.execution))
        (f.bundle/'validation.json').write_text(json.dumps(self.report))
        self.manifest['artifacts']={n:file_record(f.bundle/n) for n in f.spec['required_files']}
        (f.bundle/'manifest.json').write_text(json.dumps(self.manifest))

    def validate(self):
        f=self.fixture
        with patch('bsfm.preprocessing.response_validate.identities',return_value=self.ids):
            return fast_validate_bundle(f.bundle,f.section,self.report['source'],f.root,CONFIG,'b'*64)

    def test_real_fast_check_requires_no_external_logs_or_R(self):
        with patch('bsfm.preprocessing.response_validate.readback',side_effect=AssertionError('No R on fast resume')):
            r=self.validate();self.assertEqual(r['original_deep_validation'],'pass')
            self.assertEqual(r['validation'],'fast_closed_file_schema_hash_provenance')

    def test_corrupt_closed_file_detected(self):
        with (self.fixture.bundle/'response.h5').open('ab') as f:f.write(b'corrupt')
        with self.assertRaises(ContractError):self.validate()

    def test_wrong_run_or_code_or_failed_deep_report_rejected(self):
        for key,value in [('production_run_spec_sha256','c'*64),('code',{})]:
            original=copy.deepcopy(self.execution);self.execution[key]=value;self.write()
            with self.assertRaises(ContractError):self.validate()
            self.execution=original
        self.report['status']='failed';self.write()
        with self.assertRaises(ContractError):self.validate()

    def test_embedded_warning_rejected_even_after_rehash(self):
        self.execution['normalization']['process']['log']=embed_log(b'Warning: stack imbalance')
        self.write()
        with self.assertRaisesRegex(ContractError,'Stack imbalance'):self.validate()

    def test_shared_existing_root_and_overwrite_rejected_before_fit(self):
        f=self.fixture;root=f.root/'shared';root.mkdir();raw=copy.deepcopy(f.raw)
        import numpy as np
        raw.update(counts=np.ones((32,300)),source={})
        with patch('bsfm.preprocessing.response_run.require_clean_code',return_value={}),patch('bsfm.preprocessing.response_run.identities',return_value={}),patch('bsfm.preprocessing.response_run.raw_section',return_value=raw),patch('bsfm.preprocessing.response_run.run_r',side_effect=RuntimeError('reached fit')) as fit:
            with self.assertRaisesRegex(RuntimeError,'reached fit'):run(f.section,Path('unused'),f.root,CONFIG,root)
            self.assertEqual(fit.call_count,1)
            (root/'sections'/f.section).mkdir()
            with self.assertRaisesRegex(ContractError,'overwrite'):run(f.section,Path('unused'),f.root,CONFIG,root)
            self.assertEqual(fit.call_count,1)

    def test_raw_section_live_attestation_skips_hash_but_preserves_data_checks(self):
        import h5py
        import numpy as np
        f=self.fixture;source=f.root/'tiny.h5ad';raw=f.raw
        with h5py.File(source,'w') as h:
            for group,axis in [('obs',raw['cells']),('var',raw['genes'])]:
                g=h.create_group(group);g.attrs['_index']='_index'
                g.create_dataset('_index',data=axis,dtype=h5py.string_dtype())
            for k,v in raw['metadata'].items():h['obs'].create_dataset(k,data=v,dtype=h5py.string_dtype())
            h['obs'].create_dataset('center_y',data=raw['coordinates'][:,0])
            h['obs'].create_dataset('center_x',data=raw['coordinates'][:,1])
            h.create_dataset('obsm/spatial',data=raw['coordinates'])
            h.create_dataset('layers/RNA',data=np.ones((32,300)))
        expected={'bytes':source.stat().st_size,'sha256':sha256_file(source)}
        audit={'source':expected,'schema_checks':{'gene_order_sha256':ordered_hash(raw['genes']),'cell_order_sha256':ordered_hash(raw['cells'])}}
        directory=f.root/'docs/preprocessing/audits/20261030_raw';directory.mkdir(parents=True)
        row={'section':f.section,'eligible_cells':32,'eligible_cell_order_sha256':ordered_hash(raw['cells']),
             'eligible_MIC':8,'eligible_AST':8,'eligible_OGC':8,'total_median':300}
        with (directory/'sections.csv').open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(row));writer.writeheader();writer.writerow(row)
        registry={'sections':[{'section':f.section,'sample':'fixture','gen_fine':'fixture'}]}
        with patch('bsfm.preprocessing.response_contract.REPO',f.root),patch('bsfm.preprocessing.response_contract.load_json',return_value=audit),patch('bsfm.preprocessing.response_contract.contract',return_value=(f.cfg,f.panel,f.spec,registry)):
            with source_session(source,expected) as (token,start),patch('bsfm.preprocessing.response_contract.sha256_file',side_effect=AssertionError('Must not hash per section')):
                got=raw_section(source,f.section,CONFIG,attestation=token)
                self.assertEqual(got['counts'].shape,(32,300))
                with self.assertRaises(ContractError):raw_section(source,f.section,CONFIG,attestation=token.record())
            with patch('bsfm.preprocessing.response_contract.sha256_file',wraps=sha256_file) as hashed:
                raw_section(source,f.section,CONFIG);self.assertEqual(hashed.call_count,1)


if __name__=='__main__':unittest.main()
