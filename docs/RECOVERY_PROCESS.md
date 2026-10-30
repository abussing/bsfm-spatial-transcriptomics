# Historical recovery process

The historical BSFM material contains overlapping attempts, experiments,
promoted methods, dead ends, and deadline-oriented shortcuts. File timestamps
and names are not evidence of authority.

For each capability:

1. Recover the scientific purpose and design intent.
2. Identify historical candidate implementations and the tasks that used them.
3. Trace their input and output artifacts rather than assuming one integrated
   historical system existed.
4. Record why revisions were introduced, promoted, rejected, or left unresolved
   whenever that evidence can be found.
5. Distinguish user approval, mathematical audit, empirical comparison,
   successful integration, and mere historical use.
6. Present the lineage and unresolved choices before selecting an implementation.
7. Use narrow invariant checks as guardrails; do not allow an invented test suite
   to silently redefine a judgment-dependent scientific objective.
8. Port selected code conservatively and one capability at a time.

Suggested evidence labels:

- `historically_used`
- `explicitly_user_approved`
- `mathematically_audited`
- `empirically_compared`
- `integrated_successfully`
- `experimental`
- `rejected`
- `unresolved`

