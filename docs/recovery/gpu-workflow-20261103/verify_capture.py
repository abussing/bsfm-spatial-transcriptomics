"""Authenticate bounded text captures and distinguish source identity from execution."""
import argparse,csv,hashlib,json
from pathlib import Path,PureWindowsPath
p=argparse.ArgumentParser();p.add_argument('--capture',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
a=p.parse_args();repo=Path(__file__).resolve().parents[3]
records=list(csv.DictReader((repo/'docs/recovery/BSFM_SAMPLER_SOURCES.csv').open()))
selected_root=PureWindowsPath(r'D:\johnston_brain\run_bundles\bsfm_l4_k20_cell50_fmesher_20261026_v1\code\sampler')
selected={PureWindowsPath(r['source_path']).name:r for r in records
          if PureWindowsPath(r['source_path']).parent==selected_root}
capture=json.loads(a.capture.read_text());rows=[]
for path,item in capture.items():
    raw=item['text'].encode('utf-8')
    if len(raw)!=item['bytes'] or hashlib.sha256(raw).hexdigest()!=item['sha256']:
        raise ValueError('Capture text differs from measured bytes: '+path)
    row={'path':path,'bytes':len(raw),'sha256':item['sha256'],'evidence':'measured source bytes; not execution'}
    if '/sampler/' in path:
        reference=selected.get(Path(path).name)
        if reference is None:raise ValueError('No selected-source identity: '+path)
        # All captured selected sampler files must agree, not merely filenames.
        if reference['sha256']!=item['sha256'] or int(reference['bytes'])!=len(raw):
            raise ValueError('Historical candidate differs from selected source: '+path)
        row['selected_source_match']=True
    rows.append(row)
receipt={'status':'PASS','capture_sha256':hashlib.sha256(a.capture.read_bytes()).hexdigest(),
         'captured_files':len(rows),'selected_sampler_matches':sum(r.get('selected_source_match',False) for r in rows),
         'files':rows}
a.output.write_text(json.dumps(receipt,indent=2)+'\n')
print(receipt['status'],receipt['captured_files'],receipt['selected_sampler_matches'])
