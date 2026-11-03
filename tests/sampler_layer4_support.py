"""Bounded source authentication and independent small-system Layer-4 references."""
import ast
import copy
from dataclasses import asdict, dataclass
from functools import partial
import hashlib
import json
from pathlib import Path

import jax
import jax.numpy as jnp
import jax.scipy.linalg as jsla
import numpy as np
from scipy.linalg import block_diag
from scipy.special import logit
from bsfm.sampler import centered_hyper_kernels as ch, joint_eta_kernels as je
from bsfm.sampler.contracts import logical_hash
from bsfm.sampler.spectral import spectral_modal_geometry
from bsfm.sampler.layer4 import CenteredHyperTarget, JointEtaConditional
from sampler_layer3_support import system
from sampler_provenance import selected_source_record

ROOT = Path(__file__).resolve().parents[1]
FUNCTIONS = {
    'centered_hyper_target_qr.py': ('centered_hyper_kernels.py',
        ['positive_qr_factor', 'qr_contractions', 'spectral_qr_geometry', 'build_centered_hyper_target']),
    'joint_eta_pcg.py': ('joint_eta_kernels.py',
        ['JointEtaDiagnostics', '_joint_cell_statistics', '_block_preconditioner_cholesky',
         '_precision_matvec', '_preconditioner_solve', '_pcg', '_precision_noise', 'sample_joint_eta_pcg'])}


def historical(source_root):
    namespace = dict(np=np, jax=jax, jnp=jnp, jla=jsla, jsla=jsla,
                     dataclass=dataclass, partial=partial, spectral_modal_geometry=spectral_modal_geometry,
                     __name__=__name__)
    inventory = []
    # Authenticate both complete files before evaluating any reference node.
    sources = []
    for name, (_, names) in FUNCTIONS.items():
        p = Path(source_root)/name; b = p.read_bytes(); r = selected_source_record(name)
        if len(b) != int(r['bytes']) or hashlib.sha256(b).hexdigest() != r['sha256']:
            raise ValueError('Selected historical source identity mismatch')
        sources.append((p, b, r, names))
    for p, b, r, names in sources:
        nodes = [copy.deepcopy(n) for n in ast.parse(b.decode()).body
                 if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in names]
        assert len(nodes) == len(names)
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(p), 'exec'), namespace)
        inventory.append(dict(path=str(p), bytes=len(b), sha256=r['sha256'],
                              functions={n.name: [n.lineno, n.end_lineno] for n in nodes}))
    return namespace, inventory


def positions(target, state, pos):
    return tuple(target.position(fid, log_alpha=np.log(state.alpha[k]),
                 logit_zeta=logit(state.zeta[k]), log_ell=pos.values[2]+.1*k,
                 log_r=pos.values[3]-.05*k, zW=pos.values[4:].reshape(-1, 2)*(k+1))
                 for k, fid in enumerate(target.factor_ids))


def small_joint(seed=91):
    rng = np.random.default_rng(seed); k, n, g, c, r = 2, 5, 3, 3, 4
    return dict(y=rng.normal(0, .3, (g, n)), loading=rng.normal(0, .4, (c, g, k)),
                alpha=np.array([.7, .9]), sigma2=np.array([.4, .8, .6]),
                cell_id=np.array([0, 0, 1, 2, 2]), zeta=np.array([.35, .65]),
                features=rng.normal(0, .5, (k, n, r)))


def evaluate(seed=12, reference=None):
    t, s, p = system(seed); ps = positions(t, s, p); g = t.geometry
    factory = ch.build_centered_hyper_target if reference is None else reference['build_centered_hyper_target']
    kernels = factory(g.spectral['U'][g.arrays['active_indices']], g.spectral)
    xb = jnp.asarray(p.values[2:4]); z = jnp.asarray(p.values[4:].reshape(-1, 2))
    w = kernels['physical'](xb, z); val, grad = kernels['value_grad'](xb, w)
    change = xb+jnp.array([.07, -.04]); whitened = kernels['whiten'](change, w)
    ad = jax.grad(kernels['reference_value'])(xb, w)
    out = dict(value=float(val), gradient=np.asarray(grad).tolist(),
               AD_gradient=np.asarray(ad).tolist(), W_active=np.asarray(w).tolist(),
               rewhitened=np.asarray(whitened).tolist())
    draw = je.sample_joint_eta_pcg if reference is None else reference['sample_joint_eta_pcg']
    cases = [('small', small_joint(seed+79)), ('canonical', dict(y=t.inputs.arrays['Y'],
        loading=s.loading, alpha=s.alpha, sigma2=s.sigma2, cell_id=t.inputs.arrays['cell_id'],
        zeta=s.zeta, features=np.stack([t.features(p)[2] for p in ps])))]
    for name, kw in cases:
        rng = np.random.default_rng(901); before = copy.deepcopy(rng.bit_generator.state)
        eta, beta, diag = draw(rng, **kw)
        out[name] = dict(eta=eta.tolist(), beta_sha256=logical_hash(beta),
                         diagnostics=asdict(diag), rng_before=before,
                         rng_after=copy.deepcopy(rng.bit_generator.state))
        if name == 'small': out[name]['beta'] = beta.tolist()
    return out


