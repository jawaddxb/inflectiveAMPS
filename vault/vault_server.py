"""
Inflectiv Vault Server — personal memory + credentials + network intelligence
Port 8766 (8765 used by VINN node API)
"""
import os
import sys
import json
import re
import uuid
import fcntl
from datetime import datetime, timezone
from contextlib import asynccontextmanager, contextmanager
from typing import Optional, Literal

from fastapi import FastAPI, HTTPException, Header, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel, Field

sys.path.insert(0, os.path.dirname(__file__))
from auth import VaultAuth
from key_store import KeyStore
from memory_store import MemoryStore
from query_engine import QueryEngine
from amps import export_vault, import_amps as _import_amps

# ── Config ──────────────────────────────────────────────────────────────────
VAULT_ROOT   = os.environ.get("VAULT_ROOT", "/vault")
CONFIG_PATH  = os.path.join(VAULT_ROOT, "vault_config.json")
SECRETS_PATH = os.path.join(VAULT_ROOT, "secrets")
MEMORY_PATH  = os.path.join(VAULT_ROOT, "memory")
MASTER_PASS  = os.environ.get("VAULT_MASTER_PASSWORD", "changeme")
_vault_env   = os.environ.get("VAULT_ENV", "production")
if MASTER_PASS == "changeme":
    if _vault_env == "production":
        print("FATAL: VAULT_MASTER_PASSWORD is set to default 'changeme'.", file=sys.stderr)
        print("   Set a strong VAULT_MASTER_PASSWORD before running in production.", file=sys.stderr)
        sys.exit(1)
    else:
        print("⚠️  WARNING: VAULT_MASTER_PASSWORD not set — using default 'changeme'", file=sys.stderr)
        print("   Set VAULT_MASTER_PASSWORD env var before storing real secrets.", file=sys.stderr)
PORT         = int(os.environ.get("VAULT_PORT", 8766))

# ── Globals (init on startup) ────────────────────────────────────────────────
auth_mgr: VaultAuth = None
key_store: KeyStore = None
mem_store: MemoryStore = None
q_engine:  QueryEngine = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global auth_mgr, key_store, mem_store, q_engine
    os.makedirs(VAULT_ROOT, exist_ok=True)
    auth_mgr  = VaultAuth(CONFIG_PATH)
    key_store = KeyStore(MASTER_PASS, SECRETS_PATH)
    # Memory encryption: enabled by default, disable with VAULT_ENCRYPT_MEMORY=false
    _encrypt_memory = os.environ.get("VAULT_ENCRYPT_MEMORY", "true").lower() != "false"
    _mem_key = MASTER_PASS if _encrypt_memory else None
    if not _encrypt_memory:
        print("[vault] WARNING: Memory encryption disabled (VAULT_ENCRYPT_MEMORY=false)", file=sys.stderr)
    mem_store = MemoryStore(MEMORY_PATH, encryption_key=_mem_key)
    # Load user-configured shared/knowledge vaults from VAULTS_CONFIG yaml
    _vault_configs = []
    _vc_path = os.environ.get("VAULTS_CONFIG", "")
    if _vc_path and os.path.exists(_vc_path):
        try:
            import yaml as _yaml
            with open(_vc_path) as _vf:
                _vc_data = _yaml.safe_load(_vf)
            for _vc in (_vc_data.get("knowledge_vaults") or []):
                if _vc.get("path") and os.path.isdir(_vc["path"]):
                    _vault_configs.append({
                        "name": _vc.get("name", "shared"),
                        "path": _vc["path"],
                        "type": _vc.get("type", "shared")
                    })
            print(f"   Loaded {len(_vault_configs)} shared vault(s) from {_vc_path}")
        except ImportError:
            print("   ⚠️  PyYAML not installed — VAULTS_CONFIG ignored. pip install pyyaml", flush=True)
        except Exception as _e:
            print(f"   ⚠️  Could not load VAULTS_CONFIG: {_e}", flush=True)
    q_engine  = QueryEngine(mem_store, vault_configs=_vault_configs)
    # Create default owner token if vault is brand new
    if not auth_mgr.list_tokens():
        default_token = auth_mgr.create_token(
            role="owner", agent="default", label="initial-owner"
        )
        print(f"\n🔑 VAULT READY — save your owner token:\n   {default_token}\n")
    print(f"🏦 Inflectiv Vault {auth_mgr.vault_id} running on port {PORT}")
    if _vault_env != "production":
        print(f"   ⚠️  Dev mode active (VAULT_ENV={_vault_env}) — env-token bypass enabled", file=sys.stderr)
    yield

