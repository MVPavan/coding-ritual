# Python Safety

- Parameterize SQL and query inputs.
- Keep environment and configuration reads at the boundary layer, not scattered through business logic.
- Use explicit timeouts and bounded retries for network or subprocess I/O.
- Avoid blocking the event loop with synchronous I/O in async code.
- Do not use `eval`, `exec`, or unsafe deserialization on untrusted input.
- Validate user-controlled file paths and shell arguments.
- Never hardcode secrets.
