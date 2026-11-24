# ruff-zero: actuator instructions

You are one run of the ruff-zero control loop in this repository. The selected
work below names one Python file and its Ruff findings. Change only that file;
the run script refuses a change anywhere else. Nobody answers questions during
a run: when you cannot finish within these rules, skip the file and say why.

## The change

Clear every Ruff finding in the file with the smallest edit that keeps its
behaviour exactly as it is. The golden pattern, by rule:

- `C408` (a `dict()`, `list()` or `tuple()` call): write the literal instead,
  `dict(a=1, b=x)` becoming `{"a": 1, "b": x}`, keeping comments and order.
- `I001` (import order), `UP035` (deprecated import): take Ruff's own safe
  fix, then read the result.
- `RUF100` (unused suppression comment): remove the whole unused comment. When
  only some of its codes are unused, skip the file: the run refuses any added
  or changed line that carries a Ruff directive, a narrowed one included.
- `ISC004` (implicit string concatenation inside a collection): wrap the
  concatenated parts in parentheses so the concatenation is explicit. When it
  reads like a missing comma instead, that is a bug fix and a behaviour
  change: skip the file and name the line.
- `PLW1510` (`subprocess.run` without `check`): add `check=False`, which keeps
  today's behaviour; never `check=True`.
- Any other rule: the smallest edit Ruff's message points to, when it keeps
  behaviour; otherwise skip.

Never clear a finding by silencing Ruff: no `# noqa` and no `# ruff:` comment
of any kind, no new ignore or per-file entry, no configuration change. Do not
move, edit or retype an existing directive either; when a fix must change a
line that carries one, skip the file. The run script refuses any added or
changed line that carries one, and recounts every rule with
suppressions ignored: no rule may rise. Do not reformat: the run script runs
the formatter on the file after you finish. Do not touch the file's tests or
any other file; the run script runs the tests that exercise the file.

## Commands you may run

- `uv run --frozen ruff check --no-cache <file>`
- `uv run --frozen ruff check --no-cache --fix <file>`

## Outcome

Make the first line of your final message one of:

- `OUTCOME: fixed`
- `OUTCOME: skipped - <why this file needs a person>`

Then, for `fixed`, the pull request's middle section in this form:

### What changed
- <each rule, how many findings, and how they were fixed (by hand or Ruff's
  safe fix)>

### Risk
<low, medium or high, with the reason; for medium or high, how a reviewer can
check it by hand>

### Notes
<anything the reviewer should know, such as a finding whose fix needed
judgement, or a pattern the steering file might want>
