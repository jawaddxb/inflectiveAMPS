#!/usr/bin/env python3
"""
Inflectiv Vertical Intelligence Node — REST + A2A API Server
Exposes the node as a live queryable service on port 8765.

Endpoints:
  GET  /              Node identity card
  GET  /health        Health + freshness check
  GET  /node          Full node registration metadata
  GET  /datasets      List all datasets managed by this node
  GET  /datasets/{id} Get a specific dataset
  POST /query         Natural-language query against cached datasets
  POST /a2a           FastA2A v0.2 compatible agent-to-agent endpoint

Usage:
  python nodes/node_api.py --profile defi [--port 8765]
"""

import argparse
import json
import os
import uuid
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Any

from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel
import uvicorn

BASE = Path(__file__).parent.parent
PROFILES_DIR = BASE / "profiles"
DATA_DIR = Path(os.getenv("DATA_DIR", BASE / "nodes"))
CONNECTOR_DIR = BASE / "connector"

# ── Models ────────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    q: str
    dataset_id: Optional[str] = None
    max_results: int = 10

class QueryResponse(BaseModel):
    answer: str
    dataset_id: Optional[str]
    records_scanned: int
    freshness: str
    node_id: str
    inai_cost: float

# FastA2A v0.2 compatible models
class A2AMessagePart(BaseModel):
    type: str = "text"
    text: Optional[str] = None

class A2AMessage(BaseModel):
    role: str
    parts: list[A2AMessagePart]

class A2ATaskRequest(BaseModel):
    id: Optional[str] = None
    sessionId: Optional[str] = None
    message: A2AMessage

class A2ATaskSendParams(BaseModel):
    id: Optional[str] = None
    sessionId: Optional[str] = None
    message: A2AMessage

class A2AJsonRpcRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: Optional[dict] = None
    id: Optional[Any] = None

# ── Node State ────────────────────────────────────────────────────────────────

