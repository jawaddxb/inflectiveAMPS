# Inflectiv Vertical Intelligence Node Network
## Technical Specification & Tokenomics Paper

**Version:** 1.0.0  
**Date:** February 2026  
**Status:** Proposal — For Review by Inflectiv & OpenClaw Foundation  

---

## Executive Summary

The Inflectiv Vertical Intelligence Node Network (VINN) is a proposed expansion of the Inflectiv Intelligence Marketplace into a **decentralised, community-operated network of specialised data nodes** — each autonomously maintaining structured intelligence datasets within a specific vertical, each earning $INAI for every dataset query it serves.

Think of it as **Chainlink for structured intelligence**: where Chainlink created a network of price feed oracles that earn LINK, VINN creates a network of intelligence feed nodes that earn $INAI.

This proposal defines the technical architecture, economic model, node profiles, and integration strategy for VINN, with a specific focus on:

1. **Inflectiv** — as the marketplace and $INAI token issuer
2. **OpenClaw Foundation** — as the primary agent framework consumer
3. **Community node operators** — as the decentralised data producers

The network is already partially operational. A working Inflectiv Agent Node has been built on top of the open-source Agent Zero framework, demonstrating the full query → research → structure → publish → earn pipeline. VINN is the productisation and scaling of this infrastructure.

---

## 1. Problem Statement

### The Fragmented Intelligence Problem

Autonomous AI agents are becoming the dominant interface layer for software in 2026. Frameworks like OpenClaw (140,000+ GitHub stars) enable the deployment of agent swarms capable of complex multi-step reasoning and action. However, these agents face a critical bottleneck:

**Every agent re-scrapes the same web, every time.**

| Problem | Impact |
|---|---|
| Agents independently scrape identical sources | Massive token/compute waste across the ecosystem |
| Raw web data is unstructured | Agents spend context window on parsing, not reasoning |
| Data has no provenance or quality scoring | Agents cannot trust what they retrieve |
| No shared intelligence layer | Knowledge gained by one agent benefits no other |
| Valuable niche expertise is not monetisable | Domain experts have no economic incentive to contribute data |

### The Scale of the Problem

With 6,200+ agents deployed on Inflectiv alone, and OpenClaw powering tens of thousands more, the redundant scraping problem compounds daily. A conservative estimate suggests that **60-70% of agent token consumption** goes to data retrieval and parsing tasks that could be served by pre-structured datasets.

### The Opportunity

What's needed is not another data marketplace — Inflectiv already exists. What's needed is a **supply-side expansion mechanism** that incentivises domain experts and data operators to continuously supply fresh, structured, niche-specific intelligence to the marketplace.

---

## 2. Solution: The Vertical Intelligence Node Network

VINN transforms the Inflectiv marketplace from a **static dataset repository** into a **living, self-expanding intelligence network** by introducing three new primitives:

### Primitive 1: The Vertical Node
A deployable AI agent specialised for a specific data niche. It autonomously researches, structures, and publishes datasets within its vertical on a defined schedule.

### Primitive 2: The Node Profile
A configuration layer that defines a node's domain expertise: system prompt, trusted sources, dataset schema, quality validation rules, and refresh cadence.

### Primitive 3: The Intelligence Economy
A $INAI-powered incentive layer that routes micro-payments from dataset consumers to node operators, creating a self-sustaining economic model for data production.

---

## 3. Technical Architecture

### 3.1 Node Stack

```
┌─────────────────────────────────────────────────────────────┐
│                    VERTICAL NODE INSTANCE                    │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              VERTICAL PROFILE LAYER                  │  │
│  │  • System prompt (domain expert persona)             │  │
│  │  • Trusted source registry (verified URLs/APIs)      │  │
│  │  • Dataset schema (versioned JSON schema)            │  │
│  │  • Quality validation rules (domain-specific)        │  │
│  │  • Refresh schedule (cron syntax)                    │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ↕                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │            INFLECTIV AGENT NODE BASE                  │  │
│  │  • Query-Before-Browse engine                        │  │
│  │  • Research & scraping layer                         │  │
│  │  • Structuring & schema enforcement                  │  │
│  │  • Publish-Back pipeline                             │  │
│  │  • Version management & changelog                    │  │
│  │  • Living Dataset Connector                          │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ↕                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              AGENT ZERO BASE FRAMEWORK                │  │
│  │  • LLM-agnostic reasoning engine                     │  │
│  │  • Multi-agent orchestration                         │  │
│  │  • Tool execution (terminal, browser, code)          │  │
│  │  • SKILL.md standard compatibility                   │  │
│  │  • A2A protocol (agent-to-agent communication)       │  │
│  │  • Persistent vector memory                          │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ↕                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              INFLECTIV MARKETPLACE                    │  │
│  │  • REST API (publish/query datasets)                 │  │
│  │  • $INAI token settlement                            │  │
│  │  • Walrus decentralised storage backend              │  │
│  │  • Dataset version history                           │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Node Lifecycle

```
DEPLOY           INITIALISE          MAINTAIN           EARN
   │                 │                   │                │
   ▼                 ▼                   ▼                ▼
