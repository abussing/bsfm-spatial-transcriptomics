"""Initial all-gene expression screen; reuse section-specific SCT, no fitting.

Same gene/type/section: >=30% nonzero, q90>=1, nonconstant finite SCT.
Retain genes passing in >=2 metadata animal groups (any qualifying type).
Technical section duplicates count once per animal. Spatial signal is not a gate.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import html
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
OUT = ROOT/'all300_expression_screen'
TYPES = ['Mic', 'AST', 'OGC']


def measure(y):
    y = np.asarray(y, dtype=float)
    finite = bool(np.isfinite(y).all())
    r = dict(n_cells=len(y), finite=finite, nonzero=np.nan, detection=np.nan,
             mean=np.nan, sd=np.nan, minimum=np.nan, maximum=np.nan,
             q10=np.nan, q25=np.nan, q50=np.nan, q75=np.nan, q90=np.nan,
             q99=np.nan, iqr=np.nan, q90_minus_q10=np.nan,
             unique_values=np.nan, modal_fraction=np.nan)
    if finite:
        assert len(y) > 0 and (y >= 0).all()
        q = np.quantile(y, [.1,.25,.5,.75,.9,.99], method='linear')
        _, counts = np.unique(y, return_counts=True)
        r.update(nonzero=int(np.count_nonzero(y)), detection=float(np.mean(y != 0)),
                 mean=float(y.mean()), sd=float(y.std()), minimum=float(y.min()), maximum=float(y.max()),
                 q10=float(q[0]), q25=float(q[1]), q50=float(q[2]), q75=float(q[3]),
                 q90=float(q[4]), q99=float(q[5]), iqr=float(q[3]-q[1]),
                 q90_minus_q10=float(q[4]-q[0]), unique_values=len(counts),
                 modal_fraction=float(counts.max()/len(y)))
    r['passes_detection'] = finite and r['detection'] >= .30
    r['passes_q90'] = finite and r['q90'] >= 1.
    # Numerical constancy only: not a new substantive SD threshold.
    r['passes_nonconstant'] = finite and r['maximum']-r['minimum'] > 1e-12
    r['passes_expression'] = r['passes_detection'] and r['passes_q90'] and r['passes_nonconstant']
    r['near_constant_review'] = finite and r['modal_fraction'] >= .95
    return r


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    OUT.mkdir(exist_ok=True)
    meta = pd.read_csv(ROOT/'audit/SECTIONS.csv')
    old = pd.read_csv(ROOT/'CANDIDATES.csv')
    fits = pd.read_csv(ROOT/'COMPLETED_FIT_REVIEW.csv')
    records, provenance = [], []
    gene_order = None
    for s in meta.itertuples():
        folder = ROOT/'sections'/s.section
        with np.load(folder/'input.npz') as z:
            genes, Y, types, available = z['genes'].astype(str), z['Y'], z['types'].astype(str), z['available']
        assert len(genes) == 300 and len(set(genes)) == 300 and Y.shape == (300,len(types))
        if gene_order is None:
            gene_order = genes.tolist()
        assert genes.tolist() == gene_order
        ready = json.loads((folder/'READY.json').read_text())
        provenance.append(dict(section=s.section, input=str(folder/'input.npz'),
            input_bytes=(folder/'input.npz').stat().st_size,
            ready_sha256=sha(folder/'READY.json'), SCT_source=ready['SCT_source'],
            SCT_sha256=ready['SCT_sha256'], normalization=ready['normalization'], scale=ready['scale']))
        for ct in TYPES:
            own = types == ct
            assert own.sum() == getattr(s, 'n_'+ct)
            for i,gene in enumerate(genes):
                r = measure(Y[i,own])
                assert r['finite'] == bool(available[i]), (s.section,gene,ct)
                records.append(dict(section=s.section, animal=s.animal_group_metadata,
                    genotype=s.genotype, celltype=ct, gene=gene, **r))
        print('SCREENED', s.section, '300 genes x3 types', flush=True)
    d = pd.DataFrame(records)
    assert len(d) == 19*300*3 and d.animal.nunique() == 15
    # Independently reproduce all existing candidate expression statistics.
    check = d.merge(fits, on=['section','gene','celltype'], suffixes=('_new','_old'), validate='one_to_one')
    assert len(check) == 4104
    for a,b in [('detection','detection_SCT'),('sd','sd_SCT'),('q90','q90_SCT')]:
        np.testing.assert_allclose(check[a],check[b],rtol=1e-9,atol=1e-12,equal_nan=True)
    d.to_csv(OUT/'GENE_TYPE_SECTION_EXPRESSION.csv', index=False)
    # One row per gene/type/animal, preserving technical-section disagreement.
    a = d.groupby(['gene','celltype','animal','genotype'],as_index=False).agg(
        sections=('section','size'), passing_sections=('passes_expression','sum'),
        passes_any_section=('passes_expression','max'), passes_all_sections=('passes_expression','min'),
        median_detection=('detection','median'), median_q90=('q90','median'), median_sd=('sd','median'))
    a.to_csv(OUT/'GENE_TYPE_ANIMAL_EXPRESSION.csv',index=False)
    anytype = d.groupby(['gene','animal','genotype'],as_index=False).passes_expression.max()
    bygroup = anytype.groupby(['gene','genotype'],as_index=False).agg(
        animals=('animal','nunique'), passing_animals=('passes_expression','sum'))
    bygroup.to_csv(OUT/'GENOTYPE_COVERAGE.csv',index=False)
    typecounts = a.groupby(['gene','celltype']).passes_any_section.sum().unstack(fill_value=0)
    summaries = []
    oldset = set(old.gene)
    paper = old.set_index('gene').paper_candidate.to_dict()
    for gene,f in d.groupby('gene'):
        hits = f[f.passes_expression]
        n = hits.animal.nunique()
        ispaper = bool(paper.get(gene,False))
        if n >= 2:
            status = 'ELIGIBLE'
        elif n == 1:
            status = 'REVIEW_SINGLE_ANIMAL'
        elif ispaper:
            status = 'REVIEW_PAPER_EXCEPTION'
        elif not f.finite.any():
            status = 'UNASSESSABLE_SCT'
        else:
            status = 'NOT_ELIGIBLE'
        g = bygroup[bygroup.gene.eq(gene)].set_index('genotype')
        summaries.append(dict(gene=gene,status=status,passing_animals=n,
            passing_sections=hits.section.nunique(),passing_type_sections=len(hits),
            qualifying_types=';'.join(sorted(hits.celltype.unique())),
            Mic_animals=int(typecounts.loc[gene,'Mic']),AST_animals=int(typecounts.loc[gene,'AST']),
            OGC_animals=int(typecounts.loc[gene,'OGC']),
            WT_animals=int(g.loc['WT','passing_animals']),
            Trem2_animals=int(g.loc['Trem2','passing_animals']),
            FAD_animals=int(g.loc['5xFAD','passing_animals']),
            Trem2_FAD_animals=int(g.loc['Trem2_5xFAD','passing_animals']),
            in_previous72=gene in oldset, known_paper_candidate=ispaper,
            near_constant_pass_blocks=int((f.passes_expression & f.near_constant_review).sum()),
            nonfinite_blocks=int((~f.finite).sum())))
    s = pd.DataFrame(summaries).sort_values(['status','gene'])
    s.to_csv(OUT/'GENE_DECISIONS.csv',index=False)
    eligible = s[s.status.eq('ELIGIBLE')]
    new = eligible[~eligible.in_previous72]
    (OUT/'ELIGIBLE_GENES.txt').write_text('\n'.join(sorted(eligible.gene))+'\n')
    (OUT/'NEWLY_ELIGIBLE_BEYOND_72.txt').write_text('\n'.join(sorted(new.gene))+'\n')
    # Reuse existing files by exact section/gene/type key; this is a worklist, not submission.
    work = d[d.gene.isin(eligible.gene) & d.passes_expression][['section','gene','celltype','animal','genotype']].copy()
    work = work.merge(fits[['section','gene','celltype','gp_status']],how='left',on=['section','gene','celltype'],validate='one_to_one')
    work['action'] = np.where(work.gp_status.isin(['FIT','REUSED_FULL_DATA']),'REUSE_EXISTING_GP','NEEDS_GP_FIT')
    work.to_csv(OUT/'ELIGIBLE_GP_WORKLIST.csv',index=False)
    # Both block counts and gene counts at each cumulative stage; no spatial thresholds.
    flow=[]
    stages=[('finite SCT', d.finite), ('plus >=30% detection', d.finite & d.passes_detection),
            ('plus q90>=1',d.finite & d.passes_detection & d.passes_q90),
            ('plus nonconstant',d.passes_expression)]
    for name,mask in stages:
        subset=d[mask]
        counts=subset.groupby('gene').animal.nunique()
        flow.append(dict(stage=name,passing_blocks=int(mask.sum()),genes_any_animal=int(counts.size),
                         genes_two_or_more_animals=int(counts.ge(2).sum())))
    q=dict(created_utc=datetime.now(timezone.utc).isoformat(),genes=300,sections=19,animal_groups=15,
        type_section_gene_blocks=len(d),thresholds=dict(detection=.30,q90_SCT=1.,numerical_nonconstant_ptp=1e-12,
            distinct_animals=2,near_constant_review_modal_fraction=.95),
        rules='All three expression criteria in the same type/section. Any type can qualify; any section can qualify an animal. No WT requirement. No spatial gate.',
        counts=s.status.value_counts().to_dict(),eligible=len(eligible),new_beyond_previous72=len(new),
        retained_previous72=int(eligible.in_previous72.sum()),
        current72_not_eligible=sorted(s.loc[s.in_previous72 & ~s.status.eq('ELIGIBLE'),'gene']),
        stage_counts=flow,GP_worklist=work.action.value_counts().to_dict(),
        matched_previous_expression_records=len(check),provenance=provenance,
        fits_launched=False, preprocessing_changed=False,
        caveat='Initial expression eligibility only, not final panel or model safety. q90 is level, not spread. Near-constant flags are review-only. Known paper labels cover the previous candidate review, not exhaustive paper annotation of all300 genes.')
    (OUT/'QC.json').write_text(json.dumps(q,indent=2)+'\n',encoding='utf-8')
    public=s.copy()
    public['gene']=public.gene.map(lambda g:f'<a href="../html/{g}.html">{html.escape(g)}</a>' if g in oldset else html.escape(g))
    page='''<!doctype html><meta charset="utf-8"><title>All300 expression eligibility</title>
<style>body{font:15px system-ui;margin:28px;color:#203348}table{border-collapse:collapse}th,td{padding:7px;border-bottom:1px solid #ddd;text-align:left}th{position:sticky;top:0;background:#edf3f8}.note{background:#fff2cc;padding:16px;max-width:1050px}</style>
<h1>All300 genes across19 sections: initial expression filter</h1>
<p class="note">Eligibility is NOT a final gene panel or GP/MCMC validation. Criteria apply together within one gene/type/section: >=30% nonzero SCT, q90>=1, nonconstant finite expression. A gene needs at least two distinct animal groups with a passing block, not two technical sections. Different types may qualify in different animals; per-type replication counts are shown. No WT requirement and no spatial-signal filter. Separate-section SCT preprocessing is unchanged; inputs are log1p corrected counts, not Pearson residuals.</p>
<p>Expression spread, SD and modal fraction are recorded in the detailed CSV. Modal fraction >=95% is review-only, not an additional exclusion. A gene absent from other types is not rejected for that absence. Paper-important failures and single-animal passes are held for review. The paper flag is inherited from the72-candidate list and is not exhaustive literature annotation.</p>
<p><a href="GENE_DECISIONS.csv">All300 decisions</a> | <a href="GENE_TYPE_SECTION_EXPRESSION.csv">Every input block</a> | <a href="GENE_TYPE_ANIMAL_EXPRESSION.csv">Animal-level evidence</a> | <a href="NEWLY_ELIGIBLE_BEYOND_72.txt">New eligible genes</a> | <a href="ELIGIBLE_GP_WORKLIST.csv">Reuse/new GP worklist</a></p>'''
    page+='<h2>Cumulative filtering counts</h2>'+pd.DataFrame(flow).to_html(index=False)
    page+='<h2>Decision counts</h2><pre>'+html.escape(json.dumps(q['counts'],indent=2))+'</pre>'
    page+=f'<p>{len(new)} eligible genes are outside the previous72. No fits have been launched.</p>'
    page+='<input placeholder="Filter gene / status" oninput="for(const r of document.querySelectorAll(\'#genes tbody tr\'))r.hidden=!r.textContent.toLowerCase().includes(this.value.toLowerCase())">'
    page+=public.to_html(index=False,escape=False,table_id='genes')
    (OUT/'index.html').write_text(page,encoding='utf-8')
    print(json.dumps({k:v for k,v in q.items() if k!='provenance'},indent=2),flush=True)
    print('NEW GENES:', ', '.join(sorted(new.gene)),flush=True)


if __name__=='__main__':
    assert not measure(np.ones(10))['passes_expression']
    assert not measure(np.r_[np.zeros(8),np.ones(2)*2])['passes_expression']
    assert measure(np.r_[np.zeros(7),np.ones(3)*2])['passes_expression']
    assert not measure([np.nan,2])['finite']
    main()
