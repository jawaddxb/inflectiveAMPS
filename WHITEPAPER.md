# Inflectiv Vault & Vertical Intelligence Node Network
## Technical Whitepaper v1.1 — February 2026

---

## Executive Summary

The autonomous agent economy is producing more intelligence than it can share.
Every agent that browses the web, structures data, and produces insights throws
that work away the moment the conversation ends. Agents repeatedly pay for the
same research. The ecosystem fragments instead of compounding.

**Inflectiv Vault** is a local-first, encrypted identity and memory layer for
autonomous agents. Combined with the **Vertical Intelligence Node Network (VINN)**,
it transforms individual agent research into a shared, monetisable intelligence
commons — where contributors earn $INAI tokens and consumers gain structured,
query-ready data without re-scraping the web.

This document describes the complete technical architecture, incentive model,
and business strategy behind the system. Everything described in §3–6 is
**fully implemented and tested** as of this writing.

---

## 1. The Problem

### 1.1 Agent Intelligence is Ephemeral
Modern AI agents are excellent at research but terrible at memory. Each session
starts cold. The same web pages are re-scraped. The same PDFs are re-parsed.
At 2–8 seconds per page and $0.001–0.01 per LLM call, this is not a minor
inefficiency — it is a structural waste tax on every agent deployment.

### 1.2 Structured Data is Locked Up
The intelligence agents produce — TVL figures, benchmark comparisons, governance
vote outcomes, model pricing tables — is inherently structured. Yet it lives in
unindexed chat histories, temporary files, and markdown dumps nobody shares.

### 1.3 No Standard Memory Layer
Agent frameworks (Agent Zero, AutoGPT, CrewAI, LangGraph) each implement their
own ad-hoc memory. There is no portable, secure, cross-framework standard for:
- Encrypted credential storage
- Versioned knowledge persistence
- Cross-agent intelligence sharing
- Contribution-based access incentives

---

## 2. The Solution

### 2.1 Inflectiv Vault
A self-hostable FastAPI server (port 8766) providing:

| Layer | What It Does |
|---|---|
| **Key Store** | AES-256-GCM encrypted API keys, credentials, secrets |
| **Memory Store** | Git-versioned Markdown (`MEMORY.md`, `SOUL.md`, `task_plan.md`) |
| **Query Engine** | Unified `vault.query()` across personal + shared + network vaults |
| **Contribute Pipeline** | Auto-classify → sanitise → stage → approve → publish to VINN |
| **Stats + Earnings** | $INAI contribution ratio tracking, grace period, tier enforcement |
| **Auth** | `vtok_` prefixed owner/subscriber tokens, role-based access |

### 2.2 Vertical Intelligence Node Network (VINN)
Specialised agent nodes that own and refresh specific data niches:

```
DeFi Node        → TVL, governance votes, lending rates, DEX volumes
AI Models Node   → Benchmark scores, pricing, context windows, releases
Crypto News Node → Sentiment, protocol announcements, regulatory updates
[user-defined]   → Any niche with structured, repeatable data needs
```

Nodes earn $INAI when their published datasets are queried. This creates
a self-reinforcing quality incentive: better data → more queries → more earnings.

---

## 3. Technical Architecture

### 3.1 Vault Data Tiers

```
┌─────────────────────────────────────────────────────┐
│                  vault.query("Aave governance")      │
│                           │                          │
│  1. Personal Vault ────────┤  Private R/W             │
│     MEMORY.md              │  Highest priority        │
│     SOUL.md                │  Never leaves device     │
│     task_plan.md           │                          │
│                            │                          │
│  2. Knowledge Vaults ──────┤  Read-only subscriber    │
│     defi_intelligence/     │  Seeded by VINN nodes    │
│     ai_intelligence/       │  Auto-classified         │
│                            │                          │
│  3. Remote Vaults (v1.1) ──┤  HTTP vault-to-vault     │
│     url: partner:8766      │  Token-authenticated     │
│                            │                          │
│  4. Inflectiv VINN ────────┤  Network fallback        │
│     api.inflectiv.ai       │  Structured marketplace  │
└─────────────────────────────────────────────────────┘
                           │
              Deduplicate + rank + surface conflicts
              { results[], also_found[] }  ← source-attributed
```

