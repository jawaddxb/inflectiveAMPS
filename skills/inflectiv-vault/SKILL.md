---
name: inflectiv-vault
version: 1.0.0
title: Inflectiv Vault
description: Personal memory vault with encrypted credentials, MAD memory, and unified vault.query() interface covering personal + shared + VINN network.
tags: [memory, credentials, inflectiv, vinn, openclaw]
author: Inflectiv Agent Node Project
---

# Inflectiv Vault Skill

## Purpose
Single knowledge layer for agents: local memory, encrypted API keys, and live network intelligence through one interface.

## Start
```bash
cd /a0/usr/workdir/inflectiv-agent-node/vault
pip install fastapi uvicorn cryptography
VAULT_ROOT=/tmp/vault VAULT_MASTER_PASSWORD=secret python vault_server.py
```
Port 8766. First start prints your owner token — save it.

## Key Endpoints

### Query (unified — always call before web search)
```bash
curl -X POST http://localhost:8766/vault/query   -H "X-Vault-Token: TOKEN"   -H "Content-Type: application/json"   -d '{ "q": "Aave governance", "include_network": true }'
```
Returns: results (primary, recency-ranked) + also_found (conflicts, source-attributed)

### Session context (call at session start)
```bash
curl http://localhost:8766/vault/memory/context -H "X-Vault-Token: TOKEN"
```

### Memory read/write
```bash
curl http://localhost:8766/vault/memory/MEMORY.md -H "X-Vault-Token: TOKEN"
curl -X POST http://localhost:8766/vault/memory/MEMORY.md   -H "X-Vault-Token: TOKEN" -H "Content-Type: application/json"   -d '{ "content": "# Memory

- learned X", "mode": "write" }'
```

### Secrets
```bash
curl -X POST http://localhost:8766/vault/secrets/openai   -H "X-Vault-Token: TOKEN" -H "Content-Type: application/json"   -d '{ "value": "sk-..." }'
curl http://localhost:8766/vault/secrets/openai -H "X-Vault-Token: TOKEN"
```

### Classify + Contribute
```bash
curl -X POST http://localhost:8766/vault/classify   -H "X-Vault-Token: TOKEN" -H "Content-Type: application/json"   -d '{ "content": "Aave V4 vote 72% for dynamic rate curves" }'
curl -X POST http://localhost:8766/vault/contribute   -H "X-Vault-Token: TOKEN" -H "Content-Type: application/json"   -d '{ "content": "research text..." }'
```

### Create subscriber token (for shared/knowledge vaults)
```bash
curl -X POST http://localhost:8766/vault/tokens   -H "X-Vault-Token: OWNER_TOKEN" -H "Content-Type: application/json"   -d '{ "role": "subscriber", "agent": "dao-agent", "label": "read access" }'
```

## Memory File Structure
```
/vault/memory/
  MEMORY.md       <- long-term knowledge (load every session)
  SOUL.md         <- agent identity (load every session)
  task_plan.md    <- active goals (load at task start)
  notes.md        <- working notes
  logs/YYYY-MM-DD.md  <- daily logs (today+yesterday auto-loaded)
```

## Vault Types
- Personal: one owner token, private memory + keys, free
- Shared: owner + subscriber tokens, team/DAO knowledge
- Knowledge: Inflectiv-seeded, live-updating, $INAI subscription

## Integration Pattern
1. GET /vault/memory/context  -> load session memory
2. POST /vault/query          -> check vault before web search
3. POST /vault/memory/log/today -> log findings
4. POST /vault/contribute     -> stage intel for network


## SDK Usage (vault_client.py)

The vault exposes a Python SDK at `vault/vault_client.py`:

```python
from vault.vault_client import VaultClient
vc = VaultClient(base_url="http://localhost:8766", token="<owner_token>")

# Query across all vaults
results = vc.query("Aave governance")

# Export agent memory as AMPS
doc = vc.export()

# Contribute new intelligence
vc.contribute(content="New DeFi finding...", source="research_agent")

# Check earnings and ratio
stats = vc.stats()
```
