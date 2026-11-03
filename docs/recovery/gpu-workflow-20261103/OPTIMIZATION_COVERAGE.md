# Optimization coverage and revised priority

On 2026-11-03 the user clarified that preserving completed iterations and avoiding repeated warmup are not priorities. Recovering the best-supported analytic and GPU implementation is the priority. An exact code-upgrade continuation is therefore deferred; a fresh scientific run is acceptable once the execution path is verified. This clarification does not itself identify a replacement launch configuration or require cancellation of current jobs.

The saving correction is only one part of this review. The following mechanisms were inspected directly in current source. Presence and earlier equivalence evidence do not establish optimal full-workflow performance or exhaustive coverage of months of historical development.

| Mechanism | Current implementation | Evidence / remaining question |
| --- | --- | --- |
| Analytic finite-feature likelihood gradient | `finite_features.py:make_feature_kernel.likelihood_parts`, `field_kernels.py` | Explicit feature/phase/physical-coordinate derivatives; Layer-3 source map records exact helper-body matches to selected historical source. Not replaced with a generic differentiation-through-everything target. |
| Feature-space Gaussian algebra | `finite_features.py` | Feature-sized Hessian, Cholesky and contraction rather than observation-sized dense covariance in this target. Explicit inverse-Hessian contraction remains; determine whether a later supported implementation improved this. |
| Analytic gradient supplied to BlackJAX | `split_kernels.py:make_logdensity` | Custom VJP returns the supplied position gradient; reference autodiff exists separately for checking. |
| Compiled split field/hyperparameter transitions | `split_kernels.py:build_split` | JIT transition and JIT scan; physical W held fixed during hyperparameter block. Fifty/100-step selected-source CPU comparisons passed. Inspect compilation reuse and host/device boundary costs at realistic dimensions. |
| Joint-eta perturb-and-solve | `joint_eta_kernels.py`, `layer4.py` | JIT precision operator/PCG and vectorized block-preconditioner solves present. Layer-4 map documents unchanged mathematical bodies and decorators. This is not a replacement dense observation-space sampler. |
| Active marginal / full spectral geometry | `active.py`, `warp.py`, `centered_hyper_kernels.py` | Selected QR/full-mode marginal construction retained; do not substitute a different mesh or truncated model as a performance fix. |
| Conjugate updates and factor chronology | `conjugate.py`, `layer6.py` | Selected NumPy/SciPy conjugate work remains on host, as in selected historical path; whole sampler must not be described as exclusively GPU resident. Fresh literal chronological comparison passed. Later alternatives require their own evidence. |
| Live-state saving | `run_incremental.py` | Confirmed repeated-history validation regression addressed by opt-in candidate. GPU job 22015748 passed exact three-transaction comparison, candidate process-death recovery and non-replay. Full-size throughput not yet established. |

## Outstanding historical comparison

The selected October-26 driver and October-24 campaign copy match exactly, but that does not establish that every optimization developed earlier or later is represented. The existing source ledger compares base, production overlay and LI experiment branches; its nomination was deliberately bounded. Review later source submissions and actual execution receipts against specific numerical mechanisms rather than selecting by filename or date alone. A conversation claim is a search lead, not proof of execution or superiority.

The conversation index also includes analytic Fourier/area-Wasserstein work. That is postprocessing machinery, not automatically a missing Gibbs transition optimization. Keep its recovery separate while preserving its relevance to the eventual analysis pipeline.

For each additional candidate, record the source identity, intended improvement, numerical/model compatibility, executed validation and realistic timing evidence. Classify it as retained, omitted with a reason, superseded, or unresolved. Do not call this checklist exhaustive until the outstanding historical comparison is complete. Do not silently promote experimental LI/Fisher transitions over the accepted architecture.

## Next execution decision

Select the numerical and orchestration path from this comparison, then measure compilation, adaptation, sampler transitions, validation, serialization and end-to-end saved-iteration throughput separately on a bounded representative GPU workload. Repeating warmup is acceptable. Solving migration of old checkpoint software identities is no longer a prerequisite to a fresh run.
