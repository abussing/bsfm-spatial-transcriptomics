# Readiness for the requested overnight leave-out experiment

The requested deadline is one hour from the user's 2026-11-03 instruction. It
includes prerequisite implementation and validation; it does not waive them.
No overnight scientific job has been submitted by this review.

## What is already available

- Accepted scientific/preparation main `eeb6d9a903663907bbcb2d081bcec05475788ee1`.
- Verified HPC mirror of all 187 canonical files; no further recovery required.
- Accepted fixed-design S10 mesh and full-data S10 prepared input/GPINIT for a
  mechanical integration smoke. They are not primary holdout-scoring inputs.
- Accepted numerical Layers 1-8. The Layer-9 candidate adds orchestration;
  its local Windows synthetic evidence is separate from Linux validation.

## Required execution sequence

1. Review the complete Layer-9 candidate and its evidence. Preserve the ordinary
   saved-fixture failures and the separate exact same-environment comparisons.
2. Establish a frozen Linux environment for the later layers, a supported Linux
   single-writer implementation, and bounded synthetic warmup/sweep/resume tests.
   The existing `sampler-cpu-py311` prefix reports JAX/jaxlib 0.7.0, NumPy 2.1.3,
   SciPy 1.14.1 and no installed BlackJAX. Its prior validation covers Layers 1-3.
   Windows byte-locking and wheel/runtime authentication are not a Linux launcher.
3. Specify the small S10 end-to-end mechanical smoke with explicit resource
   limits and parameters; execute only from the reviewed committed code and
   committed run specification. Existing K=20/nfit=250 values are mechanical
   preparation settings, not automatically production choices.
4. Implement and validate the first primary spatial holdout:
   - Freeze one deterministic hole and held-out source-row identities before
     looking at outcomes; exclude all cell types within it from preprocessing.
   - Use training-only SCT fitting, depth and centering, with the frozen model
     applied to held-out observations only to construct scoring targets.
   - Preserve the accepted fixed-design geometry and coordinate frame; mask
     observations without silently rebuilding or renormalizing the mesh.
   - Generate training-only GPINIT, run warped and matched identity-warp models,
     and produce conditional posterior predictions for the same omitted cells.
   - Validate prediction algebra on synthetic examples and select explicit
     chain/warmup/settling/production/save settings and scoring metrics.
5. Freeze the experiment/run specification and code/environment/input identities,
   obtain the required run approval, then submit. Record scheduler job IDs and
   exact result locations. A queued job is not evidence of a successful fit.

## Concrete outstanding implementation

The accepted repository does not yet implement training-only holdout application,
the matched flat-model runtime, or the posterior prediction/scoring pipeline.
The canonical SCT installation is not available in the documented HPC prefix;
the interrupted Linux R mesh build is not SCT restoration. These are actual
development/environment tasks, not missing copies of already verified data.

No full-data SCT response or historical fit is substituted to make a submission
appear ready. No large 19-section/hole-size grid is started. Given these remaining
requirements, a valid leave-out submission within the requested hour is not
established by this review.
