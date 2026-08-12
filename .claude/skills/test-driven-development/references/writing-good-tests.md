# Writing good tests

Consulted from `test-driven-development` whenever tests are written or
changed — inside the loop or not. Two principles govern everything here:

1. **Every test names the break it catches.**
2. **Every test exercises the real thing.**

Examples are Python/pytest (this repo's stack); the principles are
language-neutral.

## Principle 1 — name the break

Before writing the test body, answer: *what production change should make
this test fail — and is that change a bug or a decision?* A test earns its
place by catching a wrong branch, missing side effect, wrong argument,
boundary case, or broken contract.

- **Derive expectations independently.** Hand-checked literals and worked
  fixtures; parametrized tests with literal `expected` values are the
  preferred shape. An expectation computed by the code under test — or its
  helpers — passes no matter what the code does:

  ```python
  # tautological — the code under test computes both sides; always true
  expected = calculate_total(items)
  assert calculate_total(items) == expected

  # still suspect — rebuilds the expectation with the same helper the
  # implementation uses, so a shared bug passes
  assert build_query(tag="urgent") == build_query(tag="urgent")

  # independent — a hand-derived literal
  assert calculate_total([Item(price=10), Item(price=5)]) == 15
  ```

- **No change detectors.** If only intentional decisions can fail a test —
  a constant's value, exact message wording, private structure — it fires on
  redesign and sleeps through bugs. Not `assert MAX_RETRIES == 5` but "a
  failing call is retried 5 times and the 6th attempt never happens."
- **Behavior, not text.** Asserting that a script or config contains an
  exact line proves only that the source is the source. Run the artifact
  against controlled inputs and assert outputs, side effects, or exit codes.
- **Your code, not the framework.** Test the contract your code makes at its
  boundaries — the route you register, the query you emit, the model you
  produce. Framework mechanics are their maintainers' tests. Constructors,
  trivial forwarding, and plain getters earn tests only when they validate,
  normalize, default, derive, or cause side effects.

## Principle 2 — exercise the real thing

- **Mock at system boundaries only** — external APIs, time, randomness,
  network. Never your own classes or internal collaborators. Preference
  order: real implementation > fake (in-memory) > stub > mock. Prefer a real
  test DB or in-memory fake over mocking your own store layer.
- **Mocked internals earn no assertions.** An assertion on a mock's mere
  presence, or on calls to a mocked internal collaborator, passes when the
  mock exists and says nothing about your component — unmock it or delete
  the assertion. The exception is a true outbound boundary where the
  interaction *is* the observable contract: "the email is sent exactly
  once", "the payment request carries the idempotency key" are legitimate
  assertions on arguments, counts, or ordering.
- **Mock at the right level.** Learn every side effect of the real method
  before replacing it; mock the slow or external operation and keep what the
  test depends on real.
- **Mirror real data completely.** Mock responses carry the complete real
  structure, not just the fields your test reads — partial mocks pass while
  integration breaks on the omitted field.
- **Test-only methods stay out of production classes.** Cleanup only tests
  need lives in test utilities, never as a method on the production class.
- **When mock setup outgrows the test logic**, switch to an integration test
  with real components.
- **Design for mockability at boundaries**: inject external dependencies
  (constructor injection per the repo's config rules), and prefer specific
  SDK-shaped functions per external operation over one generic fetcher —
  each mock then returns one specific shape.

## Shape

- **State, not interactions.** Assert the outcome of an operation, not which
  internal methods were called in what order.
- **Verify through the interface**, not a side channel — retrieve the thing
  you created via the API, don't query the table behind it.
- **Arrange-Act-Assert**, one behavior per test, one assertion per concept.
- **DAMP over DRY**: some duplication is fine when it makes each test
  independently readable as a specification. Prefer `pytest.mark.parametrize`
  over copy-pasted bodies, and literal expected values inside the parameter
  list.
- **Names read as specification**: `test_completing_completed_task_is_noop`,
  not `test_complete_2`.

## The mutation check

Before finishing a test file, mentally mutate the production code; at least
one test should fail for each realistic mutation:

- wrong constant or argument
- wrong branch taken
- missing state change or side effect
- empty or default return
- missing validation for zero, empty, `None`, unauthorized, malformed input

A mutation nothing catches marks the behavior as unprotected — or the test
as tautological.

## Warning signs

- Setup and assertion share the same object, guaranteeing equality.
- The test sleeps, depends on wall-clock time or randomness it doesn't
  control, or fails when run in a different order.
- A test passes alone and fails with the suite (leaked shared state — each
  test owns its setup and teardown).
- The test can fail only through a crash.
- Expected values hidden behind loops, builders, or shared helpers.
- The test greps source text.
- An assertion checks a mock artifact, or fails if you remove the mock.
- A method is called only from test files.
- Mock setup is more than half the test.
- The test exists for coverage and checks no outcome.