### 3.2 The Flywheel

```
 Node runs research cycle
        │
        ▼
 Structures data into markdown
        │
        ▼
 vault.contribute(content)          ← node_launcher.py / refresh_task.py
        │
        ▼
 taxonomy.json classifies           ← defi_governance 0.98 confidence
        │
        ▼
 Sanitise + stage (strip PII)
        │
        ▼
 User approves (UI or VAULT_AUTO_APPROVE=true)
        │
        ▼
 Published to VINN knowledge vault  ← +0.5 $INAI credited
        │
        ▼
 Next agent query finds it immediately
        │
        ▼
 No web scraping needed             ← query cost: ~0ms vs 8s
        │
        └─────────────────────────── Network gets richer ↑
```

### 3.3 Conflict Resolution
When two vaults return conflicting data for the same query:

```json
{
  "results": [
    { "content": "Aave TVL: $18.2B", "source": "defi_intelligence", "timestamp": "2026-02-22" }
  ],
  "also_found": [
    { "content": "Aave TVL: $17.8B", "source": "personal", "timestamp": "2026-02-19",
      "note": "older — personal vault" }
  ]
}
```

Primary result = most recent. Conflicts surfaced in `also_found[]` with full
source attribution. Never silently discarded.

### 3.4 Security Model

| Concern | Implementation |
|---|---|
| Secret storage | AES-256-GCM, PBKDF2-HMAC-SHA256, 600k iterations |
| Auth tokens | `vtok_` prefix, SHA-256 hashed at rest, never logged |
| Dev bypass | Gated on `VAULT_ENV != production` |
| Default password | Startup warning if `VAULT_MASTER_PASSWORD = changeme` |
| Personal data | Stripped before staging (`[redacted]` substitution) |
| Grace period | `created_at` written once on vault init, never reset |

---

## 4. Tokenomics

### 4.1 The Ratio Model

Every vault tracks a contribution ratio:

```
ratio = approved_contributions / total_queries
```

| Tier | Condition | Access |
|---|---|---|
| **Grace** | `days_since_creation <= 14` | Full network access, free |
| **Active** | `ratio >= 0.1` | Full network access |
| **Throttled** | `ratio < 0.05` | Rate-limited queries |
| **Blocked** | `ratio = 0, days > 30` | Local vault only |

This is the BitTorrent ratio tracker model applied to structured intelligence.
Consumers who never contribute are gradually throttled out of the network.

### 4.2 $INAI Earnings

```
Contribute 1 approved item     → +0.5 $INAI (staged)
Item queried by another agent  → +0.1 $INAI per query (streaming)
Run a VINN node (DeFi)         → 0.5–2.0 $INAI per dataset query
Operate a subscription vault   → subscription revenue in $INAI
```

### 4.3 The Subscription Pivot ← Business Model Headline

The conventional micro-payment model (pay-per-query) creates friction and
requires on-chain transactions for sub-cent amounts. The Inflectiv model pivots
to **subscriptions**:

1. VINN operators convert their data niche into a **Knowledge Vault subscription**
2. Subscribers pay a fixed monthly $INAI rate for unlimited access to that vertical
3. Inflectiv operates the largest vault network on its own infrastructure
4. Third-party operators run independent nodes, earning subscription revenue

**This is the AWS playbook:** Amazon built S3 for internal use, then opened it
as a platform. Inflectiv builds VINN for internal intelligence, then opens it
for community operators. The platform captures value at the subscription layer,
not the transaction layer.

```
Inflectiv Inc.
  ├── Operates: defi_intelligence vault    → $29/mo subscription
  ├── Operates: ai_intelligence vault      → $19/mo subscription
  ├── Operates: legal_intelligence vault   → $49/mo subscription
  └── Platform fee: 15% of third-party subscriptions

Community Operators
  ├── crypto_alpha_vault                   → $39/mo, Inflectiv takes 15%
  ├── nft_intelligence_vault               → $15/mo, Inflectiv takes 15%
  └── any_niche_vault                      → self-pricing
```

---

## 5. Integration with OpenClaw / Agent Zero

