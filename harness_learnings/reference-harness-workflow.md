# Reference Harness Workflow

Use this workflow when adding a new repo under `reference_harnesses/` and syncing it as a Git submodule.

## Add a New Reference Repo

From the repo root:

```bash
git submodule add <repo-url> reference_harnesses/<repo-name>
git add .gitmodules reference_harnesses/<repo-name>
git commit -m "chore: add <repo-name> reference harness"
```

If the folder already exists as a local clone:

```bash
git submodule add --force <repo-url> reference_harnesses/<repo-name>
git submodule absorbgitdirs -- reference_harnesses/<repo-name>
git add .gitmodules reference_harnesses/<repo-name>
git commit -m "chore: track <repo-name> as submodule"
```

## Update Existing Reference Repos

Update one repo:

```bash
git -C reference_harnesses/<repo-name> fetch
git -C reference_harnesses/<repo-name> pull
git add reference_harnesses/<repo-name>
git commit -m "chore: update <repo-name> reference harness"
```

Update all submodules:

```bash
git submodule update --init --recursive
git submodule update --remote --merge
git add reference_harnesses
git commit -m "chore: update reference harness submodules"
```

## Inspect Submodule State

```bash
git submodule status
git diff --submodule
git -C reference_harnesses/<repo-name> status
```

The parent repo tracks the pinned submodule commit, not the full internal file diff.

## Refresh Local Learnings And Harness

After adding or updating a reference repo, run:

```text
Use $refresh-harness-from-reference to evaluate reference_harnesses/<repo-name> and selectively update harness_learnings plus project_agnostic_claude_setup.
```

Expected behavior:

- compare the new repo against the existing reference repos
- update `harness_learnings/` only where the new repo adds a better durable pattern
- update `project_agnostic_claude_setup/` only where the smallest useful improvement is clear
- reject heavier, narrower, or repo-specific patterns

## Borrowing Rule

Always prefer the smallest durable improvement.

Do not import:
- giant catalogs
- install instructions
- local paths
- org-specific assumptions
- whole workflows when a smaller pattern is enough
