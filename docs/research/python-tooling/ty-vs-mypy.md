# ty versus mypy for this repository

Date and source retrieval: 2026-09-09.

## Decision

Keep `mypy --strict` as the required interpreter gate. Keep the user-added ty
dependency available for optional feedback; do not require both checkers on every
change. Ruff remains the formatter/linter, Pydantic the preferred modeling tool,
and uv the package manager. This is a repository-specific decision, not a ranking
of the vendors or a recommendation against ty generally.

Replacing the gate is not currently a command-only migration: default ty changes
diagnostic coverage, and its stricter configuration needs additional triage. The
measured saving on an unchanged cached run is negligible here.

## Local evidence

Versions: ty 0.0.79, mypy 2.3.1, Python 3.13.9. Installed the existing locked dev
dependencies using `uv sync --locked --group dev`; did not change the manifest or
lockfile. Both tools used the same environment and `workflow_interpreter/` target.
Mypy reported 91 checked source files.

| Run | mypy strict | ty defaults, warnings treated as failures |
| --- | ---: | ---: |
| First invocation; empty dedicated mypy cache | 1.8758 s | 0.0990 s |
| Unchanged rerun 1 | 0.0907 s | 0.0886 s |
| Unchanged rerun 2 | 0.0922 s | 0.0915 s |
| Exit status, all three runs | 0 | 1 |

Mypy passed. Ty emitted four diagnostics: one module/property name-resolution
diagnostic in `workflow_interpreter/bdio/api.py:291`, and three narrowing/type
diagnostics in `workflow_interpreter/foreman/resolve.py:156`, `:160`, and `:164`.
These have not been established as runtime bugs. No production code was changed
to silence them.

Method: sequential subprocess timings with `time.perf_counter`, alternating mypy
then ty in each of three rounds. Binaries were invoked directly to exclude uv
environment-management overhead. This is a small local sample, not a controlled
benchmark: OS caches were not cleared, tool order was fixed, and incremental runs
did not modify source. Different diagnostics mean different work. The roughly
19x first-run ratio must not be generalized to editing sessions or other projects.

Commands, from the repository root:

```bash
MYPYPATH=. MYPY_CACHE_DIR=scratchpad/typechecker-comparison/mypy-cache .venv/bin/mypy --strict --explicit-package-bases workflow_interpreter/
.venv/bin/ty check workflow_interpreter/ --output-format concise --error-on-warning
```

Six isolated code probes gave the following results:

| Probe | Current mypy strict | Default ty |
| --- | --- | --- |
| Valid Pydantic model with ConfigDict and Field factory | Accepts | Accepts |
| String returned from an int-returning function | Rejects | Rejects |
| Function without parameter/return annotations | Rejects | Accepts |
| Any returned from an int-returning function | Rejects | Accepts |
| List supplied to an integer Pydantic field | Rejects | Rejects |
| Assignment to a frozen Pydantic field | Accepts | Rejects |

The current mypy invocation has no Pydantic plugin configured. These probes do
not demonstrate that mypy is universally stricter or that ty lacks Pydantic
support. Frozen-field detection is a concrete advantage of ty in this sample.

Using Astral's recommended stricter ty rules produced 13 diagnostics across the
interpreter. The companion Ruff ANN/PYI preview check produced one additional
diagnostic about an explicit Any. Those results need classification before
adoption; neither blanket suppressions nor dropping strict checks would be an
equivalent migration.

Local scripts, snippets, outputs, and timings are gitignored under
`scratchpad/typechecker-comparison/`. The table records the decision evidence;
the temporary scripts are not a new project test suite.

## Primary-source findings

Astral reports substantial uncached speed gains for ty and positions it for
production use. These are vendor measurements, not this repository's expected
latency. Our first-run measurement supports a speed advantage, while the cached
comparison limits its practical significance here.
[Astral announcement](https://astral.sh/blog/ty)

Ty intentionally does not require annotations. Astral recommends Ruff ANN rules
for that responsibility. It has no mypy-compatible plugin system. The FAQ's
statement about considering library integrations is less specific than the
current rule reference, which already documents Pydantic-specific diagnostics;
do not infer missing Pydantic support from that FAQ paragraph.
[Typing FAQ](https://docs.astral.sh/ty/reference/typing-faq/),
[Pydantic diagnostic](https://docs.astral.sh/ty/reference/rules/#pydantic-discarded-extra-argument)

The migration guide recommends a combination of additional ty checks and Ruff
ANN/PYI rules to approximate strict checking. Its mapping also lists coverage
differences with no direct equivalents. Default ty is therefore not synonymous
with `mypy --strict`.
[Migration guide](https://docs.astral.sh/ty/coming-from-mypy-or-pyright/)

## Revisit conditions

The strongest case for replacing mypy is faster uncached feedback plus ty's
Pydantic-aware diagnostics and editor experience. A focused migration should:

1. Resolve or narrowly document the current diagnostics without weakening runtime
   behavior or adding blanket ignores.
2. Select and test ty/Ruff rules that preserve the desired annotation and dynamic
   type boundaries; validate representative Pydantic, Protocol, and narrowing cases.
3. Measure representative changed-file/editor workloads, not only unchanged runs.
4. Update the verification script, project docs, dependency groups, and sandbox
   verification expectations together before removing mypy.

Confidence is high in the recorded local results and documented differences;
moderate in the stay-with-mypy decision because this small repository sample
does not measure ty's editor responsiveness or future releases.
