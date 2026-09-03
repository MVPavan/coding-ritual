#!/usr/bin/env bash
# Render config/foreman.example.toml for the current checkout.
#
# A live foreman config names absolute machine paths and a hash-derived
# wrapper root, so it is generated rather than committed. The default output
# is scratchpad/foreman.toml, which is gitignored.
#
# Usage: scripts/make-foreman-config.sh [output-path]
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
template="$script_dir/../config/foreman.example.toml"

repo_root=$(git rev-parse --show-toplevel)
repo_root=$(cd -- "$repo_root" && pwd -P)
wrapper_home="$HOME/.wf"
output=${1:-$repo_root/scratchpad/foreman.toml}

# `ForemanConfig.wrapper_root` is wrapper_home/<first 16 hex of sha256(repo_root)>,
# and the model refuses a supervisor whose wrapper_root differs from it.
digest=$(printf '%s' "$repo_root" | sha256sum | cut -c1-16)
wrapper_root="$wrapper_home/$digest"

host=$(hostname 2>/dev/null || uname -n)
actor="wf-$USER"

mkdir -p -- "$wrapper_home" "$(dirname -- "$output")"

# §9 gate key. The allow-list must live outside the bd workspace (the repo), so
# it is generated here beside the wrapper home. Never overwritten: a regenerated
# key silently invalidates every approval an operator has already prepared, and
# the allow-list is the authority the foreman trusts.
signers_dir="$wrapper_home/signers"
key="$signers_dir/gate_key"
allow_list="$signers_dir/allowed_signers"
if [ -e "$allow_list" ]; then
  echo "kept existing $allow_list"
else
  mkdir -p -- "$signers_dir"
  if [ ! -e "$key" ]; then
    ssh-keygen -t ed25519 -N "" -C "$actor" -f "$key" >/dev/null
    echo "generated $key"
  fi
  # `principals keytype base64-key [comment]` — the sshsig ALLOWED SIGNERS
  # grammar `bdio/signing.py` parses. No `namespaces=` option: this key signs
  # gates only, and a restriction the parser must honour is one more thing to
  # get wrong for no gain here.
  printf '%s %s\n' "$actor" "$(cat -- "$key.pub")" >"$allow_list"
  echo "wrote $allow_list"
fi

sed \
  -e "s|@REPO_ROOT@|$repo_root|g" \
  -e "s|@WRAPPER_HOME@|$wrapper_home|g" \
  -e "s|@WRAPPER_ROOT@|$wrapper_root|g" \
  -e "s|@HOST@|$host|g" \
  -e "s|@ACTOR@|$actor|g" \
  "$template" >"$output"

echo "wrote $output"
echo "to approve a gate by hand, sign its payload in the wf-gate namespace:"
echo "  ssh-keygen -Y sign -f $key -n wf-gate payload.json"
echo "or let scripts/approve-gate.sh do it: scripts/approve-gate.sh <inbox> $key"