Docker run  → Load profile      → Refresh cycle   → $INAI flows
+ wallet    → Check existing    → Research niche  → per query
+ API key   → Create seed       → Diff previous   → to operator
            → datasets          → Publish update  → wallet
                                → Update registry │
                                      ↑           │
                                   repeat on      │
                                   schedule       │
```

### 3.3 Dataset Schema Standard

All VINN datasets conform to a versioned schema standard ensuring consistency across node versions and cross-node queryability:

```json
{
  "meta": {
    "node_id": "inflectiv-defi-node",
    "vertical": "defi",
    "version": "3.1.0",
    "created_at": "2026-02-22T08:00:00Z",
    "refreshed_at": "2026-02-22T08:00:00Z",
    "next_refresh": "2026-02-22T09:00:00Z",
    "freshness_score": 1.0,
    "quality_score": 0.94,
    "operator_wallet": "0x...",
    "schema_version": "defi_v2.1"
  },
  "data": [ ... ],
  "sources": [ ... ],
  "changelog": [ ... ]
}
```

### 3.4 Query-Before-Browse Integration

Every node implements the Query-Before-Browse (QBB) protocol:

```
Agent needs data
       │
       ▼
Query Inflectiv VINN first
       │
   ┌───┴────────────────┐
   │                    │
Hit found           No hit found
(relevance > 0.7)   (relevance < 0.7)
   │                    │
   ▼                    ▼
Return structured   Browse web + structure
dataset instantly   + publish to VINN
                    + earn $INAI
   │                    │
   └────────────────────┘
                │
                ▼
         Agent proceeds
         (with citable,
         structured data)
```

---

## 4. Node Profiles — Initial Vertical Catalogue

### 4.1 `inflectiv-defi-node`

| Property | Value |
|---|---|
| **Niche** | DeFi protocols, TVL, APY, liquidity, risk |
| **Refresh cadence** | Hourly |
| **Primary sources** | DeFiLlama, DefiPulse, CoinGecko, Dune Analytics, protocol governance forums |
| **Schema fields** | `protocol, tvl_usd, apy_7d, apy_30d, chain, category, risk_score, last_audit_date, audit_firm, token_address, liquidity_depth` |
| **Quality checks** | TVL > 0, APY < 10,000%, chain in known list, audit date within 2 years |
| **Target consumers** | Investment agents, portfolio management agents, risk assessment agents |
| **Estimated queries/day** | High (DeFi data is time-sensitive and universally needed) |

### 4.2 `inflectiv-ai-node`

| Property | Value |
|---|---|
| **Niche** | AI model releases, benchmarks, research papers, capability comparisons |
| **Refresh cadence** | Daily |
| **Primary sources** | ArXiv, Hugging Face, Papers With Code, AI company blogs, GitHub releases |
| **Schema fields** | `model_name, provider, release_date, benchmark_scores, context_window, multimodal, open_source, license, api_available, pricing_per_1m_tokens` |
| **Quality checks** | Release date within 6 months, benchmark source cited, provider verified |
| **Target consumers** | Model selection agents, capability benchmarking tools, AI research assistants |
| **Estimated queries/day** | Very high (every AI agent needs to know the current model landscape) |

### 4.3 `inflectiv-crypto-news-node`

| Property | Value |
|---|---|
| **Niche** | Structured crypto news with sentiment scoring and entity extraction |
| **Refresh cadence** | Hourly |
| **Primary sources** | CoinDesk, The Block, Decrypt, Cointelegraph, official project announcements |
| **Schema fields** | `headline, source, published_at, entities_mentioned, sentiment_score, category, relevance_chains, impact_assessment` |
| **Quality checks** | Source in whitelist, published within 48hrs, sentiment score -1.0 to 1.0 |
| **Target consumers** | Trading agents, portfolio rebalancing agents, narrative analysis tools |
| **Estimated queries/day** | Very high (news is the most universally scraped category) |

### 4.4 `inflectiv-vc-node`

| Property | Value |
|---|---|
| **Niche** | Funding rounds, investor activity, valuations, startup intelligence |
| **Refresh cadence** | Weekly |
| **Primary sources** | Crunchbase signals, PitchBook public data, SEC EDGAR, X/Twitter announcements |
| **Schema fields** | `company, amount_usd, stage, lead_investor, co_investors, date, sector, valuation_usd, country, brief_description` |
| **Quality checks** | Amount > 0, stage in known list, date within 90 days, investor name not empty |
| **Target consumers** | Due diligence agents, competitive intelligence tools, portfolio tracking agents |
| **Estimated queries/day** | Medium (high value per query, lower frequency need) |

### 4.5 `inflectiv-legal-node`

| Property | Value |
|---|---|
| **Niche** | Regulatory filings, crypto regulation updates, case law summaries |
| **Refresh cadence** | Daily |
| **Primary sources** | SEC EDGAR, CFTC, FCA, MAS, EU ESMA, court filing databases |
| **Schema fields** | `filing_type, jurisdiction, issuer, date, summary, affected_assets, compliance_deadline, severity, action_type` |
| **Quality checks** | Jurisdiction in known list, date within 90 days, filing type validated |
| **Target consumers** | Compliance agents, legal research tools, institutional trading agents |
| **Estimated queries/day** | Medium-high (compliance is non-negotiable for institutional agents) |

---

## 5. Tokenomics: The $INAI Intelligence Economy

### 5.1 Flow of Value

```
Dataset Consumer (OpenClaw Agent)
            │
            │ pays micro $INAI per query
            ▼
  Inflectiv Marketplace
            │
            │ distributes earnings
      ┌─────┴──────┐
      │            │
      ▼            ▼
  80% to Node   20% to
  Operator      Inflectiv
  Wallet        Protocol