app = FastAPI(
    title="Inflectiv Vault",
    description="Personal memory, credentials, and network intelligence for agents.",
    version="1.0.0",
    lifespan=lifespan
)
_cors_origins = os.environ.get("VAULT_CORS_ORIGINS", "http://localhost:*,http://127.0.0.1:*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["*"], allow_headers=["*"]
)

# ── Auth helpers ─────────────────────────────────────────────────────────────
def require_auth(x_vault_token: str = Header(...)):
    record = auth_mgr.validate(x_vault_token)
    if not record:
        raise HTTPException(status_code=401, detail="Invalid or expired vault token")
    return record

def require_owner(token=Depends(require_auth)):
    if token.role != "owner":
        raise HTTPException(status_code=403, detail="Owner token required for this operation")
    return token

def _token_from_query_or_header(
    request: Request,
    x_vault_token: Optional[str] = Header(None),
) -> str:
    """Extract token from header or ?token= query param (for browser UI endpoints)."""
    token = x_vault_token or request.query_params.get("token")
    if not token:
        raise HTTPException(status_code=401, detail="Missing vault token (header or ?token= param)")
    return token

def require_auth_ui(request: Request, x_vault_token: Optional[str] = Header(None)):
    """Auth for HTML UI endpoints — accepts header or query param."""
    token = _token_from_query_or_header(request, x_vault_token)
    record = auth_mgr.validate(token)
    if not record:
        raise HTTPException(status_code=401, detail="Invalid or expired vault token")
    return record

def require_owner_ui(token=Depends(require_auth_ui)):
    """Owner auth for HTML UI endpoints — accepts header or query param."""
    if token.role != "owner":
        raise HTTPException(status_code=403, detail="Owner token required for this operation")
    return token

def _check_ip_rate_limit(request: Request):
    """Rate limit by client IP as secondary brute-force protection."""
    client_ip = request.client.host if request.client else "unknown"
    if not auth_mgr.rate_limiter.check(f"ip:{client_ip}"):
        retry_after = auth_mgr.rate_limiter.seconds_until_reset(f"ip:{client_ip}")
        raise HTTPException(
            status_code=429,
            detail="Too many authentication attempts. Try again later.",
            headers={"Retry-After": str(retry_after)},
        )

# ── Models ───────────────────────────────────────────────────────────────────
class SecretWrite(BaseModel):
    value: str = Field(..., max_length=100_000)

class MemoryWrite(BaseModel):
    content: str = Field(..., max_length=1_000_000)
    mode: Literal["write", "append"] = "write"

class QueryRequest(BaseModel):
    q: str = Field(..., max_length=10_000)
    include_network: bool = True

class TokenCreate(BaseModel):
    role: str = "subscriber"
    agent: str = "agent"
    label: str = ""
    expires: Optional[str] = None

class ContributeRequest(BaseModel):
    content: str = Field(..., max_length=500_000)
    category: Optional[str] = None

# ── Routes: Health & Info ────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0"
    }

