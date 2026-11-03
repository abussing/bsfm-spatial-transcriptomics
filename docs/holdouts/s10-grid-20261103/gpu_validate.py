"""GPU execution evidence only; never publish these warmup endpoints as draws."""
import importlib.metadata as metadata
import json
from pathlib import Path
import subprocess
import sys
import time
import unittest

import jax
import numpy as np

from experiment import clean, target_and_seeds
from bsfm.sampler.run_initialization import initialize
from bsfm.sampler.layer5 import SplitTransition

out = Path(sys.argv[1])
clean(sys.argv[2])
report = dict(commit=sys.argv[2], packages={d.metadata['Name']: d.version for d in metadata.distributions()},
              python=sys.version, executable=sys.executable, devices=[str(d) for d in jax.devices()],
              backend=jax.default_backend(), x64=jax.config.x64_enabled)
(out/'environment.json').write_text(json.dumps(report, indent=2)+'\n')
assert report['backend']=='gpu' and report['x64'], report
for name, version in [('jax','0.7.0'),('jaxlib','0.7.0'),('blackjax','1.3'),('numpy','2.1.3'),
                      ('jax-cuda12-plugin','0.7.0'),('jax-cuda12-pjrt','0.7.0')]:
    assert metadata.version(name)==version, (name, metadata.version(name))
print('GPU DEVICE VERIFIED', report['devices'], flush=True)
suite = unittest.defaultTestLoader.loadTestsFromName('test_meeting_extensions')
result = unittest.TextTestRunner(verbosity=2).run(suite)
assert result.wasSuccessful(), 'Focused GPU tests failed'
print('GPU FOCUSED TESTS PASSED', flush=True)
prepared=Path('/work/abussing/bsfm-consolidation/evidence/holey-27f9b3f0dfa4c1df2acc9e845633a8031069daea/circles12_diameter1of8/prepared')
start=time.perf_counter()
target, loading, eta, receipt=target_and_seeds(prepared,'deep')
endpoint, keys=initialize(target,loading,eta,seed=20261103)
print('GPU REAL INPUT INITIALIZED',time.perf_counter()-start,flush=True)
split=SplitTransition(target)
start=time.perf_counter()
r=split.adapt(keys[0],endpoint.positions[0],endpoint.state,state_factor_ids=target.factor_ids,steps=20)
jax.block_until_ready(r.history.state.position)
timing=dict(seconds=time.perf_counter()-start,steps=20,factor=target.factor_ids[0],
            scope='One factor only, includes compilation; not a production or convergence result',
            leapfrogs=np.asarray(r.history.info.block_leapfrogs).tolist(),
            divergences=np.asarray(r.history.info.block_divergent).tolist(),
            acceptance=np.asarray(r.history.info.block_acceptance).tolist())
(out/'warmup-timing.json').write_text(json.dumps(timing,indent=2)+'\n')
print('GPU VALIDATION COMPLETE',json.dumps(timing),flush=True)
