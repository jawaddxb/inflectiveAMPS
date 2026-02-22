## Add AMPS Memory Portability Support

**What this PR does:** Adds `amps-crewai` adapter — one file, MIT licensed — enabling CrewAI users to export agent memory/knowledge to [AMPS format](https://github.com/inflectiv/amps) and import from Agent Zero, AutoGPT, LangGraph, and LlamaIndex.

### The Problem This Solves

CrewAI agents accumulate valuable context through task execution. Currently:
- That context is trapped in the crew's runtime state
- Framework migrations wipe all accumulated knowledge
- No standard way to persist agent identity (backstory/goals) across runs

### What AMPS Provides

[AMPS](https://github.com/inflectiv/amps) is an MIT-licensed open standard for agent memory interchange. Memory stored as plain Markdown — readable by humans, LLMs, and any framework.

### Usage

```python
from amps.adapters.crewai import CrewAIAdapter

# Export from a live crew
adapter = CrewAIAdapter(agents=my_crew.agents, crew=my_crew)
doc = adapter.export()

# Import into a new CrewAI agent
result = adapter.import_amps(foreign_amps_doc)

# Apply to agent
new_agent = Agent(
    role="DeFi Researcher",
    backstory=result["backstory_extension"] + original_backstory,
    memory=result["agent_memory"]
)
```

### What Transfers
- Agent `backstory`, `role`, `goal` → `memory.identity`
- Task output history → `memory.long_term`
- Tool bindings preserved in `migration_notes` (not portable, but not silently dropped)

### Files Changed
- `crewai/amps_adapter.py` — ~220 lines, zero new dependencies
- `docs/memory_portability.md`

**Full spec & all adapters:** https://github.com/inflectiv/amps  
**License:** MIT
