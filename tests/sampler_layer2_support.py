"""Small deterministic FEM data and explicitly bounded historical AST reference."""
import ast
import csv
import hashlib
import json
import math
from pathlib import Path

import jax
import jax.numpy as jnp
import jax.scipy as jsp
import numpy as np
import scipy.linalg as sla
from scipy.io import mmread
from scipy.special import logsumexp as scipy_logsumexp

from bsfm.mesh.october26 import fem_matrices, polynomial_fem
from bsfm.mesh.projectors import active, project
from bsfm.sampler import warp, spectral

ROOT = Path(__file__).resolve().parents[1]


def synthetic(scale=1.):
    vertices = np.array([[0.,0.],[1.,0.],[1.,1.],[0.,1.],[.5,.5]])*scale
    triangles = np.array([[0,1,4],[1,2,4],[2,3,4],[3,0,4]],dtype=np.int64)
    # Vertex, edge and interior observations; at least one inactive vertex.
    locations = np.array([[0.,0.],[.5,0.],[.5,.2]])*scale
    projector = project(vertices, triangles, locations).toarray()
    mass, stiffness, _ = fem_matrices(vertices, triangles)
    terms = np.stack(polynomial_fem(mass, stiffness))
    return dict(terms=terms, vertices=vertices, projector=projector, locations=locations,
                active_indices=active(__import__('scipy').sparse.csr_matrix(projector)),
                vertex_ids=np.array([f'v-{i}' for i in range(len(vertices))]),
                cell_ids=np.array(['vertex','edge','interior']),source_rows=np.arange(3,dtype=np.int64))


def authenticated(data):
    identity = warp.mesh_identity(data, section='synthetic', mesh_sha256='a'*64)
    return warp.WarpGeometry.authenticate(data, identity)


def historical_reference(source_root):
    """No module import, no main, no target/generator execution; authenticated AST only."""
    with (ROOT/'docs/recovery/BSFM_SAMPLER_SOURCES.csv').open(encoding='utf-8') as f:
        records={Path(x['source_path']).name:x for x in csv.DictReader(f)}
    names={
        'spectral_live_range_whitening.py':['_relative_frobenius','_sha','build_spectral_fem_artifact','spectral_modal_geometry'],
        'active_marginal_whitening.py':['_positive_qr_root','active_geometry','physical_active','dense_active_covariance'],
        'splusu_active_tqff_target.py':['barycentric_triplets'],
        'generate_splusu_phase1.py':['dense_mm']}
    namespace=dict(np=np,jax=jax,jnp=jnp,jsp=jsp,sla=sla,scipy_logsumexp=scipy_logsumexp,
                   hashlib=hashlib,math=math,mmread=mmread,Path=Path)
    inventory=[]
    for filename,functions in names.items():
        path=Path(source_root)/filename; raw=path.read_bytes(); record=records[filename]
        assert len(raw)==int(record['bytes']) and hashlib.sha256(raw).hexdigest()==record['sha256']
        tree=ast.parse(raw.decode('utf-8-sig')); nodes=[]
        for node in tree.body:
            if isinstance(node,ast.FunctionDef) and node.name in functions:nodes.append(node)
            if filename=='generate_splusu_phase1.py' and isinstance(node,ast.Assign) and 28<=node.lineno<=35:nodes.append(node)
        assert {n.name for n in nodes if isinstance(n,ast.FunctionDef)}==set(functions)
        exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),namespace)
        inventory.append(dict(path=str(path),bytes=len(raw),sha256=record['sha256'],
                              lines=[[n.lineno,n.end_lineno] for n in nodes]))
    return namespace,inventory


def evaluate(functions, data, log_ell):
    spec=functions['build_spectral_fem_artifact'](data['terms'][0],data['terms'][1:],
        functions['BINOM'],functions['NORMCONST'],functions['NU_U'],functions['D_FEM'],data['projector'])
    idx=data['active_indices'];aa=data['projector'][:,idx];ua=spec['U'][idx]
    geo=functions['active_geometry'](log_ell,ua,spec)
    z=np.arange(len(idx)*2,dtype=np.float64).reshape(-1,2)/7.-.2
    field=functions['physical_active'](log_ell,z,.13,aa,ua,spec)
    trips=functions['barycentric_triplets'](aa)
    return dict(U=spec['U'],modal_diagonals=spec['modal_diagonals'],projected_modes=spec['projected_modes'],
                audit=spec['audit'],L=geo[0],L_r=geo[1],Sigma=geo[2],Sigma_r=geo[3],modal=geo[4],
                Wcell=field[0],Wcell_r=field[1],WA=field[2],triplets_indices=trips[0],
                triplets_weights=trips[1],triplets_audit=trips[2])


def port_functions():
    from bsfm.sampler import active, projector_encoding
    return dict(build_spectral_fem_artifact=spectral.build_spectral_fem_artifact,
                active_geometry=active.active_geometry,physical_active=active.physical_active,
                barycentric_triplets=projector_encoding.barycentric_triplets,
                BINOM=warp.BINOM,NORMCONST=warp.NORMCONST,NU_U=warp.NU_U,D_FEM=warp.D_FEM)


def serial(value):
    if isinstance(value,dict):return {k:serial(v) for k,v in value.items()}
    if isinstance(value,(tuple,list)):return [serial(v) for v in value]
    if isinstance(value,(np.ndarray,jax.Array,np.generic)):return np.asarray(value).tolist()
    return value


def relative(a,b):
    return float(np.linalg.norm(np.asarray(a)-np.asarray(b))/max(np.linalg.norm(b),np.finfo(float).tiny))