def dense_fixed_w(geometry, xb, w):
    """Independent full FEM precision inverse, active submatrix, Gaussian density."""
    terms = jnp.asarray(geometry.arrays['terms']); idx = geometry.arrays['active_indices']
    kap = jnp.sqrt(40.)/jnp.exp(xb[0])
    coeff = jnp.array([1., 6., 15., 20., 15., 6., 1.])/(20*jnp.pi)*kap**(2-2*jnp.arange(7))
    full = jnp.linalg.inv(jnp.sum(coeff[:, None, None]*terms, axis=0))
    cov = jnp.exp(2*(xb[0]+xb[1]))/10 * full[np.ix_(idx, idx)]
    return (-jnp.linalg.slogdet(cov)[1]-.5*jnp.sum(w*jnp.linalg.solve(cov, w))
            -.5*(xb[0]/.5)**2-.5*(xb[1]/.3)**2)


def dense_eta(kw):
    """Direct eta-space Gaussian conditioning via observation covariance."""
    features=kw['features']; k,n,_=features.shape; g=kw['y'].shape[0]
    prior=block_diag(*[kw['alpha'][j]**2*(kw['zeta'][j]*(features[j]@features[j].T)
                     +(1-kw['zeta'][j])*np.eye(n)) for j in range(k)])
    design=np.zeros((g*n,k*n))
    for i in range(n):
        for j in range(k):design[i*g:(i+1)*g,j*n+i]=kw['loading'][kw['cell_id'][i],:,j]
    noise=np.diag(np.tile(kw['sigma2'],n)); v=design@prior@design.T+noise
    gain=np.linalg.solve(v,design@prior).T
    mean=gain@kw['y'].T.reshape(-1)
    covariance=prior-gain@design@prior
    return mean.reshape(k,n),covariance


def dense_perturbation(kw, seed=901, innovations=None):
    """Assemble a small dense beta system and global conditional nugget map.

    Exact same innovations/root convention as the source, but dense solves and
    block matrices instead of PCG/einsum precision/preconditioner. The H entries
    used for the innovation eigensystem retain source rounding; independently
    computed observation-space H and s are returned for comparison.
    """
    phi=kw['features']; k,n,r=phi.shape; a=kw['alpha']; z=kw['zeta']
    loading=kw['loading']*a[None,None,:]; dv=1-z; d=np.sqrt(dv)
    u,h,s,_=je._joint_cell_statistics(kw['y'],loading,kw['sigma2'],kw['cell_id'],d**2)
    hd=[];sd=[];pblocks=[];gblocks=[]
    for i,c in enumerate(kw['cell_id']):
        lam=loading[c];v=np.diag(kw['sigma2'])+lam@np.diag(dv)@lam.T
        hd.append(lam.T@np.linalg.solve(v,lam));sd.append(lam.T@np.linalg.solve(v,kw['y'][:,i]))
        p=np.eye(k)+np.diag(d)@u[i]@np.diag(d)
        pblocks.append(p);gblocks.append(np.linalg.inv(np.linalg.cholesky(p).T))
    # F maps factor-major beta to cell-major smooth values.
    f=np.zeros((n*k,k*r))
    for i in range(n):
        for j in range(k):f[i*k+j,j*r:(j+1)*r]=np.sqrt(z[j])*phi[j,i]
    hb=block_diag(*h); ub=block_diag(*u); db=block_diag(*[np.diag(d)]*n)
    q=np.eye(k*r)+f.T@hb@f
    rng=np.random.default_rng(seed)
    if innovations is None:
        prior=rng.standard_normal((k,r));white=rng.standard_normal((n,k));xi=rng.standard_normal((n,k))
    else:prior,white,xi=innovations
    eig,vec=np.linalg.eigh(h)
    cell=np.concatenate([vec[i]@(np.sqrt(np.maximum(eig[i],0))*white[i]) for i in range(n)])
    rhs=f.T@s.reshape(-1)+prior.reshape(-1)+f.T@cell
    beta=np.linalg.solve(q,rhs);smooth=f@beta
    rawrhs=np.concatenate([loading[c].T@(kw['y'][:,i]/kw['sigma2']) for i,c in enumerate(kw['cell_id'])])
    pb=block_diag(*pblocks);gb=block_diag(*gblocks)
    eta=smooth+db@np.linalg.solve(pb,db@(rawrhs-ub@smooth))+db@gb@xi.reshape(-1)
    beta_map=(np.eye(n*k)-db@np.linalg.solve(pb,db@ub))@f
    beta_map=(np.tile(a,n)[:,None]*beta_map).reshape(n,k,k*r).transpose(1,0,2).reshape(k*n,k*r)
    return (a[:,None]*eta.reshape(n,k).T, beta.reshape(k,r),
            dict(q=q,rhs=rhs,h_dense=np.array(hd),s_dense=np.array(sd),h=h,s=s,
                 eta_beta_map=beta_map,rng_after=copy.deepcopy(rng.bit_generator.state)))