class NodeState:
    def __init__(self, profile_id: str):
        self.profile_id = profile_id
        self.profile = self._load_profile()
        self.node_id = os.getenv("NODE_ID", f"vinn-{profile_id}-{uuid.uuid4().hex[:8]}")
        self.wallet = os.getenv("WALLET_ADDRESS", "")
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.query_count = 0
        self.inai_earned = 0.0
        self.sessions: dict[str, list] = {}  # session_id -> message history

    def _load_profile(self) -> dict:
        p = PROFILES_DIR / f"{self.profile_id}.json"
        if p.exists():
            return json.loads(p.read_text())
        return {"name": self.profile_id, "emoji": "⬡", "niche": self.profile_id}

    def get_cached_datasets(self) -> list[dict]:
        """Return all datasets from connector registry for this profile."""
        results = []
        reg_path = CONNECTOR_DIR / "registry.json"
        if reg_path.exists():
            reg = json.loads(reg_path.read_text())
            datasets = reg.get("datasets", {})
            for ds_id, ds in datasets.items():
                results.append({"id": ds_id, **ds})
        # Also check node_registry
        node_reg = DATA_DIR / "node_registry.json"
        if node_reg.exists():
            nreg = json.loads(node_reg.read_text())
            nodes_raw = nreg.get("nodes", {})
            nodes_iter = nodes_raw.values() if isinstance(nodes_raw, dict) else nodes_raw
            for n in nodes_iter:
                if not isinstance(n, dict):
                    continue
                if n.get("vertical") == self.profile_id or not self.profile_id:
                    for ds in n.get("datasets", []):
                        if isinstance(ds, dict) and not any(r.get("id") == ds.get("id") for r in results):
                            results.append(ds)
        return results

    def get_dataset(self, ds_id: str) -> Optional[dict]:
        datasets = self.get_cached_datasets()
        for ds in datasets:
            if ds.get("id") == ds_id:
                return ds
        # Try loading raw dataset file
        raw = BASE / f"{ds_id}_dataset.json"
        if raw.exists():
            return json.loads(raw.read_text())
        return None

    def search_datasets(self, query: str, max_results: int = 10) -> tuple[str, int, str]:
        """
        Simple keyword search across cached dataset records.
        Returns (answer_text, records_scanned, dataset_id).
        """
        query_lower = query.lower()
        all_records = []
        dataset_id = None
        freshness = "unknown"

        # Load raw dataset files from BASE
        for json_file in BASE.glob("*_dataset.json"):
            try:
                data = json.loads(json_file.read_text())
                meta = data.get("meta", {})
                if self.profile_id in json_file.name or True:  # search all
                    dataset_id = meta.get("dataset_id", json_file.stem)
                    freshness = meta.get("generated_at", "unknown")
                    # Try 'data' key first, then flatten all top-level lists
                    records = data.get("data", None)
                    if isinstance(records, list) and records:
                        all_records.extend(records)
                    elif isinstance(records, dict):
                        for k, v in records.items():
                            if isinstance(v, list):
                                all_records.extend(v)
                    else:
                        # Flatten: collect all list/dict values from top level
                        for k, v in data.items():
                            if k == "meta":
                                continue
                            if isinstance(v, list):
                                all_records.extend(v)
                            elif isinstance(v, dict):
                                # Convert single dict to record
                                all_records.append({"section": k, **v})
            except Exception:
                pass

        # Load connector registry datasets
        reg_path = CONNECTOR_DIR / "registry.json"
        if reg_path.exists():
            try:
                reg = json.loads(reg_path.read_text())
                for ds_id, ds in reg.get("datasets", {}).items():
                    dataset_id = ds_id
                    freshness = ds.get("last_updated", "unknown")
            except Exception:
                pass

        if not all_records:
            return (
                f"No cached data found for '{query}'. "
                f"The {self.profile['name']} node publishes to the Inflectiv marketplace "
                f"on its {self.profile.get('refresh_schedule','regular')} schedule. "
                f"Query the marketplace at api.inflectiv.ai for the latest datasets.",
                0, dataset_id or "none"
            )

        # Score records by query relevance
        scored = []
        for rec in all_records:
            rec_str = json.dumps(rec).lower()
            score = sum(1 for word in query_lower.split() if word in rec_str)
            if score > 0:
                scored.append((score, rec))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:max_results]

        if not top:
            answer = (
                f"No records directly matching '{query}' found in the {self.profile['name']} cache "
                f"({len(all_records)} records scanned). Try a broader query or check the "
                f"Inflectiv marketplace for the full dataset."
            )
        else:
            lines = [f"Found {len(top)} relevant records from {self.profile['name']} cache:\n"]
            for i, (score, rec) in enumerate(top[:5], 1):
                # Format record nicely
                if isinstance(rec, dict):
                    key_fields = list(rec.items())[:4]
                    rec_summary = " | ".join(f"{k}: {v}" for k, v in key_fields if v)
                else:
                    rec_summary = str(rec)[:120]
                lines.append(f"{i}. {rec_summary}")
            if len(top) > 5:
                lines.append(f"... and {len(top)-5} more matching records.")
            answer = "\n".join(lines)

        return answer, len(all_records), dataset_id or "local_cache"

    def register_query(self, price: float):
        self.query_count += 1
        self.inai_earned += price


# ── App Factory ───────────────────────────────────────────────────────────────

