# Integrate DWS with a research host

The host decides the research question, selects sources, judges evidence, and
writes conclusions. DWS handles discovery, capture, retrieval, and exact reads.
Use the command API, CLI, or optional MCP adapter; all return the same retained
snapshot identities. No specific agent framework is required.

## Portable CLI adapter

Install the host CLI as described in the [operator guide](usage.md), start DWS,
and load `DWS_TOKEN` and `DWS_API_URL` from the local owner configuration. This
example uses only Python's standard library and the installed `dws` command.
It accepts a source selected by the caller; it does not choose a methodology.

```python
import json
import subprocess

def dws(*arguments):
    result = subprocess.run(
        ["dws", *arguments], capture_output=True, text=True, timeout=120
    )
    response = json.loads(result.stdout)
    if result.returncode:
        raise RuntimeError(response.get("error", response))
    return response

# The host may discover candidates with dws("search", question, "--limit", "5").
# Select and evaluate a public source before treating its content as evidence.
workspace = dws("workspace", "create", "research-project")["workspace_id"]
run = dws("run", "create", "research-run", "--workspace", workspace)["run_id"]
capture = dws(
    "fetch", "https://sqlite.org/fts5.html", "--render", "never",
    "--workspace", workspace, "--run", run,
)
snapshot = capture["snapshot_id"]
dws("pin", snapshot, "--workspace", workspace)
exact = dws("read", snapshot, "--workspace", workspace, "--max-chars", "4000")
print(json.dumps({
    "workspace_id": workspace,
    "run_id": run,
    "snapshot_id": snapshot,
    "source": capture["final_url"],
    "evidence": exact,
}, ensure_ascii=False))
```

To find passages after indexing, use `retrieve QUERY --workspace ID --run ID`.
Check `partial` and the returned index state; an indexing delay does not imply
that the source lacks relevant content. `read` is available immediately. Store
the snapshot ID and returned character/line locations with the host's citation;
read that snapshot again to verify a quotation. A refresh creates another
capture, so keep the earlier ID for an earlier claim.

## API and MCP hosts

The API uses `POST /v1/<operation>` with JSON and the local bearer token. Use
the same workspace/run fields shown above. MCP exposes `search`, `fetch`,
`crawl`, `retrieve`, `read`, `job_status`, and `job_cancel` at `/mcp/` when the
optional extra is enabled. Its retained resource links identify the same
snapshots; use bounded `read` calls for large documents.

Crawl jobs belong to DWS, even if a host disconnects. Retain the acknowledged
job ID and an idempotency key, then query status after reconnecting. Cancellation
preserves acquired evidence. Scheduling, monitoring decisions, synthesis, and
alerts remain responsibilities of the host.

Use separate workspaces for project scope. The local bearer token grants owner
access; workspaces are evidence partitions, not separate tenant credentials.
Only grant this token to trusted local callers. Keep credentials out of saved
research reports and shared example configuration.
