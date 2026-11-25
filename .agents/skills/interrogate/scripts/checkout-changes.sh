#!/usr/bin/env bash
# Report what changed in a checkout since make-copy.sh recorded STATE.
# usage: checkout-changes.sh STATE [CHECKOUT]
# It covers HEAD, refs, the index, and the raw type, bytes or link target and executable
# bit of tracked and non-ignored files. It says what changed, never who changed it, and
# restores nothing. Exit 0: no change. Exit 1: changes printed. Exit 2: could not check.

die() { echo "checkout-changes: $*" >&2; exit 2; }
is_id() { printf '%s' "$1" | grep -Eq '^[0-9a-f]{40,64}$'; }
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE
export LC_ALL=C
git() { command git -c core.hooksPath=/dev/null "$@"; } # a source hook must not change what this observes

state=${1:-}; [ -n "$state" ] && [ -r "$state" ] || die "usage: checkout-changes.sh STATE [CHECKOUT]"
src=$(git -C "${2:-.}" rev-parse --show-toplevel) && [ -n "$src" ] || die "not inside a working tree"
head0=$(sed -n 1p "$state") idx0=$(sed -n 2p "$state") wt0=$(sed -n 3p "$state")
man0=$(sed -n '/^M[ ]/p' "$state") refs0=$(sed -n '4,${/^M[ ]/d;p}' "$state")
is_id "$head0" && is_id "$idx0" && is_id "$wt0" && [ -n "$man0" ] || die "$state is not a state file"
work=$(mktemp -d) && [ -n "$work" ] || die "cannot make a temporary folder"
trap 'rm -f "$work/i" "$work/i.lock" "$work/list"; rmdir "$work" 2>/dev/null' EXIT

manifest() { # as make-copy.sh: type, raw content or link-target hash, exec bit
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

head=$(git -C "$src" rev-parse --verify 'HEAD^{commit}') && is_id "$head" || die "cannot read HEAD"
idx=$(git -C "$src" write-tree) && is_id "$idx" || die "cannot read the index tree (unmerged paths?)"
GIT_INDEX_FILE=$work/i git -C "$src" read-tree HEAD || die "cannot read HEAD's tree"
GIT_INDEX_FILE=$work/i git -C "$src" add -A -- . || die "cannot snapshot the working files"
wt=$(GIT_INDEX_FILE=$work/i git -C "$src" write-tree) && is_id "$wt" || die "cannot write the working tree"
refs=$(git -C "$src" for-each-ref) || die "cannot read the refs"
man=$(manifest "$src") || die "cannot read the raw files"
vis=$(git -C "$src" diff --cached --name-only --ita-visible-in-index) || die "cannot read the index"
inv=$(git -C "$src" diff --cached --name-only --ita-invisible-in-index) || die "cannot read the index"

changed=0
if [ "$head" != "$head0" ]; then echo "HEAD moved: $head0 -> $head"; changed=1; fi
if [ "$refs" != "$refs0" ]; then
  echo "refs changed:"; diff <(printf '%s\n' "$refs0") <(printf '%s\n' "$refs") | grep '^[<>]'; changed=1
fi
if [ "$idx" != "$idx0" ]; then
  echo "index changed:"; git -C "$src" diff --name-status --no-renames "$idx0" "$idx" || die "cannot compare the index"; changed=1
fi
if [ "$vis" != "$inv" ]; then echo "intent-to-add entries now in the index"; changed=1; fi
if [ "$wt" != "$wt0" ]; then
  echo "tree changed:"; git -C "$src" diff --name-status --no-renames "$wt0" "$wt" || die "cannot compare the files"; changed=1
fi
if [ "$man" != "$man0" ]; then
  diff <(printf '%s\n' "$man0") <(printf '%s\n' "$man") | grep '^[<>]' | cut -d' ' -f6- | sort -u | sed 's/^/file: /'; changed=1
fi
exit "$changed"
