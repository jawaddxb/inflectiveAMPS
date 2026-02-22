## Add AMPS Memory Export/Import Support

**What this PR does:** Adds `amps-langgraph` adapter enabling LangGraph users to export checkpoint state to [AMPS format](https://github.com/inflectiv/amps) and import from any AMPS-compatible agent framework.

### The Problem

LangGraph's `MemorySaver` stores checkpoints efficiently for graph execution, but:
- Checkpoint format is LangGraph-specific — not portable to other frameworks
- Users switching frameworks lose all accumulated conversation/task context
- No standard backup format for long-running agent state

### AMPS Integration

AMPS extracts the **narrative content** from checkpoints — the text the agent has produced and processed — which transfers meaningfully across frameworks even when graph topology doesn't.

```python
from amps.adapters.langgraph import LangGraphAdapter

# Export from MemorySaver
adapter = LangGraphAdapter(
    checkpointer=memory_saver,
    thread_id="my-agent-session",
    system_prompt="You are a DeFi research agent..."
)
doc = adapter.export()

# Import into a new graph
result = adapter.import_amps(foreign_doc)
new_graph.invoke({
    "messages": result["initial_messages"] + user_messages
})
```

### Lossiness Contract (honest)
- **Preserved:** text content from AI/human messages, system prompt as identity
- **Not portable:** state graph topology, node functions, conditional edges, tool bindings
- `migration_notes` documents all dropped fields explicitly
- Import uses `initial_messages` injection — works with all graph types without modification

### Files Changed
- `langgraph/amps_adapter.py` — ~230 lines, zero new dependencies
- `docs/memory_portability.md`

**Spec:** https://github.com/inflectiv/amps | **License:** MIT
