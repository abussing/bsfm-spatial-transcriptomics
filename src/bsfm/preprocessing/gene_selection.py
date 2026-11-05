"""Dataset-independent expression eligibility and recurrent spatial GP selection.

The selection rule is recovered in docs/recovery/gene-panel-20261104.
This module consumes screening results; it does not fit GPs or infer animal IDs.
"""
import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np


def expression_eligible(response, *, minimum_detection, minimum_q90,
                        nonconstant_tolerance=1e-12):
    """One genes-by-observations group, in explicitly chosen nonnegative units.

    Thresholds apply together within this group. No gene SD normalization, spatial
    ranking, or minimum number of independent animals is implied by this screen.
    """
    y = np.asarray(response, dtype=np.float64)
    if y.ndim != 2 or min(y.shape) == 0 or not np.isfinite(y).all() or np.any(y < 0):
        raise ValueError('Expected finite nonnegative genes-by-observations response')
    if not math.isfinite(minimum_detection) or not 0 <= minimum_detection <= 1:
        raise ValueError('Detection threshold must lie in [0,1]')
    if not math.isfinite(minimum_q90) or minimum_q90 < 0:
        raise ValueError('Nonnegative finite q90 threshold required')
    if not math.isfinite(nonconstant_tolerance) or nonconstant_tolerance < 0:
        raise ValueError('Nonnegative finite constancy tolerance required')
    detection = np.mean(y != 0, axis=1)
    q90 = np.quantile(y, .9, axis=1, method='linear')
    span = np.ptp(y, axis=1)
    return dict(detection=detection, q90=q90, span=span,
                eligible=(detection >= minimum_detection) & (q90 >= minimum_q90)
                & (span > nonconstant_tolerance))


def select_spatial_genes(rows, *, spatial_fraction_threshold, minimum_animals,
                         allowed_celltypes, expected_animals=None):
    """Select from ONE preaggregated row per gene/celltype/animal.

    Missing GP fractions do not qualify. Missing held-out gains do not affect
    eligibility. Multiple technical sections must be aggregated upstream, not
    silently counted or combined here. Same-type recurrence is required.
    """
    if (not math.isfinite(spatial_fraction_threshold)
            or not 0 <= spatial_fraction_threshold <= 1):
        raise ValueError('Spatial threshold must lie in [0,1]')
    if type(minimum_animals) is not int or minimum_animals < 1:
        raise ValueError('Positive integer minimum_animals required')
    types = list(allowed_celltypes)
    if not types or len(set(types)) != len(types) or any(not isinstance(t,str) or not t for t in types):
        raise ValueError('Explicit unique celltype names required')
    if expected_animals is not None and (type(expected_animals) is not int or expected_animals < 1):
        raise ValueError('Positive expected_animals required')
    seen, animals, all_genes = set(), set(), set()
    passing = defaultdict(list)
    missing = 0
    for row in rows:
        gene, celltype, animal = (row[k] for k in ('gene','celltype','animal'))
        if any(not isinstance(v,str) or not v.strip() for v in (gene,celltype,animal)):
            raise ValueError('Nonempty exact gene/type/animal identities required')
        if celltype not in types:
            raise ValueError('Unconfigured celltype: '+celltype)
        key = gene, celltype, animal
        if key in seen:
            raise ValueError('Duplicate gene/type/animal row: '+repr(key))
        seen.add(key); animals.add(animal); all_genes.add(gene)
        value = row['spatial_fraction']
        if value is None or (isinstance(value,str) and value.strip() in ('','NA','NaN','nan')):
            missing += 1
            continue
        value = float(value)
        if math.isnan(value):
            missing += 1
            continue
        if not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError('Spatial fraction must lie in [0,1] or be missing')
        if value >= spatial_fraction_threshold:
            passing[gene,celltype].append((animal,value))
    if not seen:
        raise ValueError('Empty screening table')
    if expected_animals is not None and len(animals) != expected_animals:
        raise ValueError('Unexpected number of distinct animals')
    selected, decisions = [], []
    for gene in sorted(all_genes):
        choices = []
        for t in types:
            hits = passing[gene,t]
            choices.append(dict(celltype=t, qualifying_animals=len(hits),
                                median_spatial_fraction=float(np.median([v for _,v in hits])) if hits else None,
                                animals=sorted(a for a,_ in hits)))
        best = min(choices,key=lambda c:(-c['qualifying_animals'],
                   -(c['median_spatial_fraction'] if c['median_spatial_fraction'] is not None else -1),c['celltype']))
        keep = best['qualifying_animals'] >= minimum_animals
        if keep: selected.append(gene)
        decisions.append(dict(gene=gene,selected=keep,best_type=best['celltype'],support=choices))
    return dict(schema='bsfm.spatial-gene-selection.v1', genes=selected,
                spatial_fraction_threshold=spatial_fraction_threshold,
                minimum_animals=minimum_animals,allowed_celltypes=types,
                observed_animals=sorted(animals),missing_spatial_fractions=missing,
                genotype_used=False,heldout_gain_used=False,decisions=decisions)


