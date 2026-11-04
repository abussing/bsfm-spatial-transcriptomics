"""Explicit RData list adapter to the portable dataset contract.

Requires a dense normalized response with exact dimnames, 2D coordinates and a
character group vector. No implicit gene aliases, normalization or animal IDs.
"""
import argparse
import csv
import json
from pathlib import Path
import subprocess
import tempfile
import numpy as np
from .dataset import file_hash,write_dataset


def import_rdata(source,recipe,rscript,output):
    source,output=Path(source).resolve(),Path(output).resolve()
    if output.exists():raise FileExistsError(output)
    before=file_hash(source)
    if before!=recipe['source_sha256']:raise ValueError('RData source hash mismatch')
    if recipe['metadata']['animal_identity_known'] is not False:
        raise ValueError('This adapter requires unknown animal IDs; use a metadata adapter for known animals')
    if not isinstance(recipe['sample'],str) or not recipe['sample'].strip():raise ValueError('Explicit sample identity required')
    output.parent.mkdir(parents=True,exist_ok=True)
    # Keep logs and extracted identities externally. Large staging binary is
    # temporary and owned by TemporaryDirectory; the source is never modified.
    with tempfile.TemporaryDirectory(prefix='.rdata-import-',dir=output.parent) as tmp:
        stage=Path(tmp)
        command=[str(rscript),'--vanilla',str(Path(__file__).with_name('export_rdata.R')),
                 str(source),recipe['object'],recipe['expression_field'],recipe['coordinate_field'],
                 recipe['group_field'],str(stage)]
        result=subprocess.run(command,capture_output=True)
        if result.returncode:
            raise RuntimeError('R data export failed: '+result.stderr.decode(errors='replace')[-4000:])
        with (stage/'genes.csv').open(encoding='utf-8-sig',newline='') as f:genes=[r['gene'] for r in csv.DictReader(f)]
        with (stage/'cells.csv').open(encoding='utf-8-sig',newline='') as f:cells=list(csv.DictReader(f))
        y=np.fromfile(stage/'expression.f64',dtype='<f8').reshape((len(genes),len(cells)),order='F')
        data=dict(expression=y,coordinates=np.array([[float(r['axis0']),float(r['axis1'])] for r in cells],dtype=np.float64),
                  gene_names=np.array(genes),cell_names=np.array([r['cell'] for r in cells]),
                  group_names=np.array([r['group'] for r in cells]),sample_names=np.array([recipe['sample']]*len(cells)),
                  animal_names=np.array(['']*len(cells)),source_row_indices=np.array([int(r['source_row']) for r in cells],dtype=np.int64))
        if file_hash(source)!=before:raise ValueError('Source changed during import')
        metadata=dict(recipe['metadata'],adapter=dict(object=recipe['object'],expression_field=recipe['expression_field'],
            coordinate_field=recipe['coordinate_field'],group_field=recipe['group_field'],
            source_column_alignment='explicit recipe assertion: coordinates and groups follow expression columns',
            R_session=(stage/'R-session.txt').read_text(),rscript_sha256=file_hash(rscript),
            exporter_sha256=file_hash(Path(__file__).with_name('export_rdata.R')),
            stderr=result.stderr.decode(errors='replace')))
        return write_dataset(output,data,metadata,sources=[dict(path=str(source),sha256=before)])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--recipe',type=Path,required=True)
    p.add_argument('--rscript',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();recipe=json.loads(a.recipe.read_text(encoding='utf-8'))
    if recipe.get('column_alignment_confirmed') is not True:
        raise ValueError('Recipe must explicitly confirm source column alignment')
    receipt=import_rdata(a.source,recipe,a.rscript,a.output)
    print(json.dumps(dict(dimensions=receipt['dimensions'],manifest_sha256=file_hash(a.output/'dataset.json')),indent=2))


if __name__=='__main__':main()
