#!/bin/bash
# PreToolUse(Bash) guard. Blocks destructive commands and asks the user first.
# Covers: git working-tree/history destroyers, --no-verify, beads store re-init,
# recursive removes (rm -r / rm -rf) targeting anything outside /tmp, and
# shell writes to bd-generated workstream mirrors.
set -euo pipefail

INPUT=$(cat)

if command -v jq >/dev/null 2>&1; then
  COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
else
  COMMAND=$(echo "$INPUT" | grep -o '"command":"[^"]*"' | sed 's/"command":"//;s/"$//')
fi

[ -z "${COMMAND:-}" ] && exit 0

# Fixed-string dangerous patterns (git working-tree / history destroyers).
DANGEROUS_PATTERNS=(
  "git push --force"
  "git push -f"
  "git reset --hard"
  "git clean -fd"
  "git clean -f"
  "git branch -D"
  "git checkout ."
  "git restore ."
  "--no-verify"
)

for pattern in "${DANGEROUS_PATTERNS[@]}"; do
  if [[ $COMMAND == *"$pattern"* ]]; then
    echo "BLOCKED: '$COMMAND' matches dangerous pattern '$pattern'. Ask the user before proceeding." >&2
    exit 2
  fi
done

# Beads store re-initialization. `bd init --force` (deprecated alias for --reinit-local) and
# `--reinit-local` bypass bd's local data-safety guard and WIPE the Dolt store; recovery would then
# depend entirely on the committed .beads/issues.jsonl mirror. Block any `bd ... init` that carries a
# force/reinit flag (order-independent), and ask the user first.
# The checks below feed grep a here-string, never `echo | grep -q`: grep -q stops reading at the
# first match, and under pipefail the writer's SIGPIPE would turn that match into a pass.
if grep -qE '\bbd\b' <<<"$COMMAND" 2>/dev/null \
   && grep -qE '\binit\b' <<<"$COMMAND" 2>/dev/null \
   && grep -qE -- '--force|--reinit' <<<"$COMMAND" 2>/dev/null; then
  echo "BLOCKED: '$COMMAND' re-initializes the beads store (wipes the Dolt DB; recovery would depend on the committed .beads/issues.jsonl mirror). Ask the user before proceeding." >&2
  exit 2
fi

# Recursive remove outside /tmp. Any `rm -r`/`-R`/`--recursive` (with or without -f, any flag
# spelling) is destructive, so allow it only when EVERY target is under /tmp/. If a target lives
# elsewhere — or can't be proven /tmp-only (globs, quotes, command substitution, redirections) —
# block and ask the user to review. Detection is scoped per-rm-segment so an unrelated -r elsewhere
# on the line can't trip it. (Non-recursive `rm -f`/`rm <file>` is not covered — no tree deletion.)
__rm_is_recursive() { grep -qE -- '(^|[[:space:]])-[A-Za-z]*[rR]' <<<"$1" || grep -qiF -- '--recursive' <<<"$1"; }

while IFS= read -r SEG; do
  [ -z "${SEG:-}" ] && continue
  __rm_is_recursive "$SEG" || continue
  found_target=0; unsafe=0
  set -f; set -- $SEG; set +f                  # word-split the segment WITHOUT glob expansion
  for tok in "$@"; do
    [ "$tok" = "rm" ] && continue
    case "$tok" in -*) continue ;; esac         # a flag, not a target
    found_target=1
    case "$tok" in
      /tmp/*) case "$tok" in *..*) unsafe=1 ;; esac ;;   # under /tmp, but reject path-escape (..)
      *) unsafe=1 ;;                             # anything not under /tmp
    esac
  done
  if [ "$found_target" = 0 ] || [ "$unsafe" = 1 ]; then
    echo "BLOCKED: '$COMMAND' is a recursive remove (rm -r/-rf) with a target outside /tmp (or one that can't be proven /tmp-only). Review with the user before proceeding — only recursive rm under /tmp/ runs without confirmation." >&2
    exit 2
  fi
done <<EOF
$(grep -oE '(^|[[:space:]])rm[[:space:]]+[^;&|<>]*' <<<"$COMMAND" || true)
EOF

# bd-generated tracking mirrors. The per-workstream tracking trio and the cross-cutting board under
# docs/workstreams/ are read-only projections of Beads. The sanctioned writer is a project renderer
# invoked with BD_RENDER=1. Block direct shell-redirect / tee / in-place-sed writes unless that
# whitelist token is present in the command.
GEN_PATH_RE='docs/workstreams/([^|;]*/tracking/[^/[:space:]]*\.md|(status|ideas|backlog)\.md)'
if ! grep -qF 'BD_RENDER=1' <<<"$COMMAND" 2>/dev/null \
   && grep -qE "(>>?|[[:space:]]tee[[:space:]]|sed[[:space:]]+-i)[^|;]*$GEN_PATH_RE" <<<"$COMMAND" 2>/dev/null; then
  echo "BLOCKED: '$COMMAND' writes to a bd-generated workstream mirror. Update bd, then regenerate the mirror with the project renderer (run with BD_RENDER=1). Do not hand-edit generated mirrors." >&2
  exit 2