### 5.1 SKILL.md Standard
Inflectiv Vault ships as a native Agent Zero skill:
```
skills/inflectiv-vault/SKILL.md
```
Any Agent Zero or OpenClaw agent can load this skill and immediately gain:
- `vault.query()` for structured intelligence retrieval
- `vault.contribute()` for knowledge publication
- Encrypted secret management
- $INAI earning capability

### 5.2 Query-Before-Browse Pattern
Agents are instructed via system prompt to always query the vault before
browsing the web:

```
1. vault.query(topic) → check local + network
2. If fresh data found → use it (0ms, $0)
3. If stale or missing → browse web, then vault.contribute(findings)
```

This single pattern change reduces per-agent web browsing by an estimated
60–80% for agents operating in well-served verticals.

### 5.3 A2A Protocol
The vault server speaks **FastA2A v0.2**, enabling agent-to-vault and
vault-to-vault queries across the OpenClaw mesh network. Any A2A-compatible
agent can query an Inflectiv Vault node without SDK installation.

---

## 6. Roadmap

| Version | Status | Features |
|---|---|---|
| **v1.0** | ✅ Built | Vault server, key store, memory R/W, query engine, contribute pipeline, taxonomy, SDK, dashboard, Docker |
| **v1.0.1** | ✅ Built | Audit fixes: dashboard, Docker paths, grace period, security guards, SDK completion |
| **v1.1** | ✅ Built | Flywheel: node_launcher + refresh_task → vault.contribute(); remote HTTP vault-to-vault queries |
| **v1.2** | 🔵 Planned | Walrus (Sui) decentralised vault backup; on-chain $INAI contribution receipts |
| **v2.0** | 🔵 Planned | Agent Memory Portability Standard (AMPS); cross-framework import/export; public node index API |
| **v2.1** | 🔵 Planned | Vault federation protocol; automatic peer discovery; mesh-mode query routing |

---

## 7. Pitch to OpenClaw Foundation

The OpenClaw ecosystem needs a memory standard the same way the internet needed
DNS — a shared resolution layer that every agent trusts and every operator can
run.

Inflectiv Vault is that layer. It is:
- **Open source** — MIT licensed, self-hostable, no vendor lock-in
- **Agent Zero native** — ships as a SKILL.md, zero integration friction
- **Revenue-generating** — subscription model, not speculation
- **Technically complete** — 3 days from idea to working flywheel

We are asking for:
1. **Official SKILL.md inclusion** in the Agent Zero skill registry
2. **OpenClaw Foundation grant** to fund Walrus integration and AMPS spec
3. **Co-marketing** as the recommended intelligence layer for OpenClaw agents

In return, OpenClaw agents gain the fastest, cheapest path to structured
intelligence — and the ecosystem gains a monetisation primitive that makes
autonomous agents economically self-sustaining.

---

## Appendix: File Structure

```
inflectiv-agent-node/
  vault/
    vault_server.py         FastAPI :8766
    auth.py                 Token auth, vault_config.json
    key_store.py            AES-256-GCM secrets
    memory_store.py         Markdown R/W + token search
    query_engine.py         Multi-vault merge, remote HTTP (v1.1)
    taxonomy.json           Rule-based classification
    vault_client.py         Python SDK
    knowledge_vaults/       Seeded: DeFi + AI intelligence
  nodes/
    node_launcher.py        Research → structure → publish → vault
    node_runner.py          Continuous loop + A2A API server
    node_api.py             FastA2A v0.2 REST server
  connector/
    refresh_task.py         Living dataset refresh → vault
    manager.py              Dataset subscription manager
  profiles/
    defi.json               DeFi vertical config
    ai-models.json          AI Models vertical config
    crypto-news.json        Crypto News vertical config
  skills/
    inflectiv-vault/SKILL.md  Agent Zero skill
    inflectiv/SKILL.md        Marketplace query skill
  docker-compose.vault.yml
  Dockerfile.vault
  WHITEPAPER.md             ← this document
```

---

*Inflectiv Vault v1.1 — Built on Agent Zero / OpenClaw framework*
*$INAI token integration via Inflectiv.ai Intelligence Marketplace*
*February 2026*
