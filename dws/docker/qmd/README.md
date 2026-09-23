# Application QMD lexical dependency

`package.json` and `package-lock.json` are byte-for-byte copies of the accepted
cr-0km.11 runtime's manifests. Do not resolve a new transitive tree for this image.
The application Dockerfile uses `npm ci --ignore-scripts --no-audit --no-fund`
with `/dev/null` user configuration. No upstream installation script runs.

Native artifacts come from integrity-checked npm tarballs, not local binaries.
The Dockerfile verifies the accepted Linux x64 better-sqlite3 and sqlite-vec
SHA-256 values before copying the installation into the final stage.

The full locked install includes `@modelcontextprotocol/server` and `core` 2.0.0.
The Dockerfile moves that namespace outside the copied tree in the builder:
Delivery A's final application image must contain no MCP SDK. QMD 2.8.3 imports
its MCP server dynamically only in its `mcp` command; the published package
files remain unchanged. The final dependency tree is deliberately incomplete
for MCP. Do not use `npm ci` inside the final image or claim full QMD support.
Other locked dependencies, including lazy model-related code/native libraries,
remain installed. No models are supplied, downloaded, or exercised.

Build from the repository root with `bash dws/docker/application_build.sh`.
The helper streams an explicit source allowlist; it never copies a host runtime,
node_modules, virtual environment, credentials or repository history.
See [application qualification](../../../docs/verification/dws/application-image-qualification.md)
for exact digests, commands, limitations and observed results.
