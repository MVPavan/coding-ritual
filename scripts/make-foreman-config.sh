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

mkdir -p -- "$wrapper_home" "$(dirname -- "$output")"
sed \
  -e "s|@REPO_ROOT@|$repo_root|g" \
  -e "s|@WRAPPER_HOME@|$wrapper_home|g" \
  -e "s|@WRAPPER_ROOT@|$wrapper_root|g" \
  -e "s|@HOST@|$host|g" \
  -e "s|@ACTOR@|wf-$USER|g" \
  "$template" >"$output"

echo "wrote $output"
