# Requested meeting runs (review branch)

The user selected K=12, L=14 and the sequence 50 initial tuning steps per
factor, 50 full Gibbs bridge sweeps, 100 retuning steps per factor and 1,000
production sweeps. Four masks are selected: 12/8 circles crossed with diameters
1/16 and 1/8. Full-sample SCT reuse was explicitly approved. These are preliminary
transductive comparisons, not primary training-only-normalized validation.

The common input preparation applies each exact saved mask, centers each gene
using training cells within type, and runs the accepted GP-smooth SVD initializer
on training observations only (K=12, nfit=250/type). Both models share those
prepared inputs and seeds. The full 371-mode mesh is unchanged; its projector is
restricted to training rows. No expression from held-out cells enters GPINIT or
the Gibbs sampler. Scoring targets are stored separately.

The new explicit readaptation controller creates a separate child production
run. It authenticates the complete parent chain and completed checkpoint,
restores state and all RNG streams, splits the parent JAX master into next
master plus ordered factor warmup keys, and calls existing sequential adaptation.
It does not rerun initialization or PX initialization, mutate the parent or pool
bridge draws. Exact resume of a published child genesis never retunes again.
The ordinary controller's initialization arithmetic remains unchanged; only a
small overridable method was extracted. Genesis validation distinguishes the
original post-PX initialization boundary from the explicit readaptation boundary.

The flat control fixes W to reference coordinates minus the training-coordinate
mean. It samples alpha/zeta with the same collapsed finite-feature target,
loading penalty and priors, and uses existing conjugate/shrinkage/PX/joint-eta
updates. Warp fields and warp hyperparameters are not sampled. Extra chart
coordinates are fixed transport fields for shared checkpoint storage. The
second diagnostic block is disabled: zero steps, energy and acceptance, not a
second successful transition. Flat target identity records this model difference.
BlackJAX occasionally returns a probability slightly above one due to floating
rounding; this flat-only implementation maps (1,1+8*eps] to 1 and otherwise
retains the existing invalid-diagnostic failure. Invalid numeric target proposals
are rejected without parameter clipping. Divergences remain visible.

Prediction uses retained child-production states and the finite-feature Gaussian
conditional given training eta. For deep fields, unobserved mesh degrees of
freedom are sampled conditionally using the full spectral factor and orthogonal
QR completion; they are not set to zero or replaced with a conditional mean warp.
Prediction RNG is independent of sampler streams. `predict_partial.py` snapshots
up to 20 evenly spaced committed production records, computes conditional means
and marginal variances, and records the precise source receipts. No draws from
the bridge are used. Sparse early samples do not establish convergence.

Local focused validation: both-model synthetic initialization, adaptation,
bridge, child retuning, production and completed non-replay passed; parent files
remained byte-identical and changed parent bindings were rejected. Flat values
and gradients matched independent dense Gaussian calculations. Finite-feature
prediction matched an independent dense Gaussian conditional. Conditional warp
completion reproduced active observations. L14 dimensions, weights and hashes
passed. These are bounded synthetic checks, not real S10 mixing/performance.
The earlier failed local checks are retained externally; the flat probability
roundoff boundary above resolved their failure. Canonical L16 is unchanged.

HPC validation must pass before preparation and the eight scientific runs are
submitted. RUN_SPEC.json and the three sbatch files define resources. Sample
jobs have 12 hours of headroom; every completed sweep is checkpointed and every
production sweep retained. Five-hour completion is not promised. No GPU support
is inferred from the CPU implementation. Layer 9 and these extensions remain
on the review branch and are not merged into accepted main.
