"""Small synthetic payload and deliberate corruption tests; no SCT fitting."""
import copy
import base64
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import h5py
import numpy as np

from bsfm.preprocessing.raw_preflight import ContractError
from bsfm.preprocessing.execution_evidence import embed_log, authenticate_log
from bsfm.preprocessing.response_contract import (CONFIG, META, contract, file_record,
    save_json, payload_hash, load_json)
from bsfm.preprocessing.response_run import write_response, promote, run
from bsfm.preprocessing.response_validate import (check_response, check_final_metadata,
    validate_bundle, check_execution)


class ResponseBundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.cfg, self.panel, self.spec, self.registry = contract()
        self.section = self.registry['sections'][0]['section']
        self.bundle = self.root/self.section
        self.bundle.mkdir()
        genes = np.array([f'other{i}' for i in range(300)], dtype=object)
        genes[self.panel['raw_300_positions_zero_based']] = self.panel['genes']
        n = 32
        metadata = {k:np.repeat('fixture',n).astype(object) for k in META}
        metadata['cluster_coarse'] = np.tile(['OGC','other','Mic','AST'],8).astype(object)
        self.raw = {'genes':genes, 'cells':np.array([f'c{i}' for i in range(n)],dtype=object),
            'rows':np.arange(n,dtype=np.int64)*2, 'coordinates':np.arange(n*2,dtype=float).reshape(n,2),
            'metadata':metadata}
        c = np.arange(300*n,dtype=float).reshape(300,n)%17
        self.reconstructed = {'corrected':c, 'response':np.log1p(c)}
        write_response(self.bundle/'response.h5',self.raw,c,self.reconstructed['response'],self.panel,self.spec,self.cfg)

    def tearDown(self):
        self.temp.cleanup()

    def check(self):
        return check_response(self.bundle/'response.h5',self.raw,self.panel,self.spec,self.cfg,self.reconstructed)

    def final_metadata(self):
        result = self.check()
        report = {'section':self.section,'source':{'path':'fixture','bytes':5483600151,'sha256':self.panel['raw_source_sha256']},
            'animal_label':'animal','genotype':'genotype','code_commit':'0'*40,
            'identities':{k:'0'*64 for k in ['panel_registry_sha256','panel_order_sha256','section_registry_sha256','bundle_spec_sha256','run_spec_sha256','environment_source_lock_sha256','renv_lock_sha256']},
            'independent_readback':{'process':{'exit_code':0,'failure':None,
                'log':{**embed_log(b'clean readback\r\n'), 'path':str(self.root/'nonexistent.log')}}},**result}
        report['identities']['panel_order_sha256']=self.panel['ordered_hash']['value']
        for name in ['fit.rds','execution.json','session.txt']:
            (self.bundle/name).write_bytes(b'fixture only')
        save_json(self.bundle/'validation.json',report)
        manifest={'schema':self.spec['bundle_schema'],'status':'complete',
            **{k:report[k] for k in ['section','source','animal_label','genotype','code_commit','identities','datasets','axes','dimensions']},
            'regime':self.spec['regime'],'coordinates':self.spec['coordinates'],'validation':report['metrics'],
            'artifacts':{n:file_record(self.bundle/n) for n in self.spec['required_files']}}
        save_json(self.bundle/'manifest.json',manifest)
        return manifest,report

    def test_complete_payload_and_independent_centering(self):
        report=self.check()
        self.assertEqual(report['group_sizes'],[8,8,8])
        self.assertLess(report['metrics']['max_abs_centering_mean'],1e-12)
        self.assertEqual(report['dimensions']['model_cells'],24)

    def test_payload_hash_is_logical_C_order_not_storage_order(self):
        a=np.arange(12,dtype=float).reshape(3,4)
        self.assertEqual(payload_hash(a,'float64'),payload_hash(np.asfortranarray(a),'float64'))
        self.assertNotEqual(payload_hash(a,'float64'),payload_hash(a.T,'float64'))

    def test_corrupt_axes_and_mappings(self):
        for name in ['/axes/genes91/ids','/axes/cells_model/ids','/axes/cells_model/source_row',
                     '/axes/genes91/all_gene_index','/metadata/model_type_code','/axes/types/codes']:
            with self.subTest(dataset=name),h5py.File(self.bundle/'response.h5','r+') as f:
                original=f[name][:]; f[name][0]=f[name][-1]
            with self.assertRaises(ContractError): self.check()
            with h5py.File(self.bundle/'response.h5','r+') as f: f[name][:]=original

    def test_corrupt_values_coordinates_and_centering(self):
        for name in ['/all/corrected_counts','/all/log1p_response','/model/uncentered_response',
                     '/model/centered_response','/centering/means','/coordinates/model_source',
                     '/coordinates/all_source']:
            with self.subTest(dataset=name),h5py.File(self.bundle/'response.h5','r+') as f:
                original=f[name][0,0]; f[name][0,0]=original+0.5
            with self.assertRaises(ContractError): self.check()
            with h5py.File(self.bundle/'response.h5','r+') as f: f[name][0,0]=original

    def test_nonfinite_and_negative_counts(self):
        for value in [np.nan,-1.,1.5]:
            with h5py.File(self.bundle/'response.h5','r+') as f: f['/all/corrected_counts'][0,0]=value
            with self.assertRaises(ContractError): self.check()

    def test_missing_dataset_and_axis_hash(self):
        with h5py.File(self.bundle/'response.h5','r+') as f: f['/model/centered_response'].attrs['axis_hashes']='[]'
        with self.assertRaises(ContractError): self.check()
        with h5py.File(self.bundle/'response.h5','r+') as f: del f['/centering/group_sizes']
        with self.assertRaises(ContractError): self.check()

    def test_source_metadata_and_coordinate_units_corruption(self):
        with h5py.File(self.bundle/'response.h5','r+') as f: f['/metadata/all/gen'][0]='wrong animal'
        with self.assertRaises(ContractError): self.check()
        with h5py.File(self.bundle/'response.h5','r+') as f:
            f['/metadata/all/gen'][0]='fixture'
            c=copy.deepcopy(self.spec['coordinates']); c['units']='microns'; f.attrs['coordinates_contract']=json.dumps(c)
        with self.assertRaises(ContractError): self.check()

    def test_manifest_hashes_and_no_extra_files(self):
        m,r=self.final_metadata(); check_final_metadata(self.bundle,m,r,self.spec)
        bad=copy.deepcopy(m); bad['artifacts']['response.h5']['sha256']='0'*64
        with self.assertRaises(ContractError): check_final_metadata(self.bundle,bad,r,self.spec)
        (self.bundle/'unexpected').write_text('x')
        with self.assertRaises(ContractError): check_final_metadata(self.bundle,m,r,self.spec)

    def test_manifest_regime_and_identity_mutations(self):
        m,r=self.final_metadata()
        for field,value in [('regime',{'preprocessing_regime':'training_only'}),('section','unknown'),('status','writing')]:
            bad=copy.deepcopy(m); bad[field]=value
            with self.assertRaises(Exception): check_final_metadata(self.bundle,bad,r,self.spec)
        bad=copy.deepcopy(m);bad['axes']['genes91']['ordered_sha256']='0'*64
        with self.assertRaises(ContractError): check_final_metadata(self.bundle,bad,r,self.spec)

    def test_incomplete_attempt_cannot_be_consumed_or_promoted(self):
        attempt=self.root/'.attempt-test';attempt.mkdir()
        with self.assertRaises(ContractError): validate_bundle(attempt,Path('unused'),Path('unused'),CONFIG,self.root/'work')
        with self.assertRaises(ContractError): promote(attempt,self.root/'final')
        self.assertFalse((self.root/'final').exists())

    def test_promotion_and_no_overwrite(self):
        m,r=self.final_metadata()
        parent=self.root/'final';parent.mkdir(); destination=parent/self.section
        promote(self.bundle,destination)
        self.assertTrue((destination/'manifest.json').is_file())
        with self.assertRaises(ContractError): promote(destination,destination)

    def test_unknown_section_and_changed_config_rejected_before_fit(self):
        with patch('bsfm.preprocessing.response_run.run_r') as fit:
            with self.assertRaises(ContractError): run('unknown',Path('unused'),Path('unused'),CONFIG,self.root/'new')
            changed=load_json(CONFIG);changed['normalization']['depth']=125
            p=self.root/'changed.json';p.write_text(json.dumps(changed))
            with self.assertRaises(ContractError): contract(p)
            fit.assert_not_called()

    def test_failed_fit_leaves_no_final_bundle(self):
        fake=copy.deepcopy(self.raw);fake['counts']=np.ones((32,300));fake['source']={}
        with patch('bsfm.preprocessing.response_run.require_clean_code',return_value={}),patch('bsfm.preprocessing.response_run.identities',return_value={}),patch('bsfm.preprocessing.response_run.raw_section',return_value=fake),patch('bsfm.preprocessing.response_run.run_r',side_effect=ContractError('interrupted')):
            with self.assertRaisesRegex(ContractError,'interrupted'): run(self.section,Path('unused'),Path('unused'),CONFIG,self.root/'failed')
        self.assertFalse((self.root/'failed'/'sections'/self.section).exists())
        self.assertEqual(len(list((self.root/'failed'/'attempts').glob('.attempt-*/failure.json'))),1)

    def test_incomplete_final_and_false_completion_rejected(self):
        with self.assertRaises(FileNotFoundError):
            validate_bundle(self.bundle,Path('unused'),Path('unused'),CONFIG,self.root/'work')
        m,r=self.final_metadata()
        (self.bundle/'fit.rds').unlink()
        with self.assertRaises(ContractError): check_final_metadata(self.bundle,m,r,self.spec)

    def test_missing_group_and_variance_scaling_rejected(self):
        with h5py.File(self.bundle/'response.h5','r+') as f:
            f['/centering/group_sizes'][0]=0
        with self.assertRaises(ContractError): self.check()
        with h5py.File(self.bundle/'response.h5','r+') as f:
            f['/centering/group_sizes'][0]=8
            f['/model/centered_response'][:]=f['/model/centered_response'][:]*2
        with self.assertRaises(ContractError): self.check()

    def test_stack_warning_and_execution_identity_failures(self):
        log=self.root/'fit.log';log.write_text('stack imbalance warning')
        process={'exit_code':0,'failure':None,'log':{**embed_log(log.read_bytes()),'path':str(log)}}
        fit={'status':'pass','effective_method':'glmGamPoi_offset','depth':124,'seed':1448145,
             'RNG':['Mersenne-Twister','Inversion','Rejection'],'input_cells':32,'fitting_cells':32,
             'input_genes':300,'gene_availability':{'modeled_by_SCT':300,'unavailable':[]},
             'versions':{'Seurat':'5.4.0','SeuratObject':'5.4.0','sctransform':'0.4.3','Matrix':'1.7-4','glmGamPoi':'1.22.0'},
             'R':'4.5.3','Bioconductor':'3.22','threads':{'OMP_NUM_THREADS':'1'}}
        raw={**self.raw,'source':{}}
        e={'schema':'bsfm.single-section-execution.v1','identities':{},'code':{},'source':{},
           'run_configuration':self.cfg,'environment_root':str(self.root.resolve()),
           'normalization':{'report':fit,'process':process},'transport_readback':{'process':process,'report':{'warnings':[]}}}
        with patch('bsfm.preprocessing.response_validate.identities',return_value={}),patch('bsfm.preprocessing.response_validate.code_identity',return_value={}):
            with self.assertRaisesRegex(ContractError,'Stack imbalance'): check_execution(e,raw,CONFIG,self.root)
            log.write_text('clean');process['log']={**embed_log(log.read_bytes()),'path':str(log)}
            log.unlink()
            check_execution(e,raw,CONFIG,self.root)
            for field,value in [('effective_method','fallback'),('fitting_cells',31),('depth',125),('gene_availability',{'modeled_by_SCT':299,'unavailable':['x']})]:
                bad=copy.deepcopy(e);bad['normalization']['report'][field]=value
                with self.assertRaises(ContractError):check_execution(bad,raw,CONFIG,self.root)
            for field in ['identities','code','source']:
                bad=copy.deepcopy(e);bad[field]={'changed':True}
                with self.assertRaises(ContractError):check_execution(bad,raw,CONFIG,self.root)

    def test_embedded_bytes_are_exact_and_external_path_is_never_opened(self):
        content=b'progress\r\n\xffwarning: diagnostic\r\n'
        log=embed_log(content); log['path']=str(self.root/'missing-attempt'/'never-created.log')
        with patch.object(Path,'open',side_effect=AssertionError('Must not open an external log')):
            self.assertEqual(authenticate_log(log),content)
        self.assertEqual(log['warning_scan']['warning_lines'],['\ufffdwarning: diagnostic'])

    def test_embedded_byte_mutation_fails(self):
        log=embed_log(b'clean log')
        log['data']=base64.b64encode(b'other log').decode()
        with self.assertRaisesRegex(ContractError,'SHA-256'): authenticate_log(log)

    def test_embedded_hash_and_length_mutations_fail(self):
        for key,value in [('sha256','0'*64),('bytes',100)]:
            with self.subTest(key=key):
                log=embed_log(b'clean');log[key]=value
                with self.assertRaises(ContractError):authenticate_log(log)

    def test_embedded_encoding_and_scan_mutations_fail(self):
        for key,value in [('encoding','utf8'),('data','!invalid base64!'),('warning_scan',{})]:
            with self.subTest(key=key):
                log=embed_log(b'clean');log[key]=value
                with self.assertRaises(ValueError):authenticate_log(log)

    def test_embedded_stack_warning_fails_even_with_recomputed_hash(self):
        for content in [b'Warning: stack imbalance in call',b'STACK-IMBALANCE',b'stack\nimbalance']:
            with self.subTest(content=content),self.assertRaisesRegex(ContractError,'Stack imbalance'):
                authenticate_log(embed_log(content))

    def test_copied_six_file_bundle_metadata_is_independent_of_original(self):
        m,r=self.final_metadata()
        destination=self.root/'isolated'/self.section;destination.mkdir(parents=True)
        for name in set(self.spec['required_files'])|{'manifest.json'}:
            shutil.copyfile(self.bundle/name,destination/name)
        # These temporary fixture files are bounded by this test's TemporaryDirectory.
        for name in list(self.bundle.iterdir()): name.unlink()
        self.bundle.rmdir()
        check_final_metadata(destination,load_json(destination/'manifest.json'),load_json(destination/'validation.json'),self.spec)
        self.assertEqual(len(list(destination.iterdir())),6)

    def test_final_validator_rejects_embedded_mutations_with_outer_hashes_updated(self):
        m,r=self.final_metadata()
        for key,value in [('data',base64.b64encode(b'corrupt').decode()),('sha256','0'*64),('bytes',0)]:
            with self.subTest(key=key):
                altered=copy.deepcopy(r);altered['independent_readback']['process']['log'][key]=value
                (self.bundle/'validation.json').write_text(json.dumps(altered))
                updated=copy.deepcopy(m);updated['artifacts']['validation.json']=file_record(self.bundle/'validation.json')
                with self.assertRaises(ContractError):check_final_metadata(self.bundle,updated,altered,self.spec)
        altered=copy.deepcopy(r)
        altered['independent_readback']['process']['log']=embed_log(b'Warning: stack imbalance')
        (self.bundle/'validation.json').write_text(json.dumps(altered))
        updated=copy.deepcopy(m);updated['artifacts']['validation.json']=file_record(self.bundle/'validation.json')
        with self.assertRaisesRegex(ContractError,'Stack imbalance'):check_final_metadata(self.bundle,updated,altered,self.spec)


if __name__=='__main__':
    unittest.main()
