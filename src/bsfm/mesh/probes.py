"""Geometry-only fixed probe identities, computed before any candidate errors."""
import numpy as np
from scipy.spatial import cKDTree,Delaunay
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import minimum_spanning_tree
from .support import distance,hull
from .identities import require,ordered_ids


def choose(points,source_rows,support,config):
    points=np.asarray(points);rows=np.asarray(source_rows);n=len(points);count=config['count_per_stratum']
    require(n>=4*count and len(np.unique(rows))==n,'Insufficient or ambiguous identities for fixed probes')
    tree=cKDTree(points);radii=tree.query(points,k=config['density_neighbors']+1,workers=1)[0][:,-1]
    boundary=distance(points,support,boundary=True)
    scores={'boundary':boundary,'interior':-boundary,'dense':radii,'sparse':-radii}
    selected=[];labels=[];fills={};nearest=np.full(n,np.inf)
    pool_size=max(count,int(np.ceil(config['quantile_pool']*n)))
    for label in config['precedence']:
        ranking=np.lexsort((rows,scores[label]));pool=set(ranking[:pool_size])-set(selected);fill=0
        for _ in range(count):
            if not pool:
                pool=set(range(n))-set(selected);fill+=1
            candidates=np.array(sorted(pool,key=lambda i:int(rows[i])))
            j=int(candidates[np.argmax(nearest[candidates])])
            selected.append(j);labels.append(label);pool.remove(j)
            nearest=np.minimum(nearest,np.linalg.norm(points-points[j],axis=1));nearest[selected]=-np.inf
        fills[label]=fill
    idx=np.asarray(selected,dtype='int64')
    return idx,dict(indices=idx.tolist(),source_rows=rows[idx].tolist(),strata=labels,
        fills=fills,identities_sha256=ordered_ids(rows[idx]),density_radius20=radii[idx].tolist(),
        boundary_distance=boundary[idx].tolist(),ordering='stratum precedence then farthest-point selection',
        gap=gap_diagnostics(points,rows,radii))


def gap_diagnostics(points,rows,radii):
    """Diagnostic Euclidean MST edges only; Delaunay here NEVER builds the FEM mesh."""
    p,first=np.unique(points,axis=0,return_index=True)
    if np.linalg.matrix_rank(p-p[0])<2:
        order=np.argsort(p[:,np.argmax(np.ptp(p,axis=0))],kind='stable');e=np.column_stack((order[:-1],order[1:]))
    else:
        t=Delaunay(p).simplices
        e=np.unique(np.sort(np.vstack((t[:,[0,1]],t[:,[1,2]],t[:,[2,0]])),axis=1),axis=0)
    length=np.linalg.norm(p[e[:,0]]-p[e[:,1]],axis=1)
    graph=coo_matrix((np.r_[length,length],(np.r_[e[:,0],e[:,1]],np.r_[e[:,1],e[:,0]])),shape=(len(p),len(p))).tocsr()
    mst=minimum_spanning_tree(graph).tocoo();scale=float(np.median(radii))
    keep=mst.data>5*scale
    endpoints=np.column_stack((first[mst.row[keep]],first[mst.col[keep]]))
    return dict(criterion='MST edges surviving radius cutoffs 3,4,5 times median 20-NN radius',
        anatomical_claim=False,median_radius20=scale,extra_probe_indices=np.unique(endpoints).tolist(),
        edge_source_rows=rows[endpoints].tolist(),edge_lengths=mst.data[keep].tolist(),fixed_256_unchanged=True)
