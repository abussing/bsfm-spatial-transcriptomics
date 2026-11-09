"""Matched finite-feature control at fixed identity coordinates.

Legacy mode samples log-alpha/logit-zeta with fixed range. An explicit range
prior enables a three-coordinate target, adding log-ell_eta per factor.
The second diagnostic block is explicitly disabled (zero steps/energy).
"""
import json
import blackjax
import jax
import jax.numpy as jnp
import numpy as np
from scipy.linalg import solve_triangular
from blackjax.adaptation.window_adaptation import base, build_schedule
from .contracts import MU_LOG_ALPHA, VAR_LOG_ALPHA, array
from .field_target import DirectWTarget, FieldPosition
from .finite_features import make_feature_kernel
from .range_spec import validate_range_prior
from .layer5 import SplitTransition
from .split_kernels import Info, History, AdaptView, make_logdensity


class FlatTarget(DirectWTarget):
    @property
    def position_dimension(self):
        return 3 if self.learned_range else super().position_dimension

    @property
    def range_contract(self):
        if not self.learned_range:
            return super().range_contract
        return dict(mode='independent_per_factor_log_normal', **self.range_prior)

    def hyperparameters(self, position):
        if not self.learned_range:
            return super().hyperparameters(position)
        self._check_position(position)
        # Flat has no warp hyperparameters. Ones are explicit neutral transport
        # values in the common record, not inferred warp parameters.
        return dict(ell_eta=float(np.exp(position.values[2])), ell_W=1., sigma_W=1.)

    def range_position(self, factor_id, *, log_alpha, logit_zeta, log_ell_eta):
        if not self.learned_range:
            raise ValueError('Learned range position requires an explicit prior')
        values = np.asarray([log_alpha, logit_zeta, log_ell_eta], dtype=np.float64)
        result = FieldPosition(values, factor_id, self.identity)
        self._check_position(result)
        values.flags.writeable = False
        return result

    def __init__(self, inputs, geometry, rule, *, factor_ids, range_prior=None):
        self.learned_range = range_prior is not None
        self.range_prior = None if range_prior is None else validate_range_prior(range_prior)
        super().__init__(inputs, geometry, rule, factor_ids=factor_ids)
        identity = json.loads(self.identity)
        identity.update(schema='bsfm.identity-coordinate-factor-target.v1',
            model='flat', fixed_coordinate_center=inputs.arrays['slocs'].mean(axis=0).tolist(),
            sampled_coordinates=['log_alpha', 'logit_zeta'],
            acceptance_roundoff_policy='flat-only: map BlackJAX probability in (1,1+8*eps] to 1; reject all other invalid diagnostics',
            transport_only_coordinates=['log_ell_W', 'log_r_W', 'zW'])
        if self.learned_range:
            identity.update(schema='bsfm.stationary-learned-range-factor-target.v1',
                position_order=['log_alpha', 'logit_zeta', 'log_ell_eta'],
                sampled_coordinates=['log_alpha', 'logit_zeta', 'log_ell_eta'],
                transport_only_coordinates=[], factor_range=self.range_contract,
                flat_warp_summary='ell_W=sigma_W=1 are neutral transport values; no warp prior or transition',
                priors=dict(log_alpha_mean=MU_LOG_ALPHA, log_alpha_variance=VAR_LOG_ALPHA,
                            zeta_beta=[2., 2.], log_ell_eta_mean=float(np.log(self.range_prior['median'])),
                            log_ell_eta_variance=self.range_prior['log_sd']**2))
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
        live = self.learned_range
        if live:
            mu = float(np.log(self.range_prior['median']))
            variance = self.range_prior['log_sd']**2

        def value_grad(p, u, ct, penalty):
            log_ell = p[2] if live else jnp.log(.14)
            ll, _, _, a2, zeta, nv, sv, dn, ds, ge = parts(w, p[0], p[1], log_ell, u, ct)
            value = ll + dim*p[0]-.5*a2*penalty-.5*(p[0]-MU_LOG_ALPHA)**2/VAR_LOG_ALPHA
            value += 2*jax.nn.log_sigmoid(p[1])+2*jax.nn.log_sigmoid(-p[1])
            ga = 2*nv*dn+2*sv*ds+dim-a2*penalty-(p[0]-MU_LOG_ALPHA)/VAR_LOG_ALPHA
            gz = zeta*(1-zeta)*a2*(ds-dn)+2*(1-zeta)-2*zeta
            gradient = jnp.zeros_like(p).at[:2].set(jnp.array([ga, gz]))
            if live:
                # Prior density is in d log(ell); no second Jacobian is added.
                value -= .5*(log_ell-mu)**2/variance
                gradient = gradient.at[2].set(ge-(log_ell-mu)/variance)
            # Reject numerically unrepresentable proposals; do not clip parameters.
            # NUTS retains its divergent-trajectory diagnostic for these rejections.
            valid = jnp.isfinite(value) & jnp.all(jnp.isfinite(gradient)) & (zeta>0) & (zeta<1)
            if live:
                valid &= jnp.isfinite(jnp.exp(log_ell)) & (jnp.exp(log_ell)>0)
            return jnp.where(valid, value, -jnp.inf), jnp.where(valid, gradient, jnp.zeros_like(p))

        self._kernels.update(value_grad=value_grad,
            warp_features=lambda p: (w, wa, features(w, p[2])[4] if live else phi))

    def _validate_identities(self):
        super()._validate_identities()
        if hasattr(self, 'identity') and self.learned_range:
            expected = json.loads(self.identity)
            if 'factor_range' in expected and expected['factor_range'] != self.range_contract:
                raise ValueError('Flat range prior changed; rebuild the target explicitly')

    def _check_position(self, position):
        if self.learned_range:
            if (not isinstance(position, FieldPosition) or position.target_identity != self.identity
                    or position.factor_id not in self.factor_ids):
                raise ValueError('Learned-range flat position identity mismatch')
            array(position.values, 'flat position', (3,))
            with np.errstate(over='ignore', under='ignore'):
                alpha2, ell = np.exp(2*position.values[0]), np.exp(position.values[2])
            zeta = float(jax.nn.sigmoid(jnp.asarray(position.values[1])))
            if not np.isfinite([alpha2, ell]).all() or min(alpha2, ell)<=0 or not 0<zeta<1:
                raise ValueError('Nonrepresentable flat parameters; no clipping')
            return
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
        sampled = 3 if target.learned_range else 2
        kernel = blackjax.nuts.build_kernel()

        def one(key, p, u, ct, penalty, step, mass):
            full = lambda q: ld(q, u, ct, penalty)
            density = lambda v: full(p.at[:sampled].set(v))
            state = blackjax.nuts.init(p[:sampled], density)
            state, info = kernel(key, state, density, step, mass[:sampled], max_num_doublings=10)
            pn = p.at[:sampled].set(state.position)
            # BlackJAX's log-sum-exp average can exceed one by rounding. Enforce
            # probability support only in this narrow recorded roundoff interval.
            raw_ac = info.acceptance_rate
            ac = jnp.where((raw_ac>1)&(raw_ac<=1+8*np.finfo(np.float64).eps), 1., raw_ac)
            summary = Info(ac, info.is_divergent, info.num_integration_steps,
                info.energy, jnp.zeros(dimension).at[:sampled].set(info.momentum),
                jnp.array([ac, 0.]), jnp.array([info.is_divergent, False]),
                jnp.array([info.num_integration_steps, 0]), jnp.array([info.energy, 0.]), jnp.array(0.))
            return blackjax.nuts.init(pn, full), summary

        def transition(key, p, u, ct, penalty, tuning):
            return one(key, p, u, ct, penalty, tuning['step_size'], tuning['inverse_mass_matrix'])

        def adaptation(key, p, u, ct, penalty, steps):
            ai, au, af = base(True, .9)
            ads = ai(p[:sampled], .01)
            def step(carry, item):
                p, ads = carry
                key, stage = item
                mass = jnp.ones(dimension).at[:sampled].set(ads.inverse_mass_matrix)
                state, info = one(key, p, u, ct, penalty, ads.step_size, mass)
                new = au(ads, stage, state.position[:sampled], info.acceptance_rate)
                return (state.position, new), History(state, info,
                    AdaptView(new.step_size, jnp.ones(dimension).at[:sampled].set(new.inverse_mass_matrix)))
            (p, ads), history = jax.jit(lambda c, x: jax.lax.scan(step, c, x))(
                (p, ads), (jax.random.split(key, steps), build_schedule(steps)))
            step_size, mass = af(ads)
            return (blackjax.nuts.init(p, lambda q: ld(q, u, ct, penalty)),
                dict(step_size=step_size, hyper_step_size=1.,
                     inverse_mass_matrix=jnp.ones(dimension).at[:sampled].set(mass))), history

        self._runner = dict(transition=jax.jit(transition), adapt=adaptation)
