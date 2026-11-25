# Web-facing surfaces

Read when the change serves browsers or public HTTP clients.

- **Ask first** unless the exact change is already approved: new or changed
  authentication logic; new upload, webhook or callback handlers; rate-limit or
  throttling changes; relaxing CORS, security headers or cookie attributes.
- **Never:** treat client-side validation as a boundary; expose internal errors
  or stack traces to users; store sessions or tokens where page scripts can read them.
- **Baseline:** TLS for external traffic; CSP, HSTS and X-Content-Type-Options
  headers; httpOnly, secure and sameSite session cookies; passwords hashed with
  argon2, scrypt or bcrypt; encode output for its sink.
