#!/usr/bin/env bash
# Sign one §9 gate approval into its inbox.
#
# `foreman status` / `foreman run` render, per open gate, the inbox directory
# and an unsigned canonical payload template. Approval is exactly "drop
# payload.json and payload.json.sig into that inbox" (`foreman/gates.py`
# `intake`), with a nonce that has never been used under this root — the
# template ships a placeholder precisely so it cannot be signed as-is.
#
# The template is taken on stdin or as a third argument, and only its nonce is
# substituted: the signed bytes must stay the canonical emission of the payload
# (`bdio/signing.py` refuses a re-encoding), so nothing here re-serializes JSON.
# Edit the outcome in the template BEFORE piping it in if the gate needs a verb
# other than the one rendered.
#
# Usage: foreman ... status | jq -r '...template' | scripts/approve-gate.sh <inbox-dir> <key-path>
#        scripts/approve-gate.sh <inbox-dir> <key-path> template.json
set -euo pipefail

placeholder="replace-with-a-unique-nonce"
namespace="wf-gate"

if [ "$#" -lt 2 ] || [ "$#" -gt 3 ]; then
  echo "usage: $0 <inbox-dir> <key-path> [template-json]" >&2
  exit 2
fi
inbox=$1
key=$2
template=$(if [ "$#" -eq 3 ]; then cat -- "$3"; else cat; fi)

if [ ! -d "$inbox" ]; then
  echo "$0: gate inbox $inbox does not exist; take it from foreman status" >&2
  exit 1
fi
if [ ! -f "$key" ]; then
  echo "$0: signing key $key does not exist; scripts/make-foreman-config.sh makes one" >&2
  exit 1
fi
case "$template" in
  *"$placeholder"*) ;;
  *)
    echo "$0: the payload carries no $placeholder; a nonce is consumed by the gate it closes, so this one cannot be reused" >&2
    exit 1
    ;;
esac

nonce=$(python3 -c 'import uuid; print(uuid.uuid4().hex)')
payload="$inbox/payload.json"
printf '%s' "${template/$placeholder/$nonce}" >"$payload"
# `-Y sign` writes <file>.sig beside the file, which is the payload.json.sig
# name `intake` looks for.
ssh-keygen -Y sign -f "$key" -n "$namespace" "$payload" >/dev/null

echo "$payload"
echo "$payload.sig"
