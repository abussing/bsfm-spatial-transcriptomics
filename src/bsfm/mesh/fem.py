import numpy as np
from scipy import sparse
from .geometry import triangles
from .identities import require


def assemble(vertices,tv):
    areas=triangles(vertices,tv); n=len(vertices); rows=[]; cols=[]; mass=[]; stiffness=[]
    for ids,area in zip(tv,areas):
        p=vertices[ids]
        grad=np.column_stack((p[[1,2,0],1]-p[[2,0,1],1],p[[2,0,1],0]-p[[1,2,0],0]))/(2*area)
        m=area*(np.ones((3,3))+np.eye(3))/12; g=area*grad@grad.T
        rows.extend(np.repeat(ids,3));cols.extend(np.tile(ids,3));mass.extend(m.ravel());stiffness.extend(g.ravel())
    def matrix(data):
        a=sparse.coo_matrix((data,(rows,cols)),shape=(n,n)).tocsr();a.sum_duplicates();a.sort_indices();return a
    return matrix(mass),matrix(stiffness)


def validate(v,t,m,g,tol=1e-10):
    area=triangles(v,t).sum(); ones=np.ones(len(v))
    def max_sparse(a):return float(np.max(abs(a.data))) if a.nnz else 0.
    err=dict(mass_area=abs(float(ones@m@ones)-area),constant_stiffness=float(np.max(abs(g@ones))),
        mass_symmetry=max_sparse(m-m.T),stiffness_symmetry=max_sparse(g-g.T))
    require(max(err.values())<tol*max(1,float(area)), 'FEM identity failed')
    return err