def select_single_sample_genes(rows, *, sample, spatial_fraction_threshold,
                               allowed_celltypes):
    """Exploratory within-sample union; no fabricated animal or recurrence claim.

    Consume the existing GP screen rows. A gene qualifies when at least one
    configured group has a successful fit at or above the signal threshold.
    Require the complete gene/group rectangle so missing work cannot silently
    become a finalized panel. Non-fitted blocks remain explicit exclusions.
    """
    if not isinstance(sample,str) or not sample.strip():raise ValueError('Explicit sample required')
    if not math.isfinite(spatial_fraction_threshold) or not 0<=spatial_fraction_threshold<=1:
        raise ValueError('Spatial threshold must lie in [0,1]')
    types=list(allowed_celltypes)
    if not types or any(not isinstance(t,str) or not t.strip() for t in types) or len(set(types))!=len(types):
        raise ValueError('Explicit unique celltype names required')
    blocks={};genes=set()
    statuses={'FIT','EXPRESSION_INELIGIBLE','CONSTANT','TOO_FEW_NONZERO','CONSTANT_TRAINING_SUBSET'}
    for row in rows:
        gene=row['gene'];group=row['celltype'];status=row['status']
        if row['sample']!=sample or group not in types:raise ValueError('Unconfigured sample/group')
        if not isinstance(gene,str) or not gene.strip():raise ValueError('Exact gene identity required')
        if status not in statuses:raise ValueError('Unknown screening status')
        key=(gene,group)
        if key in blocks:raise ValueError('Duplicate gene/group block')
        value=row['spatial_fraction']
        if status=='FIT':
            if value is None or not math.isfinite(value) or not 0<=value<=1:
                raise ValueError('Invalid fitted spatial fraction')
        elif value is not None:raise ValueError('Non-fitted block has spatial fraction')
        blocks[key]=dict(celltype=group,status=status,spatial_fraction=value,
                         qualifies=status=='FIT' and value>=spatial_fraction_threshold)
        genes.add(gene)
    if not genes or len(blocks)!=len(genes)*len(types):raise ValueError('Incomplete gene/group screening table')
    decisions=[];selected=[]
    for gene in sorted(genes):
        support=[blocks[gene,t] for t in types];keep=any(r['qualifies'] for r in support)
        if keep:selected.append(gene)
        decisions.append(dict(gene=gene,selected=keep,support=support))
    return dict(schema='bsfm.single-sample-gene-selection.v1',sample=sample,
                genes=selected,allowed_celltypes=types,
                spatial_fraction_threshold=spatial_fraction_threshold,
                cross_animal_recurrence_assessed=False,heldout_gain_used=False,
                decisions=decisions)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    source=p.add_mutually_exclusive_group(required=True)
    source.add_argument('--animal-summary',type=Path)
    source.add_argument('--sample-screen',type=Path)
    p.add_argument('--recipe',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    recipe_bytes=a.recipe.read_bytes(); recipe=json.loads(recipe_bytes)
    path=a.animal_summary if a.animal_summary is not None else a.sample_screen
    raw=path.read_bytes()
    if a.sample_screen is not None:
        screen=json.loads(raw)
        if screen.get('schema')!='bsfm.gp-screen.v1':raise ValueError('Expected GP screening report')
        result=select_single_sample_genes(screen['rows'],**recipe['selection'])
    else:
        result=select_spatial_genes(list(csv.DictReader(raw.decode('utf-8').splitlines())),**recipe['selection'])
    result['provenance']=dict(source=str(path.resolve()),
        source_sha256=hashlib.sha256(raw).hexdigest(),recipe=str(a.recipe.resolve()),
        recipe_sha256=hashlib.sha256(recipe_bytes).hexdigest(),rationale=recipe['rationale'])
    with a.output.open('x',encoding='utf-8') as f:
        json.dump(result,f,indent=2,allow_nan=False);f.write('\n')


if __name__=='__main__':
    main()
