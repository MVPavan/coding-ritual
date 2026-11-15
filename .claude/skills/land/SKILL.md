---
name: land
description: "Use when verified work should become commits: split, order and title them, and commit only with authority. Skip pushing, merging and pull requests, and a merge already in conflict."
---

# Land

Turn verified changes into small ordered commits with conventional titles. The
deliverable is those commits or, without commit authority, the commit plan.

Run this on finished work only: a path that stopped, or whose verification is
incomplete, lands nothing. Unmerged paths in the tree belong to
`resolving-merge-conflicts`.

## 1. Confirm the work is verified

Check that your evidence covers the final form of every path you would land. If a
closeout or any later edit changed executable content after the last check, rerun
the behaviour check first. If the final form is still unverified, refuse: commit
nothing, plan nothing, and report the gap and the check that would close it.

## 2. Partition the tree

Read `git status --short` and the diff. Assign to commits only the paths this task
changed. Leave every other change in the tree as it is and name each one in your
report, including any path you cannot attribute.

If one file holds changes for two commits, say so and commit them together, because
interactive staging is unavailable.

## 3. Split and order

Size and order the commits by `principle-sequence-verifiable-units`. Work from
uncommitted changes; existing commits stay as they are unless the request names a
reorder.

## 4. Title and body

Title each commit `type(scope): subject`:

- `type` is `feat`, `fix`, `docs`, `refactor`, `test`, `chore` or `perf`, and `scope` is the area changed.
- The subject is imperative, has no trailing period and names the real symbol that carries the change.

A body says what the subject cannot and never restates it. Leave the body out when
the subject says everything.

## 5. Commit or plan

Being called by a playbook grants no commit authority; check for it separately.

- **With authority:** make the commits in order, then read `git log` and
  `git status --short` to confirm each commit holds its assigned paths and every
  other change is untouched. Report the commits and the changes you left.
- **Without authority:** stage nothing. Report the ordered commits, each with its
  paths, title and body, and the changes you left.
