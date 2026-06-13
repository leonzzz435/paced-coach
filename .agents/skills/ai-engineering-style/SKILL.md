---
alwaysApply: true
---

# Modern AI Engineering: Design Principles

**Scope:** Universal principles for building production LLM-powered systems.
Framework-agnostic — applies whether you use LangGraph, LangChain, CrewAI, Semantic Kernel, or raw orchestration.

---

## I. Agent Design

### 1. Agents Are Self-Contained Reasoning Units

An agent receives context, reasons, and produces a complete result. Its output should never require post-processing by the orchestrator to be meaningful.

**Test:** Can you unit-test this agent in isolation, without the rest of the pipeline, and verify its output is correct? If not, its boundary is incomplete.

### 2. Deterministic Shell, Stochastic Core

Separate what the LLM decides from what code enforces. The LLM interprets, classifies, and extracts. Deterministic code validates, resolves identifiers, enforces schemas, and applies business rules.

**Anti-pattern:** Letting the LLM generate identifiers, compute scores, or enforce constraints it wasn't trained for. If a lookup table or a validation rule can do it, don't ask the model.

### 3. Narrow Agent Scope

Each agent should do one thing well. Prefer multiple focused agents over a single omniscient one. A classification agent classifies. An extraction agent extracts. A validation agent validates.

**Why:** Narrow scope means targeted prompts, easier evaluation, independent improvement, and cheaper model selection per task (not everything needs GPT-4).

### 4. Configuration-Driven Behavior

Agent behavior (prompts, matching criteria, fallback strategies, required/optional status) should be driven by **configuration objects**, not by code branches. Adding a new agent variant should require a new config entry, not a new class or code path.

**Test:** Can a domain expert add a new agent variant by editing configuration alone? If it requires a code change in the orchestrator, the abstraction is wrong.

---

## II. Orchestration

### 5. Declarative Topology Over Procedural Code

Express workflow behavior as **structure** (nodes, edges, DAGs), not as procedural logic inside handler functions. The graph should be readable as a blueprint of what happens.

**Anti-pattern:** A "god node" that internally dispatches to multiple agents, manages parallelism, and aggregates results. That's a workflow engine inside a node — use the actual workflow engine.

### 6. Topology Encodes Execution Policy

Whether an agent runs unconditionally, conditionally, or optionally should be visible in the **graph structure**, not buried in handler code.

**Why:** When policy is declared in topology, anyone (including LLMs assisting with the code) can understand the system's behavior by looking at the graph. When it's hidden in procedural logic, understanding requires reading every code path.

### 7. Orchestrator Ignorance

The orchestrator routes and assembles. It never understands what agents do internally. It doesn't know about domain-specific fallbacks, identifier resolution, confidence computation, or business rules.

**Test:** If you swap one agent implementation for another with the same interface, does the orchestrator require any changes? If yes, the orchestrator knows too much.

### 8. Pure Aggregation

The final assembly step (combining agent outputs into an API response) must be a **projection** — mapping, filtering, and formatting. Never transformation, enrichment, or business logic.

**Why:** If the assembler transforms data, you've split agent logic across two locations. Bugs become non-local, testing requires integration, and changes cascade.

---

## III. Signals & Observability

### 9. Each Stage Owns Its Signals

When multiple agents contribute to a result, each agent's metadata (confidence, quality, reasoning) must originate from **that agent alone**. Never derive one agent's signals from another's output.

**Why:** Independent signals are the foundation of evaluation, calibration, and debugging. If you mix them, you cannot determine which stage is underperforming, and threshold tuning becomes meaningless.

**Corollary:** If an upstream signal is absent, use a neutral default. Do not synthesize it from downstream results.

### 10. Observability Is Not Optional

Every LLM call, every routing decision, every agent output must be traceable. Design for observability from day one — not as an afterthought.

- Structured logging at every decision point
- Trace IDs that follow a request through all agents
- LLM inputs and outputs captured for replay and evaluation
- Agent reasoning exposed (not just final values)

**Why:** LLM systems are non-deterministic. Without observability, debugging is guesswork. The first thing you'll do when something goes wrong is look at traces — make sure they're there.

### 11. Evaluation-Driven Development

Every agent should have an independent evaluation metric. If you can't measure an agent's quality in isolation, you can't improve it in isolation.

- Classification agents: precision/recall on routing decisions
- Extraction agents: accuracy against ground truth
- End-to-end: composite metrics, but never as the only metric

**Anti-pattern:** Only measuring end-to-end accuracy. When it drops, you have no idea which agent regressed.

---

## IV. Data Contracts

### 12. Schema as Contract

The interface between agents is a **typed schema** (Pydantic, JSON Schema, protobuf), never a raw dict, untyped string, or implicit convention.

**Why:** Schemas are self-documenting, validatable at runtime, and generate API docs automatically. They catch integration errors at the boundary, not deep inside agent logic.

### 13. Fail at the Boundary

Validate inputs at the edge of each agent, not deep inside processing logic. If an agent receives invalid input, it should fail immediately and clearly — not silently produce garbage.

**Anti-pattern:** An agent that accepts any input shape and tries to "make it work" with defensive coding. This hides upstream bugs and makes debugging impossible.

---

## V. Reliability

### 14. Graceful Degradation by Design

Every agent should have a defined behavior for: no LLM response, low-confidence response, timeout, malformed output. This should be explicit in configuration, not implicit in exception handlers.

- Required agents: apply fallback values
- Optional agents: return empty/skip
- All agents: structured error reporting, never silent failures

### 15. Idempotent Structure, Stochastic Content

Agent outputs should have a **deterministic structure** even though LLM content varies. The schema, field presence, and types are always the same. Only the values inside may differ between runs.

**Why:** Downstream consumers (other agents, APIs, UIs) depend on structural guarantees. If the output shape changes based on LLM mood, every consumer needs defensive parsing.

### 16. Retry at the Right Layer

LLM call retries belong at the **agent level**, not the orchestrator level. The agent knows whether a retry makes sense (transient error vs. malformed prompt). The orchestrator doesn't.

**Anti-pattern:** The orchestrator catching LLM errors and retrying the entire workflow. This wastes tokens on agents that already succeeded and conflates transient failures with logic errors.
