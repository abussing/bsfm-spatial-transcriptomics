"""Changed-coordinate measure, real Gibbs boundaries and interrupted restart."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import jax
import jax.numpy as jnp
import numpy as np
from test_meeting_extensions import setup as deep_setup
from test_flat_range import setup as flat_setup
from bsfm.sampler.checkpoint_contract import digest
from bsfm.sampler.layer4 import CenteredHyperTarget
from bsfm.sampler.reference_coordinates import build_reference_coordinates
from bsfm.sampler.run_initialization import initialize
from bsfm.sampler.run_periodic import PeriodicRunController
from bsfm.sampler.run_checkpoint_fork import CheckpointForkController, CheckpointRetuningController
from bsfm.sampler.run_genesis import load_genesis, boundary
from bsfm.sampler.run_readaptation import parent_endpoint
from bsfm.sampler.run_storage import file_record, read_json
from bsfm.sampler.transition_policy import validate_transition_policy

POLICIES = dict(flat=dict(name='flat_variances_v1'),
                deep=dict(name='deep_reference_warp_v1', reference_warp=[-.4, .2]))


class Interrupted(BaseException): pass


def make(base, root, policy, cls=PeriodicRunController, **binding_extra):
    binding = dict(base.store.input_receipt, **binding_extra)
    if policy is not None: binding['transition_policy'] = copy.deepcopy(policy)
    spec = copy.deepcopy(base.spec)
    spec.update(final_sweep=3, production_sweeps=3, save_every=2, checkpoint_every=2,
                input_sha256=digest(binding))
    return cls(root, base.target, base.loading, base.eta, spec, binding, authenticate=base.authenticate)


class ReferenceMeasureTests(unittest.TestCase):
    def test_full_canonical_measure_gradient_and_warp(self):
        with tempfile.TemporaryDirectory() as tmp:
            c = deep_setup(Path(tmp)/'fixture', 'deep'); t = c.target
            e, _ = initialize(t, c.loading, c.eta, seed=491)
            maps = CenteredHyperTarget(t)._kernels
            chart = build_reference_coordinates(t._kernels, maps, t.position_dimension, [-.4, .2])
            u, ct, penalty, _ = t.context(e.state, factor_id=t.factor_ids[0], state_factor_ids=t.factor_ids)
            for xb in ([0., 0.], [-.8, .3], [.5, -.2]):
                q = jnp.asarray(e.positions[0].values).at[2:4].set(jnp.asarray(xb))
                r = chart['to_reference'](q)
                np.testing.assert_allclose(chart['to_original'](r), q, atol=1e-11, rtol=1e-10)
                jac = jax.jacfwd(chart['to_original'])(r)
                np.testing.assert_allclose(jnp.linalg.slogdet(jac)[1], chart['log_jacobian'](r), atol=1e-10)
                def oracle(p):
                    return t._kernels['reference_value'](chart['to_original'](p), u, ct, penalty) + chart['log_jacobian'](p)
                v, g = chart['value_grad'](r, u, ct, penalty)
                ov, og = jax.value_and_grad(oracle)(r)
                np.testing.assert_allclose(v, ov, atol=1e-8, rtol=1e-10)
                np.testing.assert_allclose(g, og, atol=2e-7, rtol=2e-7)
                W = maps['physical'](q[2:4], q[4:].reshape(-1, 2))
                moved = r.at[2:4].set(jnp.array([.2, -.1]))
                qm = chart['to_original'](moved)
                np.testing.assert_allclose(maps['physical'](qm[2:4], qm[4:].reshape(-1, 2)), W, atol=2e-12)

    def test_policy_rejects_ambiguous_coordinates(self):
        for p, model in [(POLICIES['deep'], 'flat'), (POLICIES['flat'], 'deep'),
                         (dict(name='deep_reference_warp_v1', reference_warp=[True, 0]), 'deep'),
                         (dict(name='deep_reference_warp_v1', reference_warp=[float('nan'), 0]), 'deep')]:
            with self.assertRaises(ValueError): validate_transition_policy(p, model)


class CoordinateGibbsTests(unittest.TestCase):
    def test_launcher_selects_policy_and_reuses_completed_result(self):
        from bsfm.sampler.run import run_recipe, validate_recipe
        for model in ('flat', 'deep'):
            with self.subTest(model=model), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); base = deep_setup(root/'fixture', 'deep')
                data = root/'fixture.bin'; data.write_bytes(b'fixture')
                recipe = dict(schema='bsfm.sampler-run.v1', backend='cpu', model=model,
                    chain_id='chain', factor_ids=list(base.target.factor_ids), seed=491,
                    files=dict(fixture=dict(path=str(data), **file_record(data))),
                    dataset_recipe=None, gpu_runtime=None, transition_policy=POLICIES[model],
                    phases=[dict(run_id='test', warmup_steps=20, sweeps=1, save_every=1)])
                if model == 'flat': recipe['flat_range_prior'] = dict(median=.18, log_sd=.25, initial=.14)
                path = root/'run.json'; path.write_text(json.dumps(recipe))
                env = dict(lock=dict(sha256='a'*64), backend='cpu', test_only=True)
                with patch('bsfm.sampler.run.check_repository'), \
                     patch('bsfm.sampler.run_inputs.authenticate_environment', return_value=env), \
                     patch('bsfm.sampler.run_inputs.load_inputs', return_value=(
                         base.target, base.loading, base.eta, base.store.input_receipt)):
                    result = run_recipe(path, root/'out', commit='a'*40)
                    self.assertEqual(result['phases'][0]['result']['completed'], 1)
                    with patch('bsfm.sampler.run_controller.RunController._adapt_endpoint', side_effect=AssertionError('Retune')), \
                         patch('bsfm.sampler.layer6.GibbsSweep.sweep', side_effect=AssertionError('Replay')):
                        self.assertEqual(result, run_recipe(path, root/'out', commit='a'*40))
                invalid = dict(recipe, initial_endpoint=dict(path='x', bytes=1, sha256='a'*64))
                with self.assertRaises(ValueError): validate_recipe(invalid)

    def test_real_gibbs_fork_retuning_and_exact_restart(self):
        for model in ('flat', 'deep'):
            with self.subTest(model=model), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                base = flat_setup(root/'fixture') if model == 'flat' else deep_setup(root/'fixture', 'deep')
                # This parent deliberately uses the old chart.
                parent = make(base, root/'parent', None)
                if model == 'flat': parent.layer.split = base.layer.split
                parent.run(stop_after=1)
                s = parent.store.segment
                paths = dict(spec=parent.store.root/'run-spec.json', inputs=parent.store.root/'input-receipt.json',
                    genesis=s/'genesis/endpoint.npz', genesis_receipt=s/'genesis/receipt.json',
                    boundary_receipt=s/'boundaries/000000000001/receipt.json')
                source = {k: dict(path=str(p), **file_record(p)) for k, p in paths.items()}
                extra = dict(initial_checkpoint=source, checkpoint_retune=True)
                def child(name):
                    return make(base, root/name, POLICIES[model], CheckpointRetuningController, **extra)
                ref = child('reference'); ref.run()
                ep, _ = load_genesis(ref.store.segment/'genesis/endpoint.npz', ref.target, ref.cp)
                self.assertEqual(ep.evidence['adaptation_steps'], 20)
                self.assertEqual(ep.evidence['initialization']['parent']['completed_sweep'], 1)
                for row in ep.evidence['factors']:
                    self.assertEqual(row['endpoint_audit']['transition_policy'], POLICIES[model])
                for stage in ('before_genesis_publish', 'after_sweep', 'after_boundary_publish'):
                    c = child(stage)
                    def stop(where):
                        if where == stage: raise Interrupted()
                    with self.assertRaises(Interrupted): c.run(fault=stop)
                    c = child(stage)
                    with patch.object(c, '_adapt_endpoint', side_effect=AssertionError('Retuned on resume')):
                        c.run()
                    actual = parent_endpoint(c)[0]; expected = parent_endpoint(ref)[0]
                    self.assertEqual(boundary(actual, c.target), boundary(expected, c.target))
                    for n in (1, 2, 3):
                        p = f'boundaries/{n:012d}/receipt.json'
                        self.assertEqual(read_json(c.store.segment/p), read_json(ref.store.segment/p))
                    with patch.object(c.layer, 'sweep', side_effect=AssertionError('Replayed complete run')):
                        c.run()
                # A new policy cannot reinterpret inherited diagonal masses.
                bad = make(base, root/'bad', POLICIES[model], CheckpointForkController, initial_checkpoint=source)
                bad.spec['warmup_steps'] = 0
                with self.assertRaisesRegex(ValueError, 'coordinates require explicit'):
                    bad._adapt_endpoint(lambda _: None)
                changed = copy.deepcopy(POLICIES[model])
                if model == 'deep': changed['reference_warp'][0] += .1
                else: changed = None
                with self.assertRaises(ValueError):
                    make(base, root/'reference', changed, CheckpointRetuningController, **extra).run()


if __name__ == '__main__': unittest.main()
