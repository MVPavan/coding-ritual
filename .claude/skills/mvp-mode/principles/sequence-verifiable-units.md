# Sequence verifiable units

Every step ends somewhere a check can confirm.

- Before the first change, run the work's checks on the starting base and
  record the results, so a later failure can be classed as pre-existing or as
  a regression.
- Split the work into small units that each end in a state the checks that unit
  needs confirm, and start a dependent unit only when they pass. In a declared
  migration group the group is the unit (`principle-migrate-without-shims`).
- Prefer independently verifiable vertical slices over horizontal layers.
- Find prefactoring that makes the change easy and sequence it before the
  feature slices.
- For a broad refactor, use expand, migrate then contract with genuine
  dependencies; when intermediate units cannot stay green, name one
  integration boundary or atomic group.
- Size migration batches by blast radius and keep the build green between them.
- Where commits are authorized, keep each small and about one thing.
- Where commits are authorized, order them so the history proves the work:
  the failing test before the fix, removal before reshaping, baseline before
  treatment, scaffold before feature, each commit standing on its own.