def create_app(profile_id: str) -> FastAPI:
    node = NodeState(profile_id)
    profile = node.profile
    price_per_query = float(profile.get("price_per_query", 0.001))

    app = FastAPI(
        title=f"Inflectiv {profile.get('name','Node')}",
        description=f"Vertical Intelligence Node — {profile.get('niche','')}",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── GET / ─────────────────────────────────────────────────────────────────
    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def root():
        emoji = profile.get("emoji", "⬡")
        name = profile.get("name", "Inflectiv Node")
        niche = profile.get("niche", "")
        refresh = profile.get("refresh_schedule", "daily")
        price = price_per_query
        datasets = node.get_cached_datasets()
        ds_count = len(datasets)
        return f"""
        <!DOCTYPE html><html><head>
        <title>{name}</title>
        <meta charset="UTF-8">
        <style>
          body{{background:#1b0c25;color:#f0e8fc;font-family:Inter,sans-serif;display:flex;
               align-items:center;justify-content:center;min-height:100vh;margin:0}}
          .card{{background:#241035;border:1px solid #3d2557;border-radius:20px;padding:48px;
                 max-width:480px;width:100%;text-align:center}}
          .emoji{{font-size:56px;margin-bottom:16px}}
          h1{{font-size:24px;font-weight:700;color:#e8985d;margin-bottom:8px}}
          p{{color:#9080a8;font-size:14px;line-height:1.6;margin:0 0 20px}}
          .grid{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:24px 0;text-align:left}}
          .stat{{background:#2e1a42;border-radius:10px;padding:14px}}
          .stat-label{{font-size:10px;color:#6b5a80;text-transform:uppercase;letter-spacing:1px}}
          .stat-val{{font-size:18px;font-weight:700;color:#e8985d;font-family:monospace}}
          .links{{display:flex;gap:10px;justify-content:center;flex-wrap:wrap;margin-top:8px}}
          a{{color:#e8985d;text-decoration:none;font-size:13px;background:#2e1a42;
             border:1px solid #3d2557;padding:6px 14px;border-radius:20px}}
          a:hover{{border-color:#e8985d}}
          .dot{{width:8px;height:8px;background:#2dd4a0;border-radius:50%;
                display:inline-block;margin-right:6px;animation:pulse 2s infinite}}
          @keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.4}}}}
        </style></head><body>
        <div class="card">
          <div class="emoji">{emoji}</div>
          <h1>{name}</h1>
          <p><span class="dot"></span>Live · {niche}</p>
          <div class="grid">
            <div class="stat"><div class="stat-label">Refresh</div><div class="stat-val">{refresh}</div></div>
            <div class="stat"><div class="stat-label">Price/query</div><div class="stat-val">{price} $INAI</div></div>
            <div class="stat"><div class="stat-label">Datasets</div><div class="stat-val">{ds_count}</div></div>
            <div class="stat"><div class="stat-label">Queries served</div><div class="stat-val">{node.query_count}</div></div>
          </div>
          <div class="links">
            <a href="/docs">📖 API Docs</a>
            <a href="/health">❤️ Health</a>
            <a href="/datasets">📦 Datasets</a>
            <a href="/node">🔍 Node Info</a>
          </div>
        </div></body></html>
        """

    # ── GET /health ───────────────────────────────────────────────────────────
    @app.get("/health")
    async def health():
        datasets = node.get_cached_datasets()
        return {
            "status": "ok",
            "node_id": node.node_id,
            "profile": profile_id,
            "name": profile.get("name"),
            "datasets_cached": len(datasets),
            "queries_served": node.query_count,
            "inai_earned": round(node.inai_earned, 4),
            "uptime_since": node.started_at,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # ── GET /node ─────────────────────────────────────────────────────────────
    @app.get("/node")
    async def node_info():
        """Full node registration card — used by discovery services."""
        datasets = node.get_cached_datasets()
        return {
            "node_id": node.node_id,
            "profile": profile_id,
            "name": profile.get("name"),
            "emoji": profile.get("emoji"),
            "niche": profile.get("niche"),
            "description": profile.get("description"),
            "refresh_schedule": profile.get("refresh_schedule"),
            "price_per_query": price_per_query,
            "wallet": node.wallet,
            "schema_version": profile.get("dataset_schema", {}).get("version"),
            "endpoints": {
                "rest": "/query",
                "a2a": "/a2a",
                "datasets": "/datasets",
                "health": "/health",
            },
            "datasets_available": len(datasets),
            "queries_served": node.query_count,
            "inai_earned": round(node.inai_earned, 4),
            "started_at": node.started_at,
            "inflectiv_marketplace": f"https://app.inflectiv.ai/nodes/{node.node_id}",
        }

    # ── GET /datasets ─────────────────────────────────────────────────────────
    @app.get("/datasets")
    async def list_datasets():
        datasets = node.get_cached_datasets()
        return {
            "node_id": node.node_id,
            "count": len(datasets),
            "datasets": datasets,
        }

    # ── GET /datasets/{ds_id} ─────────────────────────────────────────────────
    @app.get("/datasets/{ds_id}")
    async def get_dataset(ds_id: str):
        ds = node.get_dataset(ds_id)
        if not ds:
            raise HTTPException(status_code=404, detail=f"Dataset '{ds_id}' not found")
        node.register_query(price_per_query)
        return ds

    # ── POST /query ───────────────────────────────────────────────────────────
    @app.post("/query", response_model=QueryResponse)
    async def query(req: QueryRequest):
        """
        Natural-language query against this node's cached datasets.
        Returns structured answer + metadata.
        """
        answer, records_scanned, ds_id = node.search_datasets(req.q, req.max_results)
        node.register_query(price_per_query)

        # Freshness from registry
        freshness = "unknown"
        reg_path = CONNECTOR_DIR / "registry.json"
        if reg_path.exists():
            try:
                reg = json.loads(reg_path.read_text())
                datasets = reg.get("datasets", {})
                if datasets:
                    first = next(iter(datasets.values()))
                    freshness = first.get("last_updated", "unknown")
            except Exception:
                pass

        return QueryResponse(
            answer=answer,
            dataset_id=req.dataset_id or ds_id,
            records_scanned=records_scanned,
            freshness=freshness,
            node_id=node.node_id,
            inai_cost=price_per_query,
        )

    # ── POST /a2a  (FastA2A v0.2 compatible) ──────────────────────────────────
    @app.post("/a2a")
    async def a2a(request: Request):
        """
        FastA2A v0.2 compatible agent-to-agent endpoint.
        Accepts messages from any Agent Zero / OpenClaw agent via a2a_chat tool.
        """
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON")

        # Handle both JSON-RPC style and direct task style
        method = body.get("method", "message/send")
        rpc_id = body.get("id")
        params = body.get("params", body)  # fallback: treat whole body as params

        # Extract message text
        message_text = ""
        session_id = params.get("sessionId") or params.get("id") or str(uuid.uuid4())

        msg = params.get("message", {})
        if isinstance(msg, dict):
            parts = msg.get("parts", [])
            for part in parts:
                if isinstance(part, dict) and part.get("type") == "text":
                    message_text += part.get("text", "")
        elif isinstance(msg, str):
            message_text = msg

        if not message_text:
            message_text = params.get("text", str(params))

        # Maintain session history
        if session_id not in node.sessions:
            node.sessions[session_id] = []
        node.sessions[session_id].append({"role": "user", "text": message_text})

        # Build context from session history for better responses
        history_ctx = ""
        if len(node.sessions[session_id]) > 1:
            prev = node.sessions[session_id][-3:-1]  # last 2 exchanges
            history_ctx = "Previous context: " + " | ".join(
                f"{m['role']}: {m['text'][:100]}" for m in prev
            ) + "\n\n"

        # Query the node's datasets
        answer, records_scanned, ds_id = node.search_datasets(message_text)
        node.register_query(price_per_query)

        # Wrap answer with node identity
        full_response = (
            f"{history_ctx}"
            f"{profile.get('emoji','')} **{profile.get('name','Inflectiv Node')}** | "
            f"{profile.get('niche','')}\n\n"
            f"{answer}\n\n"
            f"---\n"
            f"*{records_scanned} records scanned · {price_per_query} $INAI · "
            f"Node: `{node.node_id}`*"
        )

        node.sessions[session_id].append({"role": "assistant", "text": full_response})

        # FastA2A v0.2 response format
        task_id = str(uuid.uuid4())
        response_body = {
            "id": task_id,
            "sessionId": session_id,
            "status": {"state": "completed"},
            "result": {
                "role": "agent",
                "parts": [{"type": "text", "text": full_response}],
            },
            "metadata": {
                "node_id": node.node_id,
                "profile": profile_id,
                "records_scanned": records_scanned,
                "inai_cost": price_per_query,
            },
        }

        # Wrap in JSON-RPC if that's what was sent
        if "jsonrpc" in body:
            return {"jsonrpc": "2.0", "id": rpc_id, "result": response_body}
        return response_body

    # ── GET /a2a  (A2A agent card — discovery) ────────────────────────────────
    @app.get("/a2a")
    async def a2a_card():
        """A2A agent card for service discovery."""
        return {
            "name": profile.get("name"),
            "description": f"{profile.get('emoji','')} {profile.get('niche','')} intelligence node. "
                           f"Query structured datasets, get freshness scores, earn $INAI.",
            "url": f"/a2a",
            "version": "1.0.0",
            "capabilities": {"streaming": False, "pushNotifications": False},
            "skills": [
                {
                    "id": f"query_{profile_id}",
                    "name": f"Query {profile.get('name')}",
                    "description": f"Ask natural language questions about {profile.get('niche')}",
                    "examples": profile.get("example_queries", []),
                }
            ],
            "defaultInputModes": ["text/plain"],
            "defaultOutputModes": ["text/plain"],
        }

    return app


# ── Entry Point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Inflectiv Node API Server")
    parser.add_argument("--profile", default=os.getenv("PROFILE", "defi"))
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", 8765)))
    parser.add_argument("--host", default=os.getenv("HOST", "0.0.0.0"))
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    app = create_app(args.profile)
    profile_path = PROFILES_DIR / f"{args.profile}.json"
    if profile_path.exists():
        p = json.loads(profile_path.read_text())
        print(f"""
╔══════════════════════════════════════════════════════╗
║  {p.get('emoji','⬡')}  {p.get('name','Inflectiv Node'):<44} ║
║  REST  → http://{args.host}:{args.port}/query          ║
║  A2A   → http://{args.host}:{args.port}/a2a            ║
║  Docs  → http://{args.host}:{args.port}/docs           ║
╚══════════════════════════════════════════════════════╝
        """)

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info",
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
