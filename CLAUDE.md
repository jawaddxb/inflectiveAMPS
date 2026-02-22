# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Inflectiv Agent Node is a fork of Agent Zero (MIT-licensed AI agent framework) configured as a structured data intelligence backend for OpenClaw multi-agent systems. It comprises three main subsystems: the VINN Node API, the Vault, and the AMPS portability layer.

## Architecture

### Three Core Subsystems

**1. VINN Node API (`nodes/`)** — FastAPI server on port 8765
- `node_api.py`: REST + A2A (Agent-to-Agent) endpoint server. Uses `NodeState` to manage profile-based vertical intelligence nodes. Supports FastA2A v0.2 JSON-RPC protocol.
- `node_launcher.py`: CLI that runs research → structure → publish cycles for a vertical profile. Optionally contributes results to the Vault via HTTP.
- `node_runner.py` / `leaderboard.py`: Supporting node infrastructure.
- Profiles in `profiles/*.json` define verticals (defi, ai-models, crypto-news) with sources, schemas, refresh schedules, and $INAI pricing.

**2. Vault (`vault/`)** — FastAPI server on port 8766
- `vault_server.py`: Personal memory, encrypted secrets, and network intelligence API. Token-based auth (owner/subscriber roles via `auth.py`).
- `query_engine.py`: Unified multi-vault search. Query order: personal vault → knowledge vaults → remote vaults (HTTP) → Inflectiv VINN network. Deduplicates results and surfaces conflicts via `also_found`.
- `key_store.py`: Fernet-encrypted secret storage. `memory_store.py`: Markdown-based memory files with search.
- `vault/knowledge_vaults/`: Shared read-only knowledge vaults (e.g., `defi_intelligence/`, `ai_intelligence/`).
- Contribution pipeline: POST `/vault/contribute` → sanitize personal refs → classify against `taxonomy.json` → stage in `pending.jsonl` → approve/reject → track ratio and $INAI earnings.

**3. AMPS (`amps/`)** — Agent Memory Portability Standard v1.0
- Framework-agnostic JSON schema for exporting/importing agent memory across frameworks.
- `adapters/base.py`: `AMPSAdapter` ABC with `export()` and `import_amps()` methods. `empty_amps()` creates skeleton documents.
- Framework adapters: `agent_zero.py` (lossless), `autogpt.py`, `crewai.py`, `langgraph.py`, `llamaindex.py` (best-effort with migration_notes).
- `validate.py`: CLI validator — `python amps/validate.py file.amps.json [--strict] [--summary]`
- Schema at `amps/schema/amps_v1.schema.json`. Secrets field must always be `[]`.

### Cross-System Integration

- Node launcher (`node_launcher.py`) contributes research output to vault if `VAULT_URL` and `VAULT_TOKEN` env vars are set.
- Vault exposes AMPS export/import at `/vault/export` and `/vault/import`.
- The Inflectiv AgentSkill (`skills/inflectiv/`) follows the SKILL.md standard for compatibility with OpenClaw, Claude Code, Cursor, and Copilot.
- `connector/manager.py`: CLI for managing "Living Datasets" — interest-based auto-refreshing datasets tracked in `connector/registry.json`.

## Commands

### Docker (primary deployment)

```bash
# Full agent node (Agent Zero base + Inflectiv skills)
cp .env.example .env && docker compose up -d    # → http://localhost:50001

# Vault server
docker compose -f docker-compose.vault.yml up -d  # → http://localhost:8766

# Multi-node VINN deployment
docker compose -f docker-compose.nodes.yml up -d   # All verticals
docker compose -f docker-compose.nodes.yml up -d defi-node  # Single vertical
```

### Local Development

```bash
# Vault server
pip install -r vault/requirements.vault.txt
python vault/vault_server.py                        # Port 8766

# Node API server
pip install -r skills/inflectiv/scripts/requirements.txt
python nodes/node_api.py --profile defi [--port 8765] [--reload]

# Node research cycle
python nodes/node_launcher.py --profile defi        # Run full cycle
python nodes/node_launcher.py --list                 # List available profiles
python nodes/node_launcher.py --profile defi --dry-run

# Living Dataset connector
python connector/manager.py add --topic "x402 payments" --schedule daily
python connector/manager.py list
python connector/manager.py status

# Vault demo (requires vault running on 8766)
python demo.py

# AMPS validation
python amps/validate.py path/to/export.amps.json --strict
python amps/validate.py path/to/export.amps.json --summary  # CI mode

# Inflectiv skill scripts
python skills/inflectiv/scripts/query_datasets.py --query "DeFi TVL" --api-key $INFLECTIV_API_KEY
python skills/inflectiv/scripts/publish_dataset.py --title "Research" --files data.json --api-key $INFLECTIV_API_KEY
```

### Key Ports

| Service | Port | Compose File |
|---------|------|--------------|
| Agent Zero UI | 50001 | docker-compose.yml |
| VINN Node API | 8765 | docker-compose.nodes.yml |
| Vault Server | 8766 | docker-compose.vault.yml |
| Leaderboard UI | 8080 | docker-compose.nodes.yml |

## Key Conventions

- **Python 3.12**, no virtual env management in repo — use Docker or manual pip install.
- **FastAPI + Pydantic v2** for all API servers. Uvicorn as ASGI server.
- **No test suite exists** — there are no tests in this repo currently.
- **Vault auth**: Token-based with `X-Vault-Token` header. Roles: `owner` (full access) and `subscriber` (read-only). In non-production mode, `VAULT_TOKEN` env var provides a bypass token.
- **Memory is Markdown**: All vault memory (`MEMORY.md`, `SOUL.md`, daily logs) stored as `.md` files, searchable via keyword matching.
- **Taxonomy-driven classification**: `vault/taxonomy.json` defines categories and terms for auto-classifying contributions.
- **AMPS adapters**: When adding a new framework adapter, inherit from `AMPSAdapter` in `amps/adapters/base.py`, implement `export()` and `import_amps()`, and register in `amps/__init__.py`.
- **Contribution ratio**: Vault tracks queries-to-contributions ratio. After 14-day grace period, ratio below 0.05 with >50 queries triggers HTTP 429 throttling.

## Environment Variables

Key variables (see `.env.example` for full list):
- `INFLECTIV_API_KEY`: Platform API key
- `VAULT_MASTER_PASSWORD`: Fernet encryption key for vault secrets (default: "changeme")
- `VAULT_URL` / `VAULT_TOKEN`: Connect node launcher to vault
- `VAULT_AUTO_APPROVE`: Set "true" for auto-approving vault contributions
- `VAULTS_CONFIG`: YAML path for configuring shared/knowledge vaults
- `PROFILE`: Vertical profile name (defi, ai-models, crypto-news)
