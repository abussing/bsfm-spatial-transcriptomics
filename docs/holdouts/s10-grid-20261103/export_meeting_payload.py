import json,gzip,base64,textwrap,hashlib
from pathlib import Path
p=Path('/work/abussing/bsfm-consolidation/evidence/meeting-flat-922a558')
d=json.loads((p/'report.json').read_text());rs=d['configurations'];sel=[];reasons={}
criteria=[('high observed variance',lambda g:sum(r['gene_variance'][g] for r in rs),True),('largest relative prediction error',lambda g:sum(r['gene_rmse'][g]/max(r['gene_baseline_rmse'][g],1e-10) for r in rs),True),('lowest relative prediction error',lambda g:sum(r['gene_rmse'][g]/max(r['gene_baseline_rmse'][g],1e-10) for r in rs),False)]
for label,key,rev in criteria:
    choices=[g for g in sorted(range(91),key=key,reverse=rev) if g not in sel][:2]
    for g in choices:sel.append(g);reasons[g]=label
d['selected']=sel;d['reasons']=reasons
for r in rs:
    for k in ['train_xy','test_xy','train_type','test_type']:r.pop(k)
    for k in ['truth','mean']:r[k]=[[round(v,3) for v in r[k][g]] for g in sel]
raw=gzip.compress(json.dumps(d,separators=(',',':')).encode())
(p/'meeting-data.json.gz').write_bytes(raw)
b=base64.b64encode(raw).decode();(p/'meeting-data.b64').write_text(b)
print('EXPORT_BYTES',len(b));print('EXPORT_SHA',hashlib.sha256(raw).hexdigest())
