# Role of `agents_docs/`

The `agents_docs/` directory serves as the **repository of knowledge and process documentation** for the human-agent collaboration.

Unlike `AGENTS.md` (which are *active instructions* for the agent) or `.agents/skills` (which are *executable capabilities*), this folder contains **reference material**:

## Contents
1.  **Playbooks (`codex/*`)**:
    *   Instructions for working with Codex locally and in repo-maintenance flows.
2.  **Contracts (`codex/*`)**:
    *   High-level agreements on what "done" looks like, critical paths, and safety rails.
3.  **Checklists (`codex/*`)**:
    *   Standard operating procedures (SOPs) for verifying changes to the agent's own logic.
4.  **Context (`architecture/*`, `ops/*`, `product/*`)**:
    *   Background information, local ops notes, and product review templates.

## Why separate this from AGENTS.md?
*   **Token Economy**: `AGENTS.md` is read on *every* interaction. We keep it lean and instruction-focused. `agents_docs/` is read on demand.
*   **Audience**: `AGENTS.md` is for the *Agent*. `agents_docs/` is primarily for the *Team* (though the Agent can read it if asked).

## Structure

- `agents_docs/codex/`: Codex playbooks, contracts, checklists
- `agents_docs/ops/`: local operational docs and version-governance notes
- `agents_docs/architecture/`: architecture + diagrams
- `agents_docs/product/`: durable local-first product strategy notes
- `agents_docs/roadmap/`: planning docs (strategy + near-term execution)

## Planning (Start Here)

- `agents_docs/roadmap/now.md`: current focus for the next 1–2 weeks
- `agents_docs/roadmap/roadmap.md`: 3–6 month roadmap and priorities
- `agents_docs/roadmap/decision_log.md`: record of key product/ops decisions

## Current Product Direction

The current source of truth is the local-first OSS coaching app:

- `README.md` for the public setup and product promise
- `agents_docs/roadmap/now.md` for near-term execution
- `agents_docs/roadmap/roadmap.md` for durable direction