fi

# Git global options may sit between `git` and its subcommand (`git -C <dir> push --force`,
# `git -c k=v --no-pager reset --hard`). This check runs last, after the cheap checks above. A Python
# program reads the command on stdin and splits it into shell words with shlex (never evaluating it).
# An unquoted `#` at the start of a word begins a comment up to the end of the line, as in the shell.
# Every unquoted word `git` or `*/git` starts a git command; its global options are skipped (those git
# takes with a separate argument consume it; any other `-...` word is one option; one that makes git
# print and exit ends the command). The subcommand and the words right after it are compared with the
# git patterns above, word by word (the last word may be a prefix, so `-f` matches `-fd`), up to the
# next shell operator. It prints the matched pattern or nothing. Quoted text such as a commit message
# or a filename stays one word, so it never starts a command or joins with another word into a match.
# Parsing has a time budget of 2 seconds (SIGALRM, POSIX), because shlex is slow on one very long
# word; running out of it (exit 4) blocks.
# Limits: when python3 is missing, or the text does not tokenize (an unbalanced quote, and also shell
# text shlex does not read: heredocs, ANSI-C $'...' quoting; exit 3), only the substring check above
# runs, so global options can still hide a pattern there. Any other Python failure blocks.
read -r -d '' GIT_MATCH_PY <<'PY' || true
import io, re, shlex, signal, sys
if hasattr(signal, "SIGALRM"):  # no SIGALRM (Windows): parse without a budget rather than block every git call
    signal.signal(signal.SIGALRM, lambda *_: sys.exit(4))
    signal.alarm(2)
text = re.sub(r"(?<!\\)((?:\\\\)*)\\\n", r"\1", sys.stdin.read())
ops = "();<>|&`\n"
class Source(io.StringIO):
    # Skips a comment: an unquoted `#` read between words or right after an operator.
    comment_end = 0
    def read(self, size=-1):
        c = super().read(size)
        if c == "#" and lex.state in (" ", "c"):
            i = text.find("\n", self.tell())
            self.comment_end = i if i >= 0 else len(text)
            self.seek(self.comment_end)
            c = super().read(size)
        return c
src = Source(text)
lex = shlex.shlex(src, posix=True, punctuation_chars=ops)
lex.whitespace, lex.whitespace_split, lex.commenters = " \t\r", True, ""
words, start = [], 0
try:
    for tok in lex:
        end = src.tell()
        seg = text[max(start, src.comment_end):end]
        words.append((tok, not any(c in seg for c in "'\"\\")))
        start = end
except ValueError:
    sys.exit(3)
patterns = [p.split(" ") for p in sys.argv[1:]]
takes_arg = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--attr-source",
             "--config-env", "--shallow-file"}
exits = {"-v", "--version", "-h", "--help", "--exec-path", "--html-path", "--man-path",
         "--info-path"}
def stop(word):
    return word[1] and all(c in ops for c in word[0])
# sub[j]: index of the subcommand when global options are skipped from word j; -1 if git exits.
n = len(words)
sub = [n] * (n + 1)
for j in range(n - 1, -1, -1):
    tok = words[j][0]
    if stop(words[j]) or not tok.startswith("-"):
        sub[j] = j
    elif tok in exits:
        sub[j] = -1
    else:
        sub[j] = sub[min(j + (2 if tok in takes_arg else 1), n)]
for i, (tok, bare) in enumerate(words):
    if not bare or not (tok == "git" or tok.endswith("/git")):
        continue
    j = sub[i + 1]
    for p in patterns if j >= 0 else []:
        got = words[j:j + len(p)]
        if (len(got) == len(p) and not any(stop(w) for w in got)
                and all(w[0] == t for w, t in zip(got[:-1], p)) and got[-1][0].startswith(p[-1])):
            print("git " + " ".join(p))
            sys.exit(0)
PY
case "$COMMAND" in
  *git*)
    if command -v python3 >/dev/null 2>&1; then
      GIT_PATTERNS=()
      for pattern in "${DANGEROUS_PATTERNS[@]}"; do
        if [[ $pattern == "git "* ]]; then GIT_PATTERNS+=("${pattern#git }"); fi
      done
      rc=0
      MATCH=$(python3 -I -S -c "$GIT_MATCH_PY" "${GIT_PATTERNS[@]}" <<<"$COMMAND" 2>/dev/null) || rc=$?
      if [ "$rc" = 0 ] && [ -n "$MATCH" ]; then
        echo "BLOCKED: '$COMMAND' runs dangerous pattern '$MATCH' (after git global options). Ask the user before proceeding." >&2
        exit 2
      elif [ "$rc" = 4 ]; then
        echo "BLOCKED: the command is too large to check (the guard's parse ran out of time). Put large content in a file with the file tool (Write/Edit), then run a short command, or ask the user before proceeding." >&2
        exit 2
      elif [ "$rc" != 0 ] && [ "$rc" != 3 ]; then
        echo "BLOCKED: '$COMMAND' could not be checked: the guard could not parse the command (python3 exit $rc). Ask the user before proceeding." >&2
        exit 2
      fi
    fi ;;
esac

exit 0
