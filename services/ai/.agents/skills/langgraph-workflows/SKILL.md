---
name: langgraph-workflows
description: Patterns for implementing LangGraph agents, state management, checkpoints, and control flow. Use when working in services/ai.
---

# LangGraph Workflow Patterns

## 1. State Schema & Reducers
- **Typed state**: Use `TypedDict` or Pydantic `BaseModel` for graph state. :contentReference[oaicite:2]{index=2}
- **Reducers are required for merge semantics**:
  - Default behavior is overwrite on update.
  - For `messages`, prefer `add_messages` so updates append *and* can overwrite existing messages by ID. :contentReference[oaicite:3]{index=3}
- **Pattern (messages state)**:
  - `messages: Annotated[list[AnyMessage], add_messages]`

## 2. Graph Construction
- **Builder**: Use `StateGraph(State)` and explicit `START`/`END` edges for the “spine”.
- **Compile**: `app = builder.compile(checkpointer=...)`
- **Separate I/O schemas (when needed)**: Define input/output schemas explicitly instead of forcing everything into one mega-state. :contentReference[oaicite:4]{index=4}

## 3. Nodes
- **Async**: Prefer `async def` nodes for uniformity (I/O, LLM calls, tools).
- **Recommended signature**:
  - `async def node(state: AgentState, config: RunnableConfig) -> dict | Command[...]`
- **State updates**:
  - Return `{"some_key": new_value}` for simple updates.
  - Use `Command(update=..., goto=...)` when the node also chooses the next hop. :contentReference[oaicite:5]{index=5}
- **Typing**:
  - Use `Command[Literal["node_a", "node_b", END]]` to declare allowed destinations. :contentReference[oaicite:6]{index=6}

## 4. Control Flow (pick the right mechanism)
- **Static edges**: Use `add_edge("a", "b")` for fixed sequencing.
- **Conditional edges**: Use `add_conditional_edges("router", router_fn, ...)` for branching based on state.
- **Command routing**: Prefer `Command(goto=...)` when routing is best decided *inside* a node (common for agent handoffs). :contentReference[oaicite:7]{index=7}
- **Fan-out / Map-Reduce**:
  - Use the **Send API** (return `Send(...)` objects from conditional routing) when the number of downstream tasks is dynamic. :contentReference[oaicite:8]{index=8}
- **Loops**:
  - Use a loop edge or `Command(goto=...)` + enforce a recursion limit in config when appropriate. :contentReference[oaicite:9]{index=9}

## 5. Tool Execution
- **ToolNode**: Use the prebuilt tool execution node for model tool-calls inside graphs. :contentReference[oaicite:10]{index=10}
- **ReAct**: For quick starts, `create_react_agent(...)` is fine; for custom flows, wire model/tool nodes yourself.

## 6. Interrupts (Human-in-the-loop)
- **Pause**: Call `interrupt(value)` inside a node to stop execution and persist state (requires a checkpointer).
- **Resume**: Re-invoke with `Command(resume=...)`; the resume value is returned back into the paused node. :contentReference[oaicite:11]{index=11}

## 7. Checkpointing & Threading
- **Dev**: `InMemorySaver` for debugging/testing. :contentReference[oaicite:12]{index=12}
- **Prod**: `PostgresSaver` / `AsyncPostgresSaver` (package: `langgraph-checkpoint-postgres`). :contentReference[oaicite:13]{index=13}
- **Configurable keys**:
  - Always pass `thread_id` when using a checkpointer. :contentReference[oaicite:14]{index=14}
  - Use `checkpoint_ns` for namespacing (multi-tenant / multi-workflow).
  - Optional: `checkpoint_id` to load a specific checkpoint (time travel / replay).

## 8. Subgraphs
- **Composition**: Use subgraphs for reusable modules.
- **Memory**: Parent checkpointer typically propagates; compile subgraphs with their own checkpointer only if they need separate internal memory. :contentReference[oaicite:15]{index=15}
