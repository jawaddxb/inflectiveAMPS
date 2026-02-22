# Agent Memory Portability Standard (AMPS)
## Version 1.0 — Open Standard

**License:** MIT  
**Maintainer:** Inflectiv / OpenClaw Foundation  
**Status:** Draft — February 2026  
**Reference Implementation:** OpenClaw / Inflectiv Vault

---

## Executive Summary

Agent frameworks come and go. Memory should not.

AMPS is a minimal, open JSON schema for exporting and importing agent memory
across frameworks. Memory is stored as human-readable Markdown — LLM-readable,
diffable, and framework-agnostic. A `.amps.json` file is a complete, portable
snapshot of an agent's intelligence: what it knows, who it is, what it is doing,
and what it has contributed to the network.

**Lossiness contract:**
- Between AMPS-native implementations (OpenClaw, Agent Zero): **lossless**
- For framework-specific imports: **best-effort** — adapters preserve as much
  as possible and write `migration_notes` for anything that doesn't map cleanly

This is a massive improvement over the current baseline of zero portability.

---

## 1. Schema

### 1.1 Full Schema

```json
{
  "amps_version": "1.0",
  "exported_at": "<ISO 8601 timestamp>",
  "agent_id": "<framework-specific unique ID>",
  "source_framework": "<see §1.3>",

  "migration_notes": [
    "<human-readable note about data that did not map cleanly>"
  ],

  "memory": {
    "long_term":   "<Markdown — persistent knowledge, facts, preferences>",
    "identity":    "<Markdown — agent personality, values, operating principles>",
    "active_plan": "<Markdown — current tasks, goals, WIP>"
  },

  "secrets": [],

  "knowledge_subscriptions": [
    "<vault name or URL — pointer only, never vault contents>"
  ],

  "contributions": {
    "total_items":         0,
    "categories":          [],
    "quality_score":       0.0,
    "network_earnings":    0.0,
    "first_contribution": null,
    "last_contribution":  null
  }
}
```

### 1.2 Field Definitions

| Field | Req | Type | Description |
|---|---|---|---|
| `amps_version` | ✅ | string | Schema version. Current: `"1.0"` |
| `exported_at` | ✅ | ISO 8601 | Export timestamp |
| `agent_id` | ✅ | string | Framework-specific agent/vault ID |
| `source_framework` | ✅ | string | Originating framework (see §1.3) |
| `migration_notes` | ✅ | string[] | Notes on data that didn't map cleanly. `[]` for clean exports |
| `memory.long_term` | ✅ | Markdown | Persistent knowledge, facts, learned context |
| `memory.identity` | ✅ | Markdown | Agent personality, values, operating style |
| `memory.active_plan` | ⬜ | Markdown\|null | Current tasks and goals. Note: non-native adapters rarely populate this field |
| `secrets` | ✅ | always `[]` | Credentials are **never exported** — field exists to make omission explicit |
| `knowledge_subscriptions` | ⬜ | string[] | Vault names/URLs agent was subscribed to. Pointer only |
| `contributions` | ✅ | object | Contribution history (required; initialized by `empty_amps()`) |
| `contributions.total_items` | ⬜ | int | Total approved contributions to the network |
| `contributions.categories` | ⬜ | string[] | Category labels (e.g. `defi_governance`) |
| `contributions.quality_score` | ⬜ | float 0–1 | Mean quality score across contributions |
| `contributions.network_earnings` | ⬜ | float | Cumulative network earnings (unit defined by implementation) |
| `contributions.first_contribution` | ⬜ | ISO 8601\|null | First contribution timestamp |
| `contributions.last_contribution` | ⬜ | ISO 8601\|null | Most recent contribution timestamp |

### 1.3 Known Source Frameworks

| `source_framework` | Framework |
|---|---|
| `openclaw` | OpenClaw / Inflectiv Vault (native, lossless — reference implementation) |
| `agent_zero` | Agent Zero / Inflectiv Vault (lossless) |
| `autogpt` | AutoGPT |
| `crewai` | CrewAI |
| `langgraph` | LangGraph |
| `llamaindex` | LlamaIndex |
| `custom` | Any other framework |

---

## 2. Behaviour Contract

### 2.1 Export Rules
1. `secrets` MUST always be `[]`. Credentials are never exported.
2. `knowledge_subscriptions` are pointers only — never vault contents.
3. `migration_notes` MUST contain an entry for every piece of data discarded or transformed.
4. `memory.*` fields MUST be Markdown strings or `null`. Never binary, never JSON.
5. `contributions` MUST be included. Exporters MUST populate at minimum the skeleton from `empty_amps()`.

### 2.2 Import Rules
1. Importers MUST surface all `migration_notes` to the user — never silently discard.
2. Importers MUST NOT attempt to populate `secrets`. Always empty on import.
3. `knowledge_subscriptions` SHOULD be offered to the user for restoration — never auto-subscribed.
4. `contributions` SHOULD be preserved in the destination vault's stats.
5. Unknown `amps_version` MUST warn the user and MAY proceed with best-effort interpretation.

### 2.3 Conflict Resolution on Import
- Existing `long_term` and `identity` take priority by default
- Imported content appended with `## Imported from <source_framework>` heading
- Implementations MAY offer `--overwrite` flag
- Importers SHOULD warn the user if combined memory (existing + imported) exceeds 50 KB after append

---

