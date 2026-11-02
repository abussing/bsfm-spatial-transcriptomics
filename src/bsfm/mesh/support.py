"""Convex empirical enclosure; no anatomical or disconnected-domain inference."""
import numpy as np
from scipy.spatial import ConvexHull, HalfspaceIntersection
from .identities import require


def hull(points):
    points = np.unique(np.asarray(points, dtype=float), axis=0)
    require(len(points) >= 3 and np.linalg.matrix_rank(points-points[0]) == 2, 'Degenerate support')
    poly = points[ConvexHull(points).vertices]
    return canonical_polygon(poly)


def canonical_polygon(poly):
    p = np.asarray(poly, dtype=float)
    area = np.sum(p[:,0]*np.roll(p[:,1],-1)-p[:,1]*np.roll(p[:,0],-1))/2
    if area < 0: p = p[::-1]
    return np.roll(p, -int(np.lexsort((p[:,1],p[:,0]))[0]), axis=0).copy()


def offset(poly, radius, directions=128):
    """Circumscribed rounded convex offset via exact support-function halfplanes."""
    require(radius > 0, 'Offset radius must be positive')
    edges = np.roll(poly,-1,axis=0)-poly
    normals = np.column_stack((edges[:,1],-edges[:,0]))
    normals /= np.linalg.norm(normals,axis=1)[:,None]
    angles = np.arange(directions)*2*np.pi/directions
    normals = np.vstack((normals,np.column_stack((np.cos(angles),np.sin(angles)))))
    angles = np.mod(np.arctan2(normals[:,1],normals[:,0]),2*np.pi)
    order = np.argsort(angles,kind='stable'); normals=normals[order]; angles=angles[order]
    keep = np.r_[True,np.diff(angles)>1e-12]; normals=normals[keep]
    limits = np.max(normals@poly.T,axis=1)+radius
    vertices = HalfspaceIntersection(np.column_stack((normals,-limits)),poly.mean(axis=0)).intersections
    return hull(vertices)


def distance(points, poly, *, boundary=False):
    """Euclidean segment distance; zero inside unless boundary=True."""
    p = np.asarray(points); best = np.full(len(p),np.inf); inside=np.ones(len(p),bool)
    for a,b in zip(poly,np.roll(poly,-1,axis=0)):
        e=b-a; delta=p-a
        inside &= e[0]*delta[:,1]-e[1]*delta[:,0] >= -1e-12
        t=np.clip(delta@e/(e@e),0,1)
        best=np.minimum(best,np.linalg.norm(delta-t[:,None]*e,axis=1))
    if not boundary: best[inside]=0
    return best


def edge_distance(a,b,poly):
    """Exact planar segment-to-convex-polygon distance, including crossing edges."""
    e=b-a; ee=np.sum(e*e,axis=1)
    best=np.minimum(distance(a,poly),distance(b,poly))
    for p,q in zip(poly,np.roll(poly,-1,axis=0)):
        t=np.clip(np.sum((p-a)*e,axis=1)/ee,0,1)
        best=np.minimum(best,np.linalg.norm(p-a-t[:,None]*e,axis=1))
        f=q-p; den=e[:,0]*f[1]-e[:,1]*f[0]
        good=np.abs(den)>1e-15
        u=np.zeros(len(a));v=u.copy();delta=p-a
        u[good]=(delta[good,0]*f[1]-delta[good,1]*f[0])/den[good]
        v[good]=(delta[good,0]*e[good,1]-delta[good,1]*e[good,0])/den[good]
        best[good & (u>=0)&(u<=1)&(v>=0)&(v<=1)]=0
    return best


def enclosure(points, collar, buffer, directions=128):
    support=hull(points)
    return support, offset(support,collar,directions), offset(support,collar+buffer,directions)


def target(d,h,cap):
    return np.minimum(h+0.15*np.asarray(d),cap)
