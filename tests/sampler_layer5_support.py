"""Bounded authenticated references and deterministic split-kernel fixtures."""
import ast
from collections import namedtuple
import hashlib
import json
from pathlib import Path

import blackjax
from blackjax.adaptation.window_adaptation import base, build_schedule
import jax
import jax.numpy as jnp
import numpy as np

from bsfm.sampler import split_kernels
from bsfm.sampler.layer5 import SplitTransition
from bsfm.sampler.contracts import logical_hash
from sampler_layer4_support import system, positions
from sampler_provenance import selected_source_record

ROOT = Path(__file__).resolve().parents[1]


def historical(source_root):
    namespace = dict(np=np, jax=jax, jnp=jnp, blackjax=blackjax,
                     namedtuple=namedtuple, base=base, build_schedule=build_schedule)
    sources = []
    for name, functions in [('full_split.py', ['build_split']),
                             ('run_c3full_fixed_profile_nuts.py', ['make_logdensity'])]:
        path = Path(source_root)/name
        data = path.read_bytes(); record = selected_source_record(name)
        if len(data) != int(record['bytes']) or hashlib.sha256(data).hexdigest() != record['sha256']:
            raise ValueError('Selected source identity mismatch')
        tree = ast.parse(data)
        nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in functions]
        if name == 'full_split.py':
            nodes = [n for n in tree.body if isinstance(n, ast.Assign)]+nodes
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), namespace)
        sources.append(dict(path=str(path), bytes=len(data), sha256=record['sha256']))
    return namespace, sources


def gaussian_system(factory=split_kernels.build_split):
    # Nontrivial coordinate partition and physical chart; no BSFM fit.
    p = jnp.array([.2, -.3, -.2, .1, .4, -.1, .3, .15], dtype=jnp.float64)
    scales = jnp.array([.5, 1.3, .7, 1.4, .8, 1.1, 1.2, .6])
    ld = lambda q, u, ct, penalty: -.5*jnp.sum((q/scales)**2) + ct*jnp.sum(q[:2])
    maps = dict(physical=lambda xb, z: jnp.exp(xb.sum())*z,
                whiten=lambda xb, w: jnp.exp(-xb.sum())*w,
                logdensity=lambda xb, w: -4*xb.sum()-.5*jnp.sum(w*w)*jnp.exp(-2*xb.sum())-.5*jnp.sum(xb*xb))
    args = (p, jnp.array(0.), jnp.array(.07), jnp.array(0.))
    return factory(ld, maps, 8), args, maps, ld


def tree_record(tree):
    """Each leaf retains dtype, dimensions and exact logical payload hash."""
    return [dict(dtype=str(np.asarray(x).dtype), shape=list(np.shape(x)),
                 sha256=logical_hash(np.asarray(x))) for x in jax.tree.leaves(tree)]


def canonical_system(seed=12):
    target, state, p = system(seed)
    p = positions(target, state, p)[0]
    return target, state, p, SplitTransition(target)


def evaluate(reference=None):
    factory = split_kernels.build_split if reference is None else reference['build_split']
    bridge = split_kernels.make_logdensity if reference is None else reference['make_logdensity']
    runner, args, _, _ = gaussian_system(factory)
    key = jax.random.PRNGKey(173)
    (state, tuned), history = runner['adapt'](key, *args, 100)
    after, info = runner['transition'](jax.random.PRNGKey(174), state.position, *args[1:], tuned)
    result = dict(gaussian_adapt=tree_record(((state, tuned), history)),
                  gaussian_after=tree_record((after, info)),
                  step_size=float(tuned['step_size']), hyper_step_size=float(tuned['hyper_step_size']),
                  inverse_mass_matrix=np.asarray(tuned['inverse_mass_matrix']).tolist(),
                  warmup_endpoint=np.asarray(state.position).tolist(),
                  warmup_max_W_error=float(np.max(history.info.hyper_W_relative_error)),
                  warmup_divergences=np.asarray(history.info.block_divergent).sum(axis=0).tolist(),
                  key_data=np.asarray(key).tolist(),
                  field_hyper_keys=np.asarray(jax.random.split(key)).tolist())
    target, gs, p, public = canonical_system()
    core = factory(bridge(target._kernels), public.centered._kernels, len(p.values))
    context = target.context(gs, factor_id=p.factor_id, state_factor_ids=target.factor_ids)
    tuned = dict(step_size=.01, hyper_step_size=.01, inverse_mass_matrix=jnp.ones(len(p.values)))
    final, diag = core['transition'](jax.random.PRNGKey(182), jnp.asarray(p.values),
                                   *map(jnp.asarray, context[:3]), tuned)
    result.update(canonical_transition=tree_record((final, diag)),
                  canonical_position=np.asarray(final.position).tolist(),
                  canonical_block_leapfrogs=np.asarray(diag.block_leapfrogs).tolist(),
                  canonical_W_error=float(diag.hyper_W_relative_error))
    return result