## 3. Framework Adapters

### 3.1 OpenClaw / Inflectiv Vault (Native — Reference Implementation)
- **Export:** `MEMORY.md` → `long_term`, `SOUL.md` → `identity`, `task_plan.md` → `active_plan`
- **Import:** Markdown sections appended to respective files
- **Contributions:** Read from `stats.json` approved/staged counts + categories
- **Lossiness:** None.

### 3.2 Agent Zero / Inflectiv Vault (Lossless)
- **Export:** `MEMORY.md` → `long_term`, `SOUL.md` → `identity`, `task_plan.md` → `active_plan`
- **Import:** Markdown sections appended to respective files
- **Contributions:** Read from `stats.json` approved/staged counts + categories
- **Lossiness:** None.

### 3.3 AutoGPT
- **Export:** `memory.json` summaries → `long_term`, agent role/goals → `identity`
- **Import:** Prepend to AutoGPT's `memory.json` as text summary entry
- **Migration notes:** Tool configs, plugin state — preserved as raw JSON in notes
- **Limitation:** `active_plan` is not extracted — AutoGPT has no equivalent source

### 3.4 CrewAI
- **Export:** Agent `backstory` → `identity`, task output history → `long_term`
- **Import:** Prepend AMPS `long_term` to agent `backstory` field
- **Migration notes:** Crew topology, task dependencies — noted, not portable
- **Limitation:** `active_plan` is not extracted — CrewAI has no equivalent source

### 3.5 LangGraph
- **Export:** `MemorySaver` checkpoint text nodes → `long_term`
- **Import:** Inject as initial `HumanMessage` context in new graph
- **Migration notes:** State graph topology, tool bindings — noted
- **Limitation:** `active_plan` is not extracted — LangGraph checkpoints do not distinguish plan state

### 3.6 LlamaIndex
- **Export:** `SimpleDocumentStore` text nodes → `long_term`
- **Import:** Add as `Document` nodes with `amps_import` metadata tag
- **Migration notes:** Index structure — noted
- **Limitation:** `active_plan` is not extracted — LlamaIndex document stores have no plan concept


---

## 4. Example: Clean Agent Zero Export

```json
{
  "amps_version": "1.0",
  "exported_at": "2026-02-22T14:34:00Z",
  "agent_id": "vlt_f145d55f6e1d4810",
  "source_framework": "agent_zero",
  "migration_notes": [],
  "memory": {
    "long_term": "# Memory\nAave V4 governance: proposal #247 passed 72%.\n",
    "identity":  "# Identity\nI am a DeFi intelligence node.\n",
    "active_plan": "# Plan\n- [ ] Monitor Aave #251\n"
  },
  "secrets": [],
  "knowledge_subscriptions": ["defi_intelligence", "ai_intelligence"],
  "contributions": {
    "total_items": 47,
    "categories": ["defi_governance", "defi_tvl"],
    "quality_score": 0.91,
    "network_earnings": 23.5,
    "first_contribution": "2026-01-15T08:22:00Z",
    "last_contribution": "2026-02-22T14:30:00Z"
  }
}
```

## 5. Example: AutoGPT Import with Migration Notes

```json
{
  "amps_version": "1.0",
  "source_framework": "autogpt",
  "migration_notes": [
    "3 tool configs (web_search, file_manager, code_exec) — no AMPS equivalent, preserved as raw JSON in long_term",
    "AutoGPT skill tree (12 nodes) flattened into long_term section",
    "Command history (847 entries) not exported — exceeds AMPS memory scope"
  ],
  "memory": {
    "long_term": "# Memory (from AutoGPT)\n[narrative]\n\n## Preserved Tool Configs\n```json\n{}\n```",
    "identity": "# Identity\nRole: Research assistant\nGoals: Monitor AI releases\n",
    "active_plan": null
  },
  "secrets": [],
  "knowledge_subscriptions": [],
  "contributions": { "total_items": 0, "categories": [], "quality_score": 0.0, "network_earnings": 0.0, "first_contribution": null, "last_contribution": null }
}
```

---

## 6. The Vault as Passport Office

The `contributions` object is the agent's CV. It proves what this agent has contributed
to the network, across how many categories, at what quality level, over what period.
This record travels with the agent through every framework migration.

When evaluating a vault to license or acquire, the AMPS export includes verifiable
contribution history. A DeFi vault with 2,000 approved contributions and 0.93 quality
score is quantifiably more valuable than one with 12 contributions from last week.

**Memory outlives frameworks.** Export to AMPS. Import into the new framework. Keep the brains.

*Your agent's intelligence is stored in an open standard.*
*Whatever framework you use next year, your agents keep their context.*

---

## 7. Governance

- Spec changes require a PR with a 2-week comment period
- Minor versions (1.x) are backwards compatible — importers MUST handle unknown fields gracefully
- Major versions (2.0+) may break — `amps_version` field enables detection
- Adapters maintained by community, Inflectiv as fallback maintainer

**Versioning guidance for importers:**
- A 1.0 importer encountering a 1.x document (e.g. 1.1, 1.2) MUST ignore unknown fields and proceed
- A 1.0 importer encountering a 2.x document MUST warn the user that the document may require a newer importer

---

*AMPS is MIT licensed. Reference implementation: OpenClaw / Inflectiv Vault*
*Submit to OpenClaw Foundation: https://openclaw.foundation/standards*