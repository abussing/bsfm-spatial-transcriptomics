"""Matched finite-feature control at fixed identity coordinates.

Only log-alpha/logit-zeta have NUTS transitions. The unused warp coordinates
remain fixed transport fields for the common checkpoint format, not samples.
The second diagnostic block is explicitly disabled (zero steps/energy).
"""
import json
import blackjax
import jax
import jax.numpy as jnp
import numpy as np
from scipy.linalg import solve_triangular
from blackjax.adaptation.window_adaptation import base, build_schedule
from .contracts import MU_LOG_ALPHA, VAR_LOG_ALPHA
from .field_target import DirectWTarget
from .finite_features import make_feature_kernel
from .layer5 import SplitTransition
from .split_kernels import Info, History, AdaptView, make_logdensity


class FlatTarget(DirectWTarget):
    def __init__(self, inputs, geometry, rule, *, factor_ids):
        super().__init__(inputs, geometry, rule, factor_ids=factor_ids)
        identity = json.loads(self.identity)
        identity.update(schema='bsfm.identity-coordinate-factor-target.v1',
            model='flat', fixed_coordinate_center=inputs.arrays['slocs'].mean(axis=0).tolist(),
            sampled_coordinates=['log_alpha', 'logit_zeta'],
            acceptance_roundoff_policy='flat-only: map BlackJAX probability in (1,1+8*eps] to 1; reject all other invalid diagnostics',
            transport_only_coordinates=['log_ell_W', 'log_r_W', 'zW'])
        self.identity = json.dumps(identity, sort_keys=True)
        center = inputs.arrays['slocs'].mean(axis=0)
        w = jnp.asarray(inputs.arrays['slocs']-center)
        wa = jnp.asarray(geometry.arrays['vertices'][geometry.arrays['active_indices']]-center)
        z = solve_triangular(np.asarray(geometry.geometry(0.)[0]), np.asarray(wa)/.31622776601683794, lower=True)
        self.fixed_tail = np.r_[0., 0., z.ravel()]
        self.fixed_tail.flags.writeable = False
        features, parts, reference = make_feature_kernel(rule.arrays['omega'], rule.arrays['sqrt_weights'])
        dim = len(inputs.arrays['gene_names'])*len(inputs.arrays['cell_type_names'])
        phi = features(w, jnp.log(.14))[4]

        def value_grad(p, u, ct, penalty):
            ll, _, _, a2, zeta, nv, sv, dn, ds, _ = parts(w, p[0], p[1], jnp.log(.14), u, ct)
            value = ll + dim*p[0]-.5*a2*penalty-.5*(p[0]-MU_LOG_ALPHA)**2/VAR_LOG_ALPHA
            value += 2*jax.nn.log_sigmoid(p[1])+2*jax.nn.log_sigmoid(-p[1])
            ga = 2*nv*dn+2*sv*ds+dim-a2*penalty-(p[0]-MU_LOG_ALPHA)/VAR_LOG_ALPHA
            gz = zeta*(1-zeta)*a2*(ds-dn)+2*(1-zeta)-2*zeta
            gradient = jnp.zeros_like(p).at[:2].set(jnp.array([ga, gz]))
            # Reject numerically unrepresentable proposals; do not clip parameters.
            # NUTS retains its divergent-trajectory diagnostic for these rejections.
            valid = jnp.isfinite(value) & jnp.all(jnp.isfinite(gradient)) & (zeta>0) & (zeta<1)
            return jnp.where(valid, value, -jnp.inf), jnp.where(valid, gradient, jnp.zeros_like(p))

        self._kernels.update(value_grad=value_grad, warp_features=lambda p: (w, wa, phi))

    def _check_position(self, position):
        super()._check_position(position)
        if hasattr(self, 'fixed_tail') and not np.array_equal(position.values[2:], self.fixed_tail):
            raise ValueError('Flat control warp coordinates must remain fixed')


class FlatTransition(SplitTransition):
    def _validate_info(self, info):
        try:
            return super()._validate_info(info)
        except RuntimeError as exc:
            raise RuntimeError(str(exc)+'; flat acceptance='+repr(np.asarray(info.block_acceptance))) from exc

    def __init__(self, target):
        if not isinstance(target, FlatTarget):
            raise ValueError('Flat transition requires an explicit flat target')
        super().__init__(target)
        ld = make_logdensity(target._kernels)
        dimension = self.dimension
        kernel = blackjax.nuts.build_kernel()

        def one(key, p, u, ct, penalty, step, mass):
            full = lambda q: ld(q, u, ct, penalty)
            density = lambda v: full(p.at[:2].set(v))
            state = blackjax.nuts.init(p[:2], density)
            state, info = kernel(key, state, density, step, mass[:2], max_num_doublings=10)
            pn = p.at[:2].set(state.position)
            # BlackJAX's log-sum-exp average can exceed one by rounding. Enforce
            # probability support only in this narrow recorded roundoff interval.
            raw_ac = info.acceptance_rate
            ac = jnp.where((raw_ac>1)&(raw_ac<=1+8*np.finfo(np.float64).eps), 1., raw_ac)
            summary = Info(ac, info.is_divergent, info.num_integration_steps,
                info.energy, jnp.zeros(dimension).at[:2].set(info.momentum),
                jnp.array([ac, 0.]), jnp.array([info.is_divergent, False]),
                jnp.array([info.num_integration_steps, 0]), jnp.array([info.energy, 0.]), jnp.array(0.))
            return blackjax.nuts.init(pn, full), summary

        def transition(key, p, u, ct, penalty, tuning):
            return one(key, p, u, ct, penalty, tuning['step_size'], tuning['inverse_mass_matrix'])

        def adaptation(key, p, u, ct, penalty, steps):
            ai, au, af = base(True, .9)
            ads = ai(p[:2], .01)
            def step(carry, item):
                p, ads = carry
                key, stage = item
                mass = jnp.ones(dimension).at[:2].set(ads.inverse_mass_matrix)
                state, info = one(key, p, u, ct, penalty, ads.step_size, mass)
                new = au(ads, stage, state.position[:2], info.acceptance_rate)
                return (state.position, new), History(state, info,
                    AdaptView(new.step_size, jnp.ones(dimension).at[:2].set(new.inverse_mass_matrix)))
            (p, ads), history = jax.jit(lambda c, x: jax.lax.scan(step, c, x))(
                (p, ads), (jax.random.split(key, steps), build_schedule(steps)))
            step_size, mass = af(ads)
            return (blackjax.nuts.init(p, lambda q: ld(q, u, ct, penalty)),
                dict(step_size=step_size, hyper_step_size=1.,
                     inverse_mass_matrix=jnp.ones(dimension).at[:2].set(mass))), history

        self._runner = dict(transition=jax.jit(transition), adapt=adaptation)