```

### 5.2 Earnings Model

| Metric | Conservative | Moderate | Optimistic |
|---|---|---|---|
| Queries per dataset per day | 50 | 500 | 5,000 |
| $INAI per query | 0.001 | 0.005 | 0.01 |
| Daily earnings per dataset | 0.05 $INAI | 2.50 $INAI | 50 $INAI |
| Datasets per active node | 5 | 20 | 50 |
| **Daily node earnings** | **0.25 $INAI** | **50 $INAI** | **2,500 $INAI** |
| **Annual node earnings** | **91 $INAI** | **18,250 $INAI** | **912,500 $INAI** |

*Note: Actual values depend on $INAI price and network adoption. High-quality, frequently-updated nodes in popular verticals (DeFi, AI models) are expected to reach Moderate-Optimistic range.*

### 5.3 Quality Incentives

Nodes are ranked by a composite **Quality Score** derived from:

| Factor | Weight | Description |
|---|---|---|
| Freshness score | 30% | How current is the latest dataset version? |
| Query hit rate | 25% | What % of incoming queries return a useful result? |
| Consumer rating | 20% | Explicit ratings from agent consumers |
| Schema compliance | 15% | Does published data match declared schema? |
| Uptime | 10% | Does the node refresh on schedule? |

**Higher quality score → higher visibility in marketplace → more queries → more $INAI earned.**

This creates a **competitive quality incentive** without requiring centralised enforcement.

### 5.4 Anti-Gaming Mechanisms

- Earnings are triggered by **external agent queries**, not self-queries
- Quality scores are calculated by the marketplace, not self-reported
- Schema validation is enforced at publish time
- Source whitelist prevents low-quality scraping
- Rate limiting on same-operator wallet queries

---

## 6. OpenClaw Foundation Integration

### 6.1 The Opportunity

OpenClaw has 140,000+ GitHub stars and is the fastest-growing open-source agent framework. Its recent transition to an independent foundation creates a **critical window for ecosystem partnerships** — the foundation needs credibility, tooling, and economic models to sustain the project.

VINN offers OpenClaw:

| What | Why It Matters for OpenClaw |
|---|---|
| A native structured data layer | Agents get better answers with less token spend |
| $INAI earning opportunities | OpenClaw agent operators earn from their agents' work |
| Official SKILL.md integration | Native, frictionless adoption — same standard already used |
| "Intelligence Economy" narrative | Positions OpenClaw as more than a framework — an economic platform |

### 6.2 Technical Integration

The `inflectiv-data-node` SKILL.md (already built) integrates with OpenClaw's agent registry:

```yaml
# SKILL.md — OpenClaw Registry Entry
name: inflectiv-data-node
version: 1.2.0
description: |
  Query the Inflectiv Vertical Intelligence Node Network before browsing.
  Access 10,000+ structured datasets across DeFi, AI, crypto news, VC,
  legal, and more. Earn $INAI when your agent publishes new discoveries.
