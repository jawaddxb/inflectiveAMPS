## Add AMPS Memory Export/Import Support

**What this PR does:** Adds `amps-autogpt` adapter — one file, 200 lines, MIT licensed — enabling AutoGPT users to export their agent memory to the [AMPS (Agent Memory Portability Standard)](https://github.com/inflectiv/amps) format and import from any AMPS-compatible framework.

### The Problem This Solves

Your issues tracker has multiple open requests for memory export/portability:
- Users want to switch frameworks without losing their agent's trained knowledge
- No current answer to "how do I backup my agent's memory?"
- Migration from AutoGPT → other frameworks loses all accumulated context

### What AMPS Provides

AMPS is a minimal open standard (MIT, JSON + Markdown) for agent memory interchange:
```json
{
  "amps_version": "1.0",
  "memory": {
    "long_term":   "# What the agent knows...",
    "identity":    "# Who the agent is...",
    "active_plan": "# What it's doing..."
  },
  "secrets": [],
  "contributions": { "total_items": 847 }
}
```
Secrets are **never exported** (empty array by spec). Memory is plain Markdown — human-readable, LLM-readable, diffable.

### Usage (drop-in, no new dependencies)

```python
from amps.adapters.autogpt import AutoGPTAdapter

# Export
adapter = AutoGPTAdapter(workspace_dir="/path/to/workspace")
doc = adapter.export()
with open("my_agent.amps.json", "w") as f:
    json.dump(doc, f, indent=2)

# Import from another framework
result = adapter.import_amps(foreign_doc)
print(result["applied"])     # what was written
print(result["migration_notes"])  # what didn't transfer
```

### Lossiness Contract
- **Preserved:** memory summaries, agent role/goals as identity
- **Not portable:** tool configs, plugin state, command history
- `migration_notes` field documents exactly what was dropped — no silent data loss

### Files Changed
- `autogpt/amps_adapter.py` — 200 lines, zero new dependencies
- `docs/memory_portability.md` — usage guide

**Reference implementation:** [OpenClaw / Inflectiv Vault](https://github.com/inflectiv/vault) (native, lossless)
**Full spec:** [AMPS_SPEC.md](https://github.com/inflectiv/amps/blob/main/AMPS_SPEC.md)  
**License:** MIT
