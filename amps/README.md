# AMPS — Agent Memory Portability Standard

**Version 1.0 | MIT License | Reference Implementation: [OpenClaw / Inflectiv Vault](https://github.com/inflectiv/vault)**

> Migrate your agent in 30 seconds.

Agent frameworks come and go. Memory should not.

AMPS is a minimal, open JSON schema for exporting and importing agent memory
across frameworks. Memory is stored as human-readable Markdown — LLM-readable,
diffable, framework-agnostic. A `.amps.json` file is a complete, portable snapshot
of an agent's intelligence.

---

## Quick Start

```python
# Export from OpenClaw / Inflectiv Vault (reference implementation)
from amps.adapters.openclaw import OpenClawAdapter
adapter = OpenClawAdapter(vault_root="/path/to/vault")
doc = adapter.export()

# Import into a new OpenClaw vault
adapter2 = OpenClawAdapter(vault_root="/new/vault")
result = adapter2.import_amps(doc)
```

```python
# Export from Agent Zero / Inflectiv Vault
from amps.adapters.agent_zero import AgentZeroAdapter
doc = AgentZeroAdapter(vault_root="/path/to/vault").export()

# Export from CrewAI
from amps.adapters.crewai import CrewAIAdapter
doc = CrewAIAdapter(agents=crew.agents, crew=crew).export()

# Import into LangGraph
from amps.adapters.langgraph import LangGraphAdapter
result = LangGraphAdapter().import_amps(doc)
new_graph.invoke({"messages": result["initial_messages"] + msgs})
```

```bash
# Validate any .amps.json file
python amps/validate.py my_agent.amps.json
```

---

## The Format

```json
{
  "amps_version": "1.0",
  "exported_at": "2026-02-22T14:34:00Z",
  "agent_id": "vlt_f145d55f",
  "source_framework": "agent_zero",
  "migration_notes": [],
  "memory": {
    "long_term":   "# What the agent knows...",
    "identity":    "# Who the agent is...",
    "active_plan": "# What it's working on..."
  },
  "secrets": [],
  "knowledge_subscriptions": ["defi_intelligence"],
  "contributions": {
    "total_items": 47, "categories": ["defi_governance"],
    "quality_score": 0.91, "network_earnings": 23.5
  }
}
```

**`secrets` is always `[]`** — credentials are never exported, by spec.

---

## Supported Frameworks

| Framework | Adapter | Lossiness | Install |
|---|---|---|---|
| OpenClaw / Inflectiv Vault | `adapters/openclaw.py` | **Lossless** | native |
| Agent Zero / Inflectiv Vault | `adapters/agent_zero.py` | **Lossless** | native |
| AutoGPT | `adapters/autogpt.py` | Best-effort | copy file |
| CrewAI | `adapters/crewai.py` | Best-effort | copy file |
| LangGraph | `adapters/langgraph.py` | Best-effort | copy file |
| LlamaIndex | `adapters/llamaindex.py` | Best-effort | copy file |

**Lossiness contract:** Lossless between AMPS-native implementations.
Best-effort for framework-specific adapters — `migration_notes` documents
everything that didn't transfer. Nothing is silently dropped.

---

## Validate

```bash
python validate.py my_agent.amps.json

  AMPS Validator v1.0
  File   : my_agent.amps.json
  Agent  : vlt_f145d55f
  Source : agent_zero
  Score  : 95/100

  ✓ Valid AMPS document (1 warning)
  ⚠  memory.active_plan is empty
```

---

## Repository Structure

```
amps/
  README.md                        This file — the spec and the docs
  AMPS_SPEC.md                     Full spec with governance
  ADOPTION_ROADMAP.md              How to drive adoption
  COMPATIBILITY_REPORT_TEMPLATE.md Monthly compatibility reports
  validate.py                      CLI validator
  schema/
    amps_v1.schema.json            JSON Schema for machine validation
  adapters/
    base.py                        Abstract base class
    openclaw.py                    Reference implementation (lossless)
    agent_zero.py                  Agent Zero adapter (lossless)
    autogpt.py                     AutoGPT adapter
    crewai.py                      CrewAI adapter
    langgraph.py                   LangGraph adapter
    llamaindex.py                  LlamaIndex adapter
  pr_templates/                    Ready-to-submit PRs for each framework
```

---

## Contributing

- **New adapter:** copy `adapters/base.py`, implement `export()` and `import_amps()`
- **Spec changes:** PR with 2-week comment period for minor versions
- **Bug reports:** open an issue with a minimal `.amps.json` that fails validation

---

## License

MIT. Use it. Fork it. Build on it.

Reference implementation: [OpenClaw / Inflectiv Vault](https://github.com/inflectiv/vault)
Spec maintained by: [OpenClaw Foundation](https://openclaw.foundation) + Inflectiv
