---
name: grill-me
description: Interview the user relentlessly about a plan or design until reaching shared understanding, resolving each branch of the decision tree. Use when user wants to stress-test a plan, get grilled on their design, or mentions "grill me".
---

Interview me relentlessly about every aspect of this plan until we reach a shared understanding. Walk down each branch of the design tree, resolving dependencies between decisions one-by-one. For each question, provide your recommended answer.

Before asking the first question:

- Read the root `AGENTS.md`.
- If the likely scope is clear, read the nearest scoped `AGENTS.md` too.
- If a question can be answered by exploring the codebase, explore the codebase instead of asking.
- Identify the highest-leverage unresolved branch first so the questioning starts with the most dependency-shaping decision.

Ask the questions one at a time.

For each question:

- Ask exactly one question.
- Include your recommended answer immediately after the question.
- Briefly explain what downstream decision that answer unlocks.
- Prefer concrete tradeoffs over abstract brainstorming.

Keep going until the plan is decision-complete enough to implement or until the remaining uncertainty is genuinely external to the repo.
