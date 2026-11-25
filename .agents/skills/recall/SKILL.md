---
name: recall
description: "Rebuild recent work in this project from past chats and the shared record (beads, commits) into one brief of where things stand and the next move. Use for /recall; resuming one known piece of work is session-pickup."
disable-model-invocation: true
argument-hint: "Topic, window or 'everything' (default: this workspace, last 7 days)"
---

# Recall

Before work starts or resumes, rebuild where the recent work stands and what
comes next, as one short brief.

The context lives in two records, and recall needs both. Past chats hold what
was done and decided. The shared record holds what happened around the same work
under other names: Beads (search, notes, in-progress and recently closed beads),
git (log, branches, recent merges and reverts), the workstream state files and
docs a bead or `.repo-context/docs-index.md` names, and any issue thread, team
chat or error report the record links to.

## Steps

1. **Route.** First rule out three other tasks and hand each back to the router
   without mining: resuming one known piece of work (`session-pickup`), turning
   habits into a durable skill, and writing a summary of the work for a person to
   read. If the person already gave the state (paths, branch, the change), use it
   as given and do no mining.
2. **Lock the scope** before any search: the window ("recent" is a real range,
   default the last 7 days), the topic if one is named, and the workspace (default
   this one; read another project's chats only when asked). State the scope back.
   Never narrow "all" or "everything" to a recent subset without saying so.
3. **Mine the chats.** Read `references/chat-logs.md` for where they are. Order
   candidates newest first by real modification time, never by file name. Search
   for the topic first, then read only the matching chats and only their matching
   regions. Skip the current chat and helper, eval and test chats. For one or two
   chats, search them yourself; for more, hand slices to helpers through
   `delegation`. Each chat gets one block in one schema: topic, the person's goal,
   decisions, open threads, struggles and corrections, artifacts (beads, branches,
   commits, pull requests), citing the chat by session id. Where the answer turns
   on what an agent actually did (the tools it ran, the files it read, the errors
   it hit), read its full log, not a trimmed copy.
4. **Sweep the shared record** whenever the topic names a feature, file,
   subsystem, area or bug; "my work on X" does not exempt it. Skip it only for
   activity recall with no named target ("what did I do this week"). Give a source
   its own helper through `delegation` only when its investigation is sizeable and
   independent; read small sources yourself, in one pass where one pass covers
   them. Ask each source for the current state, failed attempts and open reports,
   not for design rationale. A search that finds nothing is a finding: report it.
   List every source as searched, empty or unavailable, with the reason; an
   unavailable source is a gap in coverage, never an empty result.
5. **Write the brief** to the contract below.

## Output contract

Group the brief by thread and stay on the named topic. Lead with the capsule,
then the threads, then the problems, then the next move; deeper detail goes after
the problems, before the next move, or is cut.

- **Capsule.** At most 5 bullets: what this work is and where it stands overall.
- **Threads.** Give each thread one line with one tag: merged, open pull request,
  in flight, verified uncommitted, reverted, abandoned or planned; a state none of
  these fits is said in plain words.
- **Problems.** At most 5, the recurring ones, including symptoms people keep
  reporting and fixes that failed or were reverted, so the next attempt starts
  where the last one failed.
- **Coverage.** The source list from step 4.
- **Next move.** The single most useful next action, concrete. The brief ends
  on this line.

Leave out adjacent work unless it blocks this one. When the brief outgrows one
screen, cut detail before cutting threads. Cite every finding by its source
kind: a chat by session id; a shared-record finding by its bead id, pull request
or issue number, message permalink or error-tracker issue where the record holds
one, otherwise by its commit or `path:line`.

Reply with the brief itself.
