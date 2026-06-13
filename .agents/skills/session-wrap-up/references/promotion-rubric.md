# Promotion Rubric

Use this rubric when deciding how far a wrap-up learning should propagate.

## Zones

### Green Zone

These files are safe to update directly during wrap-up:

- `.agents/skills/**`
- Scoped `*/.agents/skills/**`
- `agents_docs/agent_improvements/inbox.md`

### Yellow Zone

These files require a stronger justification and should only be updated when the pattern is clearly repeated or repo-wide:

- `AGENTS.md`
- Scoped `AGENTS.md`
- `agents_docs/roadmap/**`

Use yellow-zone updates when the improvement is genuinely durable and broad, not just a local preference from one task.

### Red Zone

Wrap-up must not modify these automatically:

- Local database volumes or training-plan data
- Secret-bearing config or `.env` files
- Git pushes, especially to `main`
- Remote vendor state

## Promotion Ladder

1. **One-off lesson**
   - Mention it only in the wrap-up report.
2. **Recurring friction, but not yet stable**
   - Add a short entry to `agents_docs/agent_improvements/inbox.md`.
3. **Stable workflow gap**
   - Update or create a skill under `.agents/skills/**` or the nearest scoped `*/.agents/skills/**`.
4. **Repo-wide rule gap**
   - Update `AGENTS.md` only if the guidance truly applies broadly.

## Commit Rule

Wrap-up may create a commit when either of these is true:

- The user explicitly asked for a commit.
- The only pending changes are wrap-up-owned files created or updated during the current pass.

Otherwise, emit a commit-message draft and stop there.
