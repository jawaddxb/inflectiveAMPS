# AMPS Compatibility Report — [Month Year]

*Published by Inflectiv / OpenClaw Foundation*
*Next report: [date]*

---

## Overview

The AMPS Compatibility Report tracks how well each framework's adapter preserves
agent memory through export → import cycles.

**This month:** [X] frameworks tracked, [Y] new adapters, [Z] migration case studies.

---

## Compatibility Matrix

> Score = % of memory fields transferred without data loss, averaged across test migrations.
> Lossless = 100% for AMPS-native implementations.

| Framework | Export Score | Import Score | AMPS Score | Adapter Version | Notes |
|---|---|---|---|---|---|
| Agent Zero (native) | 100% | 100% | **100** | v1.0 | Reference implementation — lossless |
| AutoGPT | ?% | ?% | **?** | v1.0 | Memory summaries + role/goals |
| CrewAI | ?% | ?% | **?** | v1.0 | Backstory + task outputs |
| LangGraph | ?% | ?% | **?** | v1.0 | Checkpoint text nodes |
| LlamaIndex | ?% | ?% | **?** | v1.0 | Docstore text content |

*Scores based on [N] migrations tested this month.*

---

## Field-Level Coverage

| Field | Agent Zero | AutoGPT | CrewAI | LangGraph | LlamaIndex |
|---|---|---|---|---|---|
| `memory.long_term` | ✅ Native | ✅ memory_summary | ✅ task outputs | ✅ checkpoint text | ✅ docstore |
| `memory.identity` | ✅ SOUL.md | ✅ role+goals | ✅ backstory | ⚠️ system prompt only | ⚠️ manual |
| `memory.active_plan` | ✅ task_plan.md | ❌ no equivalent | ❌ no equivalent | ❌ no equivalent | ❌ no equivalent |
| `secrets` | ✅ never exported | ✅ never exported | ✅ never exported | ✅ never exported | ✅ never exported |
| `contributions` | ✅ from stats.json | ❌ no equivalent | ❌ no equivalent | ❌ no equivalent | ❌ no equivalent |

✅ Full support | ⚠️ Partial / manual | ❌ Not applicable

---

## Migration Case Studies

### [Framework A] → [Framework B]

**Agent:** [description — e.g., DeFi research agent, 3 months of training]  
**Memory size:** [X KB long_term, Y KB identity]  
**Contributions:** [N items, quality score Z]  
**Migration time:** [seconds]  
**Migration notes:** [what was dropped, if anything]  
**Outcome:** [e.g., "agent had 85% of prior context on first query"]

---

## New Community Adapters

| Adapter | Framework | Author | AMPS Score | Link |
|---|---|---|---|---|
| [name] | [framework] | [@handle] | [score] | [url] |

*To submit a community adapter: open a PR to `inflectiv/amps/community_adapters/`*

---

## Trend: AMPS Scores Over Time

```
Framework    | Jan | Feb | Mar | Apr | May | Jun
-------------|-----|-----|-----|-----|-----|----
Agent Zero   | 100 | 100 | 100 | 100 | 100 | 100
AutoGPT      |  -- |  72 |  75 |  78 |  81 |  83
CrewAI       |  -- |  68 |  71 |  74 |  76 |  79
LangGraph    |  -- |  61 |  65 |  70 |  73 |  77
LlamaIndex   |  -- |  66 |  69 |  72 |  75 |  78
```

*Scores improve as adapters mature and framework maintainers adopt AMPS natively.*

---

## Next Month

- [ ] [Planned adapter / framework coverage]
- [ ] [Planned case study]
- [ ] [Community contribution highlight]

*AMPS is MIT licensed. Contribute adapters, report issues, propose spec changes:*
*https://github.com/inflectiv/amps*
