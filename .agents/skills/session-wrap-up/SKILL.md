---
name: session-wrap-up
description: Close out a coding session, summarize the work, extract repeated corrections, and promote durable improvements into safe source-of-truth files for Codex.
---

# Session Wrap-Up

Use this skill when the user asks to wrap up a coding session, prepare a handoff, summarize work, extract repeated corrections, improve the agent workflow, or prepare a safe commit.

## Inputs to read

- The current chat
- `git status --short`
- The relevant diff (`git diff --stat` plus targeted diffs as needed)
- [`AGENTS.md`](../../../AGENTS.md)
- [`references/promotion-rubric.md`](references/promotion-rubric.md)
- [`agents_docs/agent_improvements/inbox.md`](../../../agents_docs/agent_improvements/inbox.md) when deciding whether a learning should be promoted or parked

## Modes

- **Default**: report + propose
- **Apply**: may update safe-zone source files directly
- **Commit**: may commit only when explicitly asked or when the only pending changes are wrap-up-owned files created in this pass

## Workflow

1. **Inspect worktree ownership**
   - Separate active feature work from wrap-up-owned improvements.
   - Identify unrelated user changes and leave them alone.
   - Never revert, reformat, or absorb unrelated changes just to make wrap-up easier.
2. **Produce a closeout report**
   - Work summary
   - Verification status
   - Open risks / unresolved items
   - Repeated corrections or friction discovered during the session
   - Promotion candidates
   - Draft commit message
   - Next-session handoff
3. **Promote learnings using the rubric**
   - Shared workflow improvements belong in `.agents/skills/**` or the nearest scoped `*/.agents/skills/**`
   - Unresolved recurring ideas can be appended to `agents_docs/agent_improvements/inbox.md`
   - Repo-wide instructions in `AGENTS.md` are acceptable only for clear repeated guidance gaps, not one-off annoyances
4. **Apply safely**
   - Update the live `.agents/**` file directly when it is the source of truth
   - Never push or touch red-zone paths during wrap-up
5. **Commit or handoff**
   - If commit ownership is unclear, produce a commit message draft instead of forcing a commit
   - If committing, include only files the current wrap-up pass actually owns
   - Always mention whether the result is report-only, proposed, applied, or committed

## Output bar

- Keep the report concrete and operational
- Reference exact files and commands
- Say explicitly when no durable learning exists
- Prefer a short precise handoff over a long narrative