@app.get("/vault/info", dependencies=[Depends(require_auth)])
def vault_info():
    files = mem_store.list_files()
    secrets = key_store.list_secrets()
    return {
        "vault_id": auth_mgr.vault_id,
        "memory_files": len(files),
        "secrets_stored": len(secrets),
        "token_count": len(auth_mgr.list_tokens()),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# ── Routes: Secrets ──────────────────────────────────────────────────────────
@app.get("/vault/secrets", dependencies=[Depends(require_owner)])
def list_secrets():
    return {"secrets": key_store.list_secrets()}

@app.get("/vault/secrets/{name}", dependencies=[Depends(require_owner)])
def get_secret(name: str):
    value = key_store.retrieve(name)
    if value is None:
        raise HTTPException(status_code=404, detail=f"Secret '{name}' not found")
    return {"name": name, "value": value}

@app.post("/vault/secrets/{name}", dependencies=[Depends(require_owner)])
def set_secret(name: str, body: SecretWrite):
    key_store.store(name, body.value)
    return {"stored": name, "ok": True}

@app.delete("/vault/secrets/{name}", dependencies=[Depends(require_owner)])
def delete_secret(name: str):
    ok = key_store.delete(name)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Secret '{name}' not found")
    return {"deleted": name}

# ── Routes: Memory ───────────────────────────────────────────────────────────
@app.get("/vault/memory", dependencies=[Depends(require_auth)])
def list_memory():
    return {"files": mem_store.list_files()}

@app.get("/vault/memory/context", dependencies=[Depends(require_auth)])
def session_context():
    """Return auto-loaded session context (MEMORY.md + SOUL.md + recent logs)"""
    return {"context": mem_store.load_session_context()}

@app.get("/vault/memory/{filepath:path}", dependencies=[Depends(require_auth)])
def read_memory(filepath: str):
    try:
        content = mem_store.read(filepath)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Path traversal denied")
    if content is None:
        raise HTTPException(status_code=404, detail=f"Memory file '{filepath}' not found")
    return {"file": filepath, "content": content}

@app.post("/vault/memory/{filepath:path}", dependencies=[Depends(require_owner)])
def write_memory(filepath: str, body: MemoryWrite):
    try:
        if body.mode == "append":
            result = mem_store.write(filepath, body.content, mode="append")
        else:
            result = mem_store.write(filepath, body.content, mode="write")
    except PermissionError:
        raise HTTPException(status_code=403, detail="Path traversal denied")
    return {"ok": True, **result}

@app.post("/vault/memory/log/today", dependencies=[Depends(require_owner)])
def append_today_log(body: MemoryWrite):
    log_file = mem_store.today_log()
    result = mem_store.append(log_file, body.content)
    return {"ok": True, "file": log_file, **result}

# ── Routes: Query ─────────────────────────────────────────────────────────────
@app.post("/vault/query", dependencies=[Depends(require_auth)])
def query(body: QueryRequest):
    """Unified vault query — personal + knowledge vaults + VINN network"""
    # Track query count for ratio scoring
    _increment_stat("queries")
    # Ratio enforcement: after grace period, throttle if ratio too low
    _sp = _stats_path()
    stats_data = json.loads(open(_sp).read()) if os.path.exists(_sp) else {}
    grace_active_now, _ = _is_grace_active()
    if not grace_active_now:
        approved = stats_data.get("approved_contributions", 0)
        queries_made = stats_data.get("queries", 0)
        ratio = approved / max(queries_made, 1)
        if ratio < 0.05 and queries_made > 50:
            return JSONResponse(status_code=429, content={
                "error": "query_limit_reached",
                "message": "Contribution ratio too low. Share structured intelligence to continue querying.",
                "ratio": ratio,
                "required_ratio": 0.05,
                "tip": "POST /vault/contribute to improve your ratio"
            })
    result = q_engine.query(body.q, include_network=body.include_network)
    return result

@app.post("/vault/classify", dependencies=[Depends(require_auth)])
def classify(body: ContributeRequest):
    """Classify text against VINN taxonomy — returns matching categories"""
    matches = q_engine.classify(body.content)
    return {
        "input": body.content[:200],
        "classifications": matches,
        "top_category": matches[0] if matches else None
    }

# ── PII Sanitisation ─────────────────────────────────────────────────────────
_personal_patterns = [
    # ── Behavioral patterns ──
    r"\bmy\s+(portfolio|wallet|position|holdings?|account|balance)\b",
    r"\bfor\s+\[?\w+\]?'s\b",
    r"\b(user|client|customer):\s*\w+",

    # ── Email addresses ──
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",

    # ── Crypto wallet addresses ──
    r"\b0x[a-fA-F0-9]{40}\b",                    # Ethereum/EVM
    r"\b(bc1|[13])[a-zA-HJ-NP-Z0-9]{25,39}\b",  # Bitcoin
    r"\b[1-9A-HJ-NP-Za-km-z]{32,44}\b",          # Solana/Base58 (broad)

    # ── Phone numbers (international) ──
    r"\b\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",

    # ── IP addresses ──
    r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",

    # ── API keys / tokens (common prefixes) ──
    r"\b(sk-|pk-|vtok_|ghp_|gho_|github_pat_|xoxb-|xoxp-|AKIA)[A-Za-z0-9_-]{10,}\b",

    # ── SSN pattern ──
    r"\b\d{3}-\d{2}-\d{4}\b",
]

def _sanitise_content(content: str) -> tuple[str, list[dict], list[str]]:
    """Sanitise PII from content. Returns (sanitised_text, redaction_report, stripped_terms)."""
    sanitised = content
    report = []
    for pat in _personal_patterns:
        found = re.findall(pat, sanitised, re.IGNORECASE)
        if found:
            count = len(found)
            sanitised = re.sub(pat, "[redacted]", sanitised, flags=re.IGNORECASE)
            report.append({
                "pattern": pat[:60],
                "matches": [str(m)[:40] for m in found[:5]],
                "count": count,
            })
    stripped_terms = []
    for entry in report:
        stripped_terms.extend(entry["matches"])
    return sanitised, report, stripped_terms

# ── Routes: Contribute ────────────────────────────────────────────────────────
@app.post("/vault/contribute", dependencies=[Depends(require_owner)])
def contribute(body: ContributeRequest):
    """
    Sanitise + classify content, stage for contribution to Inflectiv VINN.
    Returns sanitised diff and classification for user approval.
    """
    sanitised, redaction_report, stripped = _sanitise_content(body.content)

    classifications = q_engine.classify(sanitised)
    top = classifications[0] if classifications else None

    # Log to today's contribution staging area
    staging = {
        "id": str(uuid.uuid4()),
        "original_length": len(body.content),
        "sanitised": sanitised,
        "stripped_terms": stripped,
        "redaction_report": redaction_report,
        "classifications": classifications,
        "staged_at": datetime.now(timezone.utc).isoformat()
    }
    staging_path = os.path.join(VAULT_ROOT, "staging", "pending.jsonl")
    os.makedirs(os.path.dirname(staging_path), exist_ok=True)
    with open(staging_path, "a") as f:
        f.write(json.dumps(staging) + "\n")
    _increment_stat("staged")

    return {
        "contribution_id": staging["id"],
        "original": body.content[:300],
        "sanitised": sanitised[:300],
        "stripped": stripped,
        "redaction_report": redaction_report,
        "top_category": top,
        "all_categories": classifications,
        "status": "staged_for_approval",
        "message": "Review the sanitised diff. POST /vault/pending/{contribution_id}/approve to publish."
    }

@app.get("/vault/contribute/pending", dependencies=[Depends(require_owner)])
def pending_contributions():
    staging_path = os.path.join(VAULT_ROOT, "staging", "pending.jsonl")
    if not os.path.exists(staging_path):
        return {"pending": [], "count": 0}
    items = []
    with open(staging_path) as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return {"pending": items[-20:], "count": len(items)}

# ── Routes: Stats ────────────────────────────────────────────────────────────
def _stats_path():
    return os.path.join(VAULT_ROOT, "staging", "stats.json")

def _is_grace_active() -> tuple[bool, int]:
    """Check if 14-day grace period is active. Returns (active, days_remaining)."""
    config_path = os.path.join(VAULT_ROOT, "vault_config.json")
    try:
        cfg = json.loads(open(config_path).read()) if os.path.exists(config_path) else {}
        created = datetime.fromisoformat(
            cfg.get("created_at", datetime.now(timezone.utc).isoformat())
        )
        age_days = (datetime.now(timezone.utc) - created).days
        return age_days < 14, max(0, 14 - age_days)
    except Exception:
        return True, 14

@contextmanager
def _locked_file(path: str, mode: str = "r+"):
    """Context manager for exclusive file locking on read-modify-write operations."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write("{}")
    f = open(path, mode)
    try:
        fcntl.flock(f, fcntl.LOCK_EX)
        yield f
    finally:
        fcntl.flock(f, fcntl.LOCK_UN)
        f.close()

def _increment_stat(key: str, amount: int = 1):
    sp = _stats_path()
    with _locked_file(sp, "r+") as f:
        try:
            stats = json.loads(f.read())
        except Exception:
            stats = {}
        stats[key] = stats.get(key, 0) + amount
        f.seek(0)
        f.truncate()
        f.write(json.dumps(stats))

@app.get("/vault/stats", dependencies=[Depends(require_auth)])
def vault_stats():
    """Ratio tracking: queries made vs contributions staged + simulated $INAI earnings"""
    sp = _stats_path()
    stats = json.loads(open(sp).read()) if os.path.exists(sp) else {}
    queries = stats.get("queries", 0)
    contributions = stats.get("approved_contributions", 0)
    staged = stats.get("staged", 0)
    # Ratio: contributions / max(queries,1)
    ratio = round(contributions / max(queries, 1), 3)
    # Grace period: 14 days from vault creation
    grace_active, grace_days_remaining = _is_grace_active()
    # Simulated $INAI: 0.5 per approved contribution, 0.1 per query on shared vault
    inai_earned = round(contributions * 0.5, 2)
    access_tier = "grace" if grace_active else ("full" if ratio >= 0.1 else "limited")
    return {
        "queries_made": queries,
        "contributions_staged": staged,
        "contributions_approved": contributions,
        "ratio": ratio,
        "access_tier": access_tier,
        "grace_period_active": grace_active,
        "grace_days_remaining": grace_days_remaining,
        "inai_earned": inai_earned,
        "inai_pending": round(staged * 0.3, 2),
        "note": "Earn $INAI by contributing structured intelligence to the network"
    }

# ── Routes: Approve/Reject Contributions ──────────────────────────────────────
@app.post("/vault/pending/{contrib_id}/approve", dependencies=[Depends(require_owner)])
def approve_contribution(contrib_id: str):
    """Approve a staged contribution — publishes to VINN and credits ratio"""
    staging_path = os.path.join(VAULT_ROOT, "staging", "pending.jsonl")
    approved_path = os.path.join(VAULT_ROOT, "staging", "approved.jsonl")
    if not os.path.exists(staging_path):
        raise HTTPException(404, "No staged contributions")
    with _locked_file(staging_path, "r+") as f:
        items, found = [], None
        for line in f:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            if item.get("id") == contrib_id:
                found = item
            else:
                items.append(line)
        if not found:
            raise HTTPException(404, f"Contribution {contrib_id} not found")
        f.seek(0)
        f.truncate()
        f.write("\n".join(items) + ("\n" if items else ""))
    os.makedirs(os.path.dirname(approved_path), exist_ok=True)
    found["approved_at"] = datetime.now(timezone.utc).isoformat()
    with open(approved_path, "a") as af:
        fcntl.flock(af, fcntl.LOCK_EX)
        af.write(json.dumps(found) + "\n")
        fcntl.flock(af, fcntl.LOCK_UN)
    _increment_stat("approved_contributions")
    return {"approved": contrib_id, "inai_earned": 0.5,
            "message": "Contribution published to VINN. +0.5 $INAI credited."}

@app.delete("/vault/pending/{contrib_id}", dependencies=[Depends(require_owner)])
def reject_contribution(contrib_id: str):
    """Reject and discard a staged contribution"""
    staging_path = os.path.join(VAULT_ROOT, "staging", "pending.jsonl")
    if not os.path.exists(staging_path):
        raise HTTPException(404, "No staged contributions")
    with _locked_file(staging_path, "r+") as f:
        items, found = [], False
        for line in f:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            if item.get("id") == contrib_id:
                found = True
            else:
                items.append(line)
        if not found:
            raise HTTPException(404, f"Contribution {contrib_id} not found")
        f.seek(0)
        f.truncate()
        f.write("\n".join(items) + ("\n" if items else ""))
    return {"rejected": contrib_id, "message": "Contribution discarded."}


# ── Routes: Dashboard UI ────────────────────────────────────────────────────
@app.get("/ui/dashboard", response_class=HTMLResponse, dependencies=[Depends(require_auth_ui)])
def dashboard_ui():
    """$INAI earnings + ratio dashboard"""
    import os as _os
    html_path = _os.path.join(_os.path.dirname(__file__), "dashboard.html")
    if not _os.path.exists(html_path):
        return HTMLResponse("<h1>dashboard.html not found</h1>", status_code=404)

    with open(html_path) as _f:
        html = _f.read()

    # Use vault_stats() which computes all derived fields correctly
    _vs = vault_stats()
    queries   = _vs.get("queries_made", 0)
    staged    = _vs.get("contributions_staged", 0)
    approved  = _vs.get("contributions_approved", 0)
    ratio     = _vs.get("ratio", 0.0)
    inai_e    = _vs.get("inai_earned", 0.0)
    inai_p    = _vs.get("inai_pending", 0.0)
    grace     = _vs.get("grace_period_active", True)
    days_left = _vs.get("grace_days_remaining", 14)
    tier      = _vs.get("access_tier", "grace")

    tier_colors = {
        "grace":     ("#4CAF50", "#4CAF5022", "#4CAF5044"),
        "active":    ("#00d4ff", "#00d4ff22", "#00d4ff44"),
        "limited":   ("#FF9800", "#FF980022", "#FF980044"),
        "suspended": ("#F44336", "#F4433622", "#F4433644"),
    }
    tc, tc_bg, tc_border = tier_colors.get(tier, ("#9E9E9E", "#9E9E9E22", "#9E9E9E44"))
    ratio_pct = min(int(ratio / 0.20 * 100), 100)

    grace_icon = "&#127807;" if grace else "&#9889;"
    if grace:
        grace_msg = "<strong>Grace Period Active</strong> &mdash; {} days remaining. Explore freely.".format(days_left)
        grace_bg, grace_border = "#4CAF5011", "#4CAF5033"
    else:
        grace_msg = "<strong>Active Contributor</strong> &mdash; Keep contributing to maintain access."
        grace_bg, grace_border = "#00d4ff11", "#00d4ff33"

    tier_desc = "Grace period" if grace else "Ratio-based access"

    html = (html
        .replace("GRACE_BG",          grace_bg)
        .replace("GRACE_BORDER",      grace_border)
        .replace("GRACE_ICON",        grace_icon)
        .replace("GRACE_MESSAGE",     grace_msg)
        .replace("STAT_QUERIES",      str(queries))
        .replace("STAT_APPROVED",     str(approved))
        .replace("STAT_STAGED",       str(staged))
        .replace("STAT_INAI_EARNED",  "{:.4f}".format(inai_e))
        .replace("STAT_INAI_PENDING", "{:.4f}".format(inai_p))
        .replace("STAT_INAI_TOTAL",   "{:.4f}".format(inai_e + inai_p))
        .replace("STAT_RATIO",        "{:.3f}".format(ratio))
        .replace("STAT_TIER",         tier.upper())
        .replace("TIER_COLOR",        tc)
        .replace("TIER_BG",           tc_bg)
        .replace("TIER_BORDER",       tc_border)
        .replace("TIER_DESC",         tier_desc)
        .replace("RATIO_PCT",         str(ratio_pct))
    )
    return HTMLResponse(html)

# ── Routes: Approval UI ────────────────────────────────────────────────────────
@app.get("/ui/approve", response_class=HTMLResponse, dependencies=[Depends(require_owner_ui)])
def approval_ui():
    """HTML approval UI — review and approve/reject staged contributions"""
    ui_path = os.path.join(os.path.dirname(__file__), "approval_ui.html")
    if os.path.exists(ui_path):
        return open(ui_path).read()
    return "<h1>Approval UI not found — place approval_ui.html in vault/</h1>"

# ── Routes: Tokens ────────────────────────────────────────────────────────────
@app.get("/vault/tokens", dependencies=[Depends(require_owner)])
def list_tokens():
    return {"tokens": auth_mgr.list_tokens()}

@app.post("/vault/tokens", dependencies=[Depends(require_owner)])
def create_token(body: TokenCreate):
    token = auth_mgr.create_token(
        role=body.role, agent=body.agent,
        label=body.label, expires=body.expires
    )
    return {
        "token": token,
        "role": body.role,
        "agent": body.agent,
        "note": "Save this token — it cannot be retrieved again."
    }


# ══════════════════════════════════════════════════════════════
# AMPS — Agent Memory Portability Standard (v1.0)
# ══════════════════════════════════════════════════════════════

class AMPSImportBody(BaseModel):
    amps_doc: dict
    overwrite: bool = False

@app.get("/vault/export",
         summary="Export vault to AMPS portable format",
         dependencies=[Depends(require_owner)])
def vault_export():
    """
    Export vault memory, identity, plan, and contribution history
    as an AMPS v1.0 JSON document.
    Secrets are never exported (empty array by spec).
    """
    try:
        # Read vault_id directly from config file
        _vc_file = os.path.join(VAULT_ROOT, "vault_config.json")
        _vault_id = "unknown"
        if os.path.exists(_vc_file):
            try:
                _vault_id = json.loads(open(_vc_file).read()).get("vault_id", "unknown")
            except Exception:
                pass
        doc = export_vault(
            vault_root=VAULT_ROOT,
            stats_path=_stats_path(),
            vault_id=_vault_id
        )
        return doc
    except Exception as e:
        raise HTTPException(500, f"Export failed: {e}")


@app.post("/vault/import",
          summary="Import an AMPS document into this vault",
          dependencies=[Depends(require_owner)])
def vault_import(body: AMPSImportBody):
    """
    Import an AMPS v1.0 JSON document into this vault.
    Memory is appended (existing content takes priority unless overwrite=true).
    Secrets in the import document are ignored.
    Migration notes and warnings are returned.
    """
    try:
        result = _import_amps(
            amps_doc=body.amps_doc,
            vault_root=VAULT_ROOT,
            overwrite=body.overwrite
        )
        return result
    except Exception as e:
        raise HTTPException(500, f"Import failed: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("vault_server:app", host="0.0.0.0", port=PORT, reload=False)
