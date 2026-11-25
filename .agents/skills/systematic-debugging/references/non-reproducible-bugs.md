# Non-reproducible and flaky bugs

Load when the bug will not reproduce on demand, or a test is flaky. Two moves,
in order: diagnose *why* it flakes, then raise the reproduction rate until the
reproduction is debuggable.

## Diagnose the flake class

```text
Cannot reproduce on demand — which class?
├── Timing-dependent
│   ├── add timestamps to logs around the suspect area
│   ├── widen race windows: inject sleeps at suspected interleavings
│   └── run under load / parallelism to raise collision probability
├── Environment-dependent
│   ├── diff versions, OS, env vars between where it fails and where it doesn't
│   ├── diff the data (empty vs populated store)
│   └── reproduce in CI or a container where the environment is clean
├── State-dependent
│   ├── hunt leaked state between tests or requests
│   ├── check globals, singletons, module-level caches, mutable class attributes
│   └── run the failing scenario alone vs after other operations
│       (pollution confirmed → the systematic-debugging skill's `scripts/find-polluter.sh`)
└── Truly random — none of the above reproduces it
    ├── add defensive logging at the suspected site, tagged
    ├── alert on the exact error signature
    └── document the observed conditions; revisit on recurrence
```

## Raise the reproduction rate

The goal is not a clean repro but a rate high enough to debug against: loop
the trigger 100×, parallelise, add stress, narrow timing windows, inject
sleeps at suspected races. A 50% flake is debuggable; 1% is not — keep raising
the rate, then make that rate the reproduction you diagnose against.

## Environmental cause — an end-state finding, not an exit

Claimable only after the hypotheses are exhausted: every one falsified and the
flake tree above walked. Then an external or environmental root cause
is reported to the user as **UNRESOLVED FINDING** with the written
investigation attached — branches tried, rates reached, hypotheses falsified.
Never present a mitigation (retry, timeout, monitoring) as the fix; whether to
ship one is the user's decision to make on the finding. 95% of "no root
cause" is incomplete investigation.
