<div align="center">

<img src="https://www.inflectiv.ai/inflectiv-logo.png" alt="Inflectiv" width="240" />

# Inflectiv Agent Node

### The Intelligence Layer for OpenClaw Agents

*Capture Experience. Liberate Knowledge. Fuel Every AI.*

[![License: MIT](https://img.shields.io/badge/License-MIT-1b0c25.svg?style=for-the-badge)](LICENSE)
[![OpenClaw Compatible](https://img.shields.io/badge/OpenClaw-Compatible-45658a?style=for-the-badge)](https://openclaw.foundation)
[![Powered by Inflectiv](https://img.shields.io/badge/Powered%20by-Inflectiv-e8985d?style=for-the-badge)](https://inflectiv.ai)
[![SKILL.md](https://img.shields.io/badge/SKILL.md-Standard-a3c7dc?style=for-the-badge)](https://agentskills.io)

</div>

---

## What is Inflectiv Agent Node?

**Inflectiv Agent Node** is a fork of [Agent Zero](https://github.com/agent0ai/agent-zero) — the MIT-licensed, model-agnostic AI agent framework — pre-configured as a **structured data intelligence backend** for [OpenClaw](https://openclaw.foundation) multi-agent systems.

OpenClaw agents are world-class at *taking actions*. Inflectiv Agent Node gives them world-class *structured intelligence* to act on.

```
┌─────────────────────────────────────────────────────────────┐
│                    YOUR OPENCLAW SWARM                      │
│                                                             │
│   ┌──────────────┐    ┌──────────────┐    ┌─────────────┐  │
│   │  OpenClaw    │    │  OpenClaw    │    │  OpenClaw   │  │
│   │   Agent A    │    │   Agent B    │    │   Agent C   │  │
│   └──────┬───────┘    └──────┬───────┘    └──────┬──────┘  │
│          │                  │                    │         │
│          └──────────────────┼────────────────────┘         │
│                             │ A2A Protocol                 │
│                             ▼                              │
│                  ┌─────────────────────┐                   │
│                  │  Inflectiv Agent    │                   │
│                  │      Node  🧠       │                   │
│                  │  (This Repo)        │                   │
│                  └──────────┬──────────┘                   │
└─────────────────────────────┼───────────────────────────────┘
                              │ Inflectiv API + $INAI
                              ▼
             ┌─────────────────────────────────┐
             │      Inflectiv.ai Marketplace   │
             │  ┌─────────┐  ┌─────────────┐  │
             │  │Datasets │  │  AI Agents  │  │
             │  └─────────┘  └─────────────┘  │
             │  ┌─────────┐  ┌─────────────┐  │
             │  │ Walrus  │  │  $INAI Rail │  │
             │  │Storage  │  │  Payments   │  │
             │  └─────────┘  └─────────────┘  │
             └─────────────────────────────────┘
```

---

## ✨ Key Features

### 🔍 Native Inflectiv AgentSkill
Pre-installed `SKILL.md`-compatible skill for querying and publishing to the Inflectiv marketplace. OpenClaw agents can delegate data tasks natively — no setup required.

### 🧠 Query-Before-Browse Pattern
Before touching the web, the node checks Inflectiv's structured datasets first. Saves tokens. Saves time. Earns $INAI rewards for the data creator.

### 📤 Publish-Back Pipeline
When the node discovers new data via browsing or research, it automatically structures and publishes it back to the Inflectiv marketplace — turning every agent run into a data flywheel.

### 💸 $INAI Micro-Payment Rail
Agent-to-agent data transactions priced in $INAI and settled automatically on-chain. Your node earns every time its datasets are queried.

### 🗄️ Walrus Decentralized Storage
Optional Walrus backend for encrypted, decentralized agent memory — no single point of failure, full data sovereignty.

### 📊 Living Datasets
Interest-based, auto-refreshing datasets that stay current without manual intervention. Subscribe to a topic, and the node continuously researches, structures, and publishes updates on your schedule.

### 🤝 Full OpenClaw A2A Compatibility
Runs as a subordinate data node that any OpenClaw agent can call via the Agent-to-Agent (A2A) protocol. Drop it into any existing swarm.

### 🔧 100% Model-Agnostic
Works with OpenAI, Anthropic, Ollama, Mistral, or any LLM. Same flexibility as Agent Zero, tuned for the Intelligence Economy.

---

## ⚡ Quick Start

### Docker (Recommended)

```bash
# 1. Clone this repo
git clone https://github.com/your-org/inflectiv-agent-node
cd inflectiv-agent-node

# 2. Configure your environment
cp .env.example .env
# Edit .env with your INFLECTIV_API_KEY and LLM keys

# 3. Run
docker compose up -d

# 4. Open http://localhost:50001
```

### Manual

```bash
# Pull Agent Zero base
docker pull agent0ai/agent-zero

# Mount this repo's skills and prompts
docker run -p 50001:80 \
  -v $(pwd)/skills:/a0/skills \
  -v $(pwd)/prompts:/a0/prompts \
  --env-file .env \
  agent0ai/agent-zero
```

---

## 📦 The Inflectiv AgentSkill

The skill is located at `skills/inflectiv/` and follows the [SKILL.md standard](https://agentskills.io), making it compatible with:
- ✅ OpenClaw
- ✅ Agent Zero
- ✅ Claude Code
- ✅ Cursor
- ✅ GitHub Copilot
- ✅ OpenAI Codex CLI

### Using the skill from any compatible agent:

```bash
# Query a dataset
python skills/inflectiv/scripts/query_datasets.py \
  --query "DeFi protocol TVL data Q4 2025" \
  --api-key $INFLECTIV_API_KEY

# Publish discovered data back to the marketplace
python skills/inflectiv/scripts/publish_dataset.py \
  --title "OpenClaw Agent Research: DeFi Q4 2025" \
  --files report.json data.csv \
  --api-key $INFLECTIV_API_KEY \
  --visibility public
```

---

## 🏗️ Project Structure

```
inflectiv-agent-node/
├── skills/
│   └── inflectiv/
│       ├── SKILL.md                    ← OpenClaw-compatible skill definition
│       └── scripts/
│           ├── query_datasets.py       ← Query Inflectiv marketplace
│           ├── publish_dataset.py      ← Publish data back to marketplace
│           └── requirements.txt
├── connector/
│   ├── manager.py                ← Living Dataset CLI manager
│   ├── refresh_task.py           ← Auto-refresh engine
│   └── registry.json             ← Active dataset registry
├── prompts/
│   └── inflectiv-node/
│       └── agent.system.md             ← Specialized system prompt
├── brand-assets/                       ← Inflectiv brand assets
├── docker-compose.yml
├── .env.example
├── OPENCLAW_PITCH.md                   ← Partnership proposal
└── README.md
```

---

## 🔗 Ecosystem

| Project | Role | Link |
|---|---|---|
| **Inflectiv** | Intelligence platform & marketplace | [inflectiv.ai](https://inflectiv.ai) |
| **Agent Zero** | Base agent framework (MIT) | [agent-zero.ai](https://agent-zero.ai) |
| **OpenClaw Foundation** | Agent ecosystem & distribution | [openclaw.foundation](https://openclaw.foundation) |
| **Walrus** | Decentralized storage layer | Partner |
| **$INAI** | Economic primitive & payment rail | [inflectiv.ai/tokenization](https://inflectiv.ai/tokenization) |
| **Sui** | Blockchain infrastructure | Partner |

---

## 📚 Documentation

- [Inflectiv Docs](https://inflectiv.gitbook.io/inflectiv)
- [Agent Zero Docs](https://agent-zero.ai)
- [SKILL.md Standard](https://agentskills.io)
- [OpenClaw Foundation](https://openclaw.foundation)

---

## 🤝 Contributing

This project is MIT licensed. Contributions welcome.

To propose a partnership with the OpenClaw Foundation, see [OPENCLAW_PITCH.md](OPENCLAW_PITCH.md).

---

<div align="center">

*Part of the Inflectiv Intelligence Economy*

[![X](https://img.shields.io/badge/@inflectivAI-000000?style=flat&logo=x)](https://x.com/inflectivAI)
[![Discord](https://img.shields.io/badge/Discord-5865F2?style=flat&logo=discord&logoColor=white)](https://discord.com/invite/inflectiv)
[![Telegram](https://img.shields.io/badge/Telegram-2CA5E0?style=flat&logo=telegram&logoColor=white)](https://t.me/inflectiv)

**Turn data into usable and ownable intelligence assets.**

</div>