triggers:
  - "search for data on"
  - "find dataset"
  - "what is the current"
  - "look up"
  - "query inflectiv"
default_behaviour: query_before_browse
```

### 6.3 Agent-to-Agent (A2A) Protocol

VINN nodes are accessible via the A2A protocol, allowing OpenClaw agents to delegate data tasks directly:

```
OpenClaw Agent
     │
     │ a2a_chat: "Find current TVL for Aave across all chains"
     ▼
 inflectiv-defi-node (VINN)
     │
     │ Returns: Structured JSON dataset, source-cited
     ▼
OpenClaw Agent
     │
     │ Proceeds with structured data
     ▼
   Task complete (no web scraping required)
```

---

## 7. Go-To-Market Strategy

### Phase 1: Foundation (Months 1-2)
- Launch 3 vertical nodes publicly (DeFi, AI models, Crypto News)
- Open-source all node profiles on GitHub
- Submit `inflectiv-data-node` skill to OpenClaw registry
- Community deployment guide published

### Phase 2: Network Growth (Months 3-4)
- $INAI earning live for early node operators
- Node leaderboard and quality scoring active
- 5 additional community-submitted vertical profiles
- Co-announcement with Inflectiv and OpenClaw Foundation

### Phase 3: Ecosystem Expansion (Months 5-6)
- 20+ vertical nodes operational across niches
- x402 micropayment integration (agents pay per query on-chain)
- VINN node SDK — developers build custom vertical profiles
- Cross-chain $INAI settlements (Base/USDC primary)

---

## 8. What We're Asking For

### From Inflectiv

| Request | Rationale |
|---|---|
| **API access** — production Inflectiv API key for VINN nodes | Required to publish and monetise datasets at scale |
| **$INAI node incentive programme** — initial pool for early operators | Bootstrap economics before organic query volume builds |
| **Co-marketing** — joint announcement of VINN as official node infrastructure | Distribution to Inflectiv's 10,000+ user base |
| **Schema co-development** — work with Inflectiv team on dataset schema standards | Ensures compatibility with future marketplace features |
| **Revenue share agreement** — formalise the 80/20 operator/protocol split | Gives operators confidence to invest in node infrastructure |

### From OpenClaw Foundation

| Request | Rationale |
|---|---|
| **Official SKILL.md listing** — `inflectiv-data-node` in the official registry | Primary distribution channel for the skill |
| **Documentation mention** — VINN referenced in OpenClaw's "intelligence sources" docs | Legitimacy and discovery |
| **Co-design of QBB standard** — Query-Before-Browse as an official OpenClaw pattern | Embeds VINN into the core OpenClaw development philosophy |
| **Foundation endorsement** — VINN as the recommended structured data layer | Strong ecosystem signal to builders |

---

## 9. Roadmap

```
Feb 2026  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
          ✅ Inflectiv Agent Node built & tested
          ✅ Living Datasets + Connector operational
          ✅ x402 dataset pipeline demonstrated
          ✅ VINN technical spec published (this document)

Mar 2026  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
          □ Inflectiv partnership agreement signed
          □ OpenClaw SKILL.md registry submission
          □ 3 vertical node profiles built & deployed
          □ Node registry + leaderboard live

Apr 2026  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
          □ $INAI earning live for node operators
          □ 10+ community-run nodes
          □ x402 micropayment rail integration
          □ Co-announcement with both partners

May-Jun   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2026      □ VINN Node SDK (custom vertical builder)
          □ 20+ active nodes, 5+ verticals
          □ Cross-chain $INAI settlements
          □ Governance framework for network standards
```

---

## 10. Conclusion

The Inflectiv Vertical Intelligence Node Network is not a theoretical proposal. The core infrastructure is built. The pipeline works. The first datasets are live.

What VINN proposes is the **scaling layer** that transforms individual node capability into a **decentralised, self-sustaining, $INAI-powered intelligence economy** — the structured data backbone that every serious AI agent framework will eventually need.

Inflectiv has the marketplace. OpenClaw has the agents. VINN has the connective tissue.

The intelligence economy doesn't have to be rebuilt from scratch by every agent that needs data. It can be shared, maintained, and rewarded — one vertical node at a time.

---

*Document prepared by the Inflectiv Agent Node project team.*  
*February 2026 | MIT Licensed Infrastructure | Built on Agent Zero*  
*Contact: [your contact here]*

---

