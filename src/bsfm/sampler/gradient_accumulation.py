"""Fixed-incidence reduction for repeated-index GPU gradient accumulation."""
import numpy as np
import jax.numpy as jnp


def fixed_incidence_reducer(indices, n_active):
    """Build a gather/reduce with no conflicting writes, in cell/corner order.

    Geometry is static. Padding costs n_active * maximum vertex incidence,
    not n_active * number of cells. Exact replay is a same-runtime guarantee;
    this does not promise identical sums across hardware or compiler versions.
    """
    flat = np.asarray(indices).reshape(-1)
    groups = [np.flatnonzero(flat == vertex) for vertex in range(n_active)]
    width = max(1, max(map(len, groups), default=0))
    padded = np.zeros((n_active, width), np.int32)
    mask = np.zeros((n_active, width), bool)
    for vertex, group in enumerate(groups):
        padded[vertex, :len(group)] = group
        mask[vertex, :len(group)] = True
    padded, mask = jnp.asarray(padded), jnp.asarray(mask)

    def reduce(contributions):
        return jnp.sum(jnp.where(mask[:, :, None], contributions[padded], 0.), axis=1)

    return reduce
