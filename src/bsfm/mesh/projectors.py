import numpy as np
from scipy import sparse
from scipy.spatial import cKDTree
from .geometry import triangles
from .identities import require


def project(vertices,tv,points,tol=1e-10):
    """Exact candidate-triangle tests; no Delaunay retriangulation or nearest fallback."""
    triangles(vertices,tv);p=np.asarray(points); tri=vertices[tv]
    cent=tri.mean(axis=1); radii=np.linalg.norm(tri-cent[:,None,:],axis=2).max(axis=1)
    tree=cKDTree(cent); radius=float(radii.max())+tol
    inv=np.linalg.inv(np.stack((tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=2))
    rows=[];cols=[];values=[]
    for i,x in enumerate(p):
        candidates=sorted(tree.query_ball_point(x,radius))
        found=False
        for j in candidates:
            ab=inv[j]@(x-tri[j,0]);w=np.r_[1-ab.sum(),ab]
            if w.min()>=-tol and w.max()<=1+tol:
                w[np.abs(w)<1e-15]=0
                for k,value in zip(tv[j],w):
                    if value!=0:rows.append(i);cols.append(k);values.append(value)
                found=True;break
        require(found,f'Observation {i} outside mesh; nearest fallback forbidden')
    a=sparse.csr_matrix((values,(rows,cols)),shape=(len(p),len(vertices)));a.sort_indices()
    validate(a,vertices,p,tol)
    return a


def validate(a,v,points,tol=1e-10):
    a=a.tocsr();require(a.shape==(len(points),len(v)), 'Projector dimensions')
    counts=np.diff(a.indptr)
    require(np.all((counts>=1)&(counts<=3)),'Projector coverage/row sparsity')
    require(np.isfinite(a.data).all() and np.min(a.data)>=-tol,'Invalid barycentric weights')
    row=float(np.max(abs(np.asarray(a.sum(axis=1)).ravel()-1)))
    affine=float(np.max(abs(a@v-points)))
    require(row<=tol and affine<=tol*max(1,float(np.max(abs(v)))),'Projector affine identity')
    return dict(row_sum_error=row,affine_error=affine,min_weight=float(a.data.min()),max_nonzeros=int(counts.max()))


def active(a):
    b=a.copy();b.eliminate_zeros();return np.unique(b.indices).astype('int64')
