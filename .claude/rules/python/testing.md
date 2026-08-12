# Python Testing

- Use `pytest` unless the repo already standardizes on a different framework.
- For behavior-risky work, write a failing test or characterization test before changing the code.
- Prefer unit tests for pure logic and integration tests for I/O boundaries.
- Treat the test pyramid as effort guidance, not a quota: start near 80% unit, 15% integration, and 5% end-to-end, then adjust to the system's risks.
- Test sizes — **small:** one process, no I/O/network/database, milliseconds; **medium:** multi-process, local I/O or test databases, no external services, seconds; **large:** external services, browsers, staging, minutes.
- Pure logic with no side effects → unit/small. A database, filesystem, API, or component boundary → integration/medium. A critical full user flow → end-to-end/large; keep these few.
- Test behavior through public interfaces, not private implementation details.
- Prefer parametrization and shared fixtures over repetitive test bodies.
- Do not mock internals by default; mock hard external boundaries when needed.
- Reuse the repo's existing test directories, fixtures, and markers where they exist.
- The exact commands to trust live in `.claude/project/verification.md`.
