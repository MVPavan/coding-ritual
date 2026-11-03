#!/usr/bin/env bash
# Make one verified disposable copy of a checkout, or stop with a reason.
# usage: make-copy.sh [--expect STATE] SOURCE DEST
# The copy has SOURCE's HEAD, staged state, unstaged state and untracked files that
# are not ignored, with its own object storage, no remote and no hooks. A raw manifest
# (type, bytes or link target, executable bit of each covered path) proves it equal.
# Ignored paths and submodule contents are not copied; a moved submodule is refused.
# DEST.state records HEAD, the index tree, the working tree, the refs and the manifest;
# --expect refuses a source that no longer matches an earlier state.
# Exit 0 prints DEST; exit 2 prints a reason. A failed run may leave a partial DEST
# with no state file: it is not a copy, so do not use it.

die() { echo "make-copy: $*" >&2; exit 2; }
is_id() { printf '%s' "$1" | grep -Eq '^[0-9a-f]{40,64}$'; }
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE
export LC_ALL=C
git() { command git -c core.hooksPath=/dev/null "$@"; } # a source hook must not change what this observes

expect=
if [ "${1:-}" = --expect ]; then expect=${2:-}; [ -n "$expect" ] || die "--expect needs a state file"; shift 2; fi
[ $# -eq 2 ] && [ -n "$1" ] && [ -n "$2" ] || die "usage: make-copy.sh [--expect STATE] SOURCE DEST"
dest=$2
[ ! -e "$dest" ] && [ ! -e "$dest.state" ] || die "$dest or its state file already exists"
src=$(git -C "$1" rev-parse --show-toplevel) && [ -n "$src" ] || die "$1 is not inside a working tree"
parent=$(cd "$(dirname "$dest")" 2>/dev/null && pwd -P) || die "the folder for $dest does not exist"
case "$parent/" in "$src"/*) die "$dest is inside the checkout" ;; esac
dest=$parent/$(basename "$dest")
work=$(mktemp -d) && [ -n "$work" ] || die "cannot make a temporary folder"
trap 'rm -f "$work/i" "$work/i.lock" "$work/list" "$work/staged" "$work/unstaged"; rmdir "$work" 2>/dev/null' EXIT

tree_of() { # the tree Git would store for a checkout's tracked and non-ignored files
  GIT_INDEX_FILE=$work/i git -C "$1" read-tree HEAD || return 1
  GIT_INDEX_FILE=$work/i git -C "$1" add -A -- . || return 1
  GIT_INDEX_FILE=$work/i git -C "$1" write-tree
}
manifest() { # one line per covered path: type, raw content or link-target hash, exec bit
  local f p k h x t
  git -C "$1" ls-files -z --cached --others --exclude-standard > "$work/list" && sort -zu -o "$work/list" "$work/list" || return 1
  [ -s "$work/list" ] || return 1
  while IFS= read -r -d '' f; do
    p=$1/$f x=- h=-
    if [ -L "$p" ]; then k=link; t=$(readlink "$p") && h=$(printf '%s' "$t" | sha256sum) || return 1
    elif [ -d "$p" ]; then k=dir # a submodule: the tree holds its pointer
    elif [ -f "$p" ]; then k=file; h=$(sha256sum < "$p") && is_id "${h%% *}" || return 1; [ ! -x "$p" ] || x=x
    elif [ -e "$p" ]; then k=other
    else k=gone; fi
    printf 'M %s %s %s %q\n' "$k" "${h%% *}" "$x" "$f"
  done < "$work/list"
}

# Refuse what a snapshot cannot carry.
flags=$(git -C "$src" ls-files -u) || die "cannot read the index"
[ -z "$flags" ] || die "the index has unmerged paths"
for f in MERGE_HEAD CHERRY_PICK_HEAD REVERT_HEAD rebase-merge rebase-apply BISECT_LOG; do
  p=$(git -C "$src" rev-parse --path-format=absolute --git-path "$f") || die "cannot read Git state"
  [ ! -e "$p" ] || die "an operation is in progress ($f)"
done
sparse=$(git -C "$src" config --bool core.sparseCheckout); rc=$? # 1 means unset
[ "$rc" = 0 ] || [ "$rc" = 1 ] || die "cannot read the Git config"
[ "$sparse" != true ] || die "sparse checkout is on"
flags=$(git -C "$src" ls-files -v) || die "cannot read the index"
if printf '%s\n' "$flags" | grep -q '^[a-zS] '; then die "some paths are marked skip-worktree or assume-unchanged"; fi
vis=$(git -C "$src" diff --cached --name-only --ita-visible-in-index) || die "cannot read the index"
inv=$(git -C "$src" diff --cached --name-only --ita-invisible-in-index) || die "cannot read the index"
[ "$vis" = "$inv" ] || die "the index has intent-to-add paths"

capture() { # the manifest comes last, so it sees any change made during the tree reads
  head=$(git -C "$src" rev-parse --verify 'HEAD^{commit}') && is_id "$head" || die "cannot read HEAD"
  idx=$(git -C "$src" write-tree) && is_id "$idx" || die "cannot read the index tree"
  wt=$(tree_of "$src") && is_id "$wt" || die "cannot snapshot the working files"
  refs=$(git -C "$src" for-each-ref) || die "cannot read the refs"
  man=$(manifest "$src") || die "cannot read the raw files"
}
quiet() { capture; [ "$head$idx$wt$refs$man" = "$first" ] || die "the source changed during the copy; try again when it is quiet"; }
capture; first=$head$idx$wt$refs$man
if [ -n "$expect" ]; then
  [ "$(sed -n 1,3p "$expect")" = "$head
$idx
$wt" ] && [ "$(sed -n '/^M[ ]/p' "$expect")" = "$man" ] || die "the source no longer matches $expect"
fi

dopts='--binary --no-renames --no-ext-diff --src-prefix=a/ --dst-prefix=b/'
# shellcheck disable=SC2086
git -C "$src" diff $dopts "$head" "$idx" > "$work/staged" || die "cannot write the staged patch"
# shellcheck disable=SC2086
git -C "$src" diff $dopts "$idx" "$wt" > "$work/unstaged" || die "cannot write the unstaged patch"

git clone -q --no-local --no-checkout --template= "$src" "$dest" || die "clone failed" # no shared object files
in_copy() { git -C "$dest" "$@"; }
in_copy checkout -q --detach "$head" || die "cannot check out $head"
if [ -s "$work/staged" ]; then in_copy apply --index --whitespace=nowarn "$work/staged" || die "the staged patch did not apply"; fi
if [ -s "$work/unstaged" ]; then in_copy apply --whitespace=nowarn "$work/unstaged" || die "the unstaged patch did not apply"; fi
in_copy remote remove origin || die "cannot remove the copy's remote"

# Verify: same HEAD, same trees, same raw files.
quiet
got=$(in_copy rev-parse --verify 'HEAD^{commit}') && [ "$got" = "$head" ] || die "the copy's HEAD differs"
got=$(in_copy write-tree) && [ "$got" = "$idx" ] || die "the copy's index differs"
got=$(tree_of "$dest") && [ "$got" = "$wt" ] || die "the copy's files differ (a nested repository or a moved submodule?)"
got=$(manifest "$dest") || die "cannot read the copy's raw files"
[ "$got" = "$man" ] || die "the copy's raw files differ (line endings, a content filter or core.fileMode?): $(diff <(printf '%s\n' "$got") <(printf '%s\n' "$man") | grep '^[<>]' | head -1 | cut -d' ' -f6-)"

quiet
printf '%s\n%s\n%s\n%s\n%s\n' "$head" "$idx" "$wt" "$refs" "$man" > "$dest.state" || die "cannot write the state file"
printf '%s\n' "$dest"
