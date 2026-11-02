import numpy as np
from scipy import sparse
from scipy.sparse.csgraph import connected_components
from .identities import require
from .support import distance, edge_distance, target


def triangles(vertices, tv):
    v=np.asarray(vertices); t=np.asarray(tv)
    require(v.ndim==2 and v.shape[1]==2 and np.isfinite(v).all(), 'Invalid vertices')
    require(t.ndim==2 and t.shape[1]==3 and t.dtype.kind in 'iu', 'Invalid triangles')
    require(t.size>0 and t.min()==0 and t.max()<len(v) and len(np.unique(t))==len(v), 'Ambiguous or nonzero-based indexing / unused vertex')
    require(len(np.unique(np.sort(t,axis=1),axis=0))==len(t), 'Duplicate triangle')
    e=v[t[:,1]]-v[t[:,0]]; f=v[t[:,2]]-v[t[:,0]]
    area=(e[:,0]*f[:,1]-e[:,1]*f[:,0])/2
    require(np.all(area>1e-16), 'Degenerate or reversed triangle')
    return area


def edges(tv):
    return np.unique(np.sort(np.vstack((tv[:,[0,1]],tv[:,[1,2]],tv[:,[2,0]])),axis=1),axis=0)


def canonicalize(v,t):
    order=np.lexsort((v[:,1],v[:,0])); inverse=np.empty(len(v),int);inverse[order]=np.arange(len(v))
    v=v[order];t=inverse[t]
    e=v[t[:,1]]-v[t[:,0]];f=v[t[:,2]]-v[t[:,0]]
    reverse=e[:,0]*f[:,1]-e[:,1]*f[:,0]<0
    t[reverse]=t[reverse][:,[0,2,1]]
    t=np.array([np.roll(row,-np.argmin(row)) for row in t])
    t=t[np.lexsort((t[:,2],t[:,1],t[:,0]))]
    triangles(v,t)
    return v,t


def diagnostics(v,t,support,collar,outer,h,cap,bins=8):
    area=triangles(v,t); e=edges(t);length=np.linalg.norm(v[e[:,1]]-v[e[:,0]],axis=1)
    d=edge_distance(v[e[:,0]],v[e[:,1]],collar); limits=target(d,h,cap)
    lengths=np.linalg.norm(v[t]-v[np.roll(t,-1,axis=1)],axis=2)
    angles=[]
    for i in range(3):
        x=lengths[:,i];y=lengths[:,(i+1)%3];z=lengths[:,(i+2)%3]
        angles.extend(np.degrees(np.arccos(np.clip((x*x+y*y-z*z)/(2*x*y),-1,1))))
    adjacency=sparse.coo_matrix((np.ones(2*len(e)),(np.r_[e[:,0],e[:,1]],np.r_[e[:,1],e[:,0]])),shape=(len(v),len(v))).tocsr()
    components=connected_components(adjacency,directed=False)[0]
    require(components==1,'Disconnected computational mesh')
    # Euler disk invariant + boundary degree ensures one topological boundary.
    raw=np.sort(np.vstack((t[:,[0,1]],t[:,[1,2]],t[:,[2,0]])),axis=1)
    unique,count=np.unique(raw,axis=0,return_counts=True)
    require(np.all(count<=2) and len(v)-len(e)+len(t)==1,'Non-disk or nonmanifold mesh')
    boundary_edges=unique[count==1];degree=np.bincount(boundary_edges.ravel(),minlength=len(v))
    require(np.all((degree==0)|(degree==2)),'Invalid boundary topology')
    regions=np.where(distance(v,support)<=1e-12,0,np.where(distance(v,collar)<=1e-12,1,2)).astype('int64')
    require(np.max(distance(v,outer))<1e-9,'Vertex outside enclosure')
    breaks=np.linspace(0,max(float(d.max()),1e-15),bins+1)
    rows=[]
    for i in range(bins):
        mask=(d>=breaks[i]) & ((d<breaks[i+1]) if i<bins-1 else d<=breaks[i+1])
        rows.append(dict(low=float(breaks[i]),high=float(breaks[i+1]),count=int(mask.sum()),
            minimum=float(length[mask].min()) if mask.any() else None,
            median=float(np.median(length[mask])) if mask.any() else None,
            maximum=float(length[mask].max()) if mask.any() else None,
            max_target_ratio=float(np.max(length[mask]/limits[mask])) if mask.any() else None))
    return regions,dict(vertices=len(v),triangles=len(t),components=int(components),area=float(area.sum()),
        min_area=float(area.min()),min_angle=float(np.min(angles)),
        max_edge_target_ratio=float(np.max(length/limits)),grading_bins=rows,
        region_mapping={'0':'convex_support','1':'fine_collar','2':'buffer'},boundary_vertices=np.flatnonzero(degree).tolist())
