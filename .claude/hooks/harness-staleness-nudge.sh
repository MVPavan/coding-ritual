#!/usr/bin/env bash
# SessionStart nudge: if the reference-harness catalogs haven't been refreshed in
# over 30 days, print a one-line reminder to run /harness-status. Reads file
# timestamps only — never fetches, scans, or touches the submodules. Curation-only
# (harness-* name), so build-template.sh strips it from the shipped template.
set -u
DIR="${CLAUDE_PROJECT_DIR:-.}/harness_lifecycle/catalogs"
[ -d "$DIR" ] || exit 0
# ours.json is our own working-tree snapshot, regenerated often — it would mask
# stale reference catalogs forever, so it never counts toward freshness here.
if [ -z "$(find "$DIR" -name '*.json' ! -name 'ours.json' -newermt '30 days ago' 2>/dev/null | head -1)" ]; then
  echo "[harness-lifecycle] reference-harness catalogs are >30 days old — run /harness-status to check upstream drift."
fi
exit 0
