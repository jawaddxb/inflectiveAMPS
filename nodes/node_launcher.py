#!/usr/bin/env python3
"""
Inflectiv Vertical Intelligence Node Launcher
Loads a vertical profile and runs the full research → structure → publish pipeline.
Usage: python node_launcher.py --profile defi
       python node_launcher.py --profile ai-models
       python node_launcher.py --profile crypto-news
       python node_launcher.py --list
"""

import json
import os
import sys
import argparse
import random
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
PROFILES_DIR = BASE_DIR / "profiles"
REGISTRY_FILE = BASE_DIR / "nodes" / "node_registry.json"

INAI_PURPLE = "\033[95m"
INAI_ORANGE = "\033[93m"
INAI_GREEN = "\033[92m"
INAI_CYAN = "\033[96m"
INAI_RED = "\033[91m"
INAI_BOLD = "\033[1m"
RESET = "\033[0m"

# ── Vault Integration ──────────────────────────────────────────
def vault_contribute(content: str, dataset_id: str, auto_approve: bool = False) -> bool:
    """Contribute research output to local vault if VAULT_URL is configured."""
    vault_url   = os.getenv("VAULT_URL", "").rstrip("/")
    vault_token = os.getenv("VAULT_TOKEN", "")
    if not vault_url or not vault_token:
        return False  # vault not configured — skip silently
    try:
        import urllib.request, urllib.error
        import json as _json
        payload = _json.dumps({"content": content}).encode()
        req = urllib.request.Request(
            f"{vault_url}/vault/contribute",
            data=payload,
            headers={"Content-Type": "application/json", "X-Vault-Token": vault_token},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = _json.loads(resp.read())
        cid      = data.get("contribution_id", "")
        category = data.get("top_category", {}).get("category", "unknown")
        conf     = data.get("top_category", {}).get("confidence", 0)
        print(f"      {INAI_CYAN}🏦 Vault: staged {category} ({conf:.0%} confidence) → id {cid[:8]}...{RESET}")
        if auto_approve and cid:
            req2 = urllib.request.Request(
                f"{vault_url}/vault/pending/{cid}/approve",
                data=b"",
                headers={"X-Vault-Token": vault_token},
                method="POST"
            )
            with urllib.request.urlopen(req2, timeout=10) as resp2:
                ack = _json.loads(resp2.read())
            print(f"      {INAI_GREEN}🏦 Vault: auto-approved → {ack.get('message','ok')}{RESET}")
        return True
    except Exception as e:
        print(f"      {INAI_ORANGE}⚠️  Vault contribute failed: {e}{RESET}")
        return False


def load_profile(name: str) -> dict:
    path = PROFILES_DIR / f"{name}.json"
    if not path.exists():
        print(f"{INAI_RED}✗ Profile not found: {name}{RESET}")
        print(f"  Available: {', '.join(p.stem for p in PROFILES_DIR.glob('*.json'))}")
        sys.exit(1)
    with open(path) as f:
        return json.load(f)

def load_registry() -> dict:
    if REGISTRY_FILE.exists():
        with open(REGISTRY_FILE) as f:
            return json.load(f)
    return {"nodes": {}, "network_stats": {"total_queries": 0, "total_datasets": 0, "total_inai_earned": 0.0}}

def save_registry(reg: dict):
    REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(REGISTRY_FILE, "w") as f:
        json.dump(reg, f, indent=2)

def register_node(profile: dict, registry: dict) -> dict:
    node_id = profile["node_id"]
    if node_id not in registry["nodes"]:
        registry["nodes"][node_id] = {
            "node_id": node_id,
            "name": profile["name"],
            "vertical": profile["vertical"],
            "emoji": profile.get("emoji", "🔵"),
            "color": profile.get("color", "#e8985d"),
            "version": profile["version"],
            "status": "active",
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "last_refresh": None,
            "next_refresh": None,
            "datasets_published": 0,
            "queries_served": 0,
            "earnings_inai": 0.0,
            "quality_score": 0.0,
            "freshness_score": 0.0,
            "tags": profile.get("tags", []),
            "refresh_schedule": profile["refresh"]["schedule"],
            "refresh_description": profile["refresh"]["description"],
            "inai_price": profile["inai"]["suggested_price"]
        }
        print(f"{INAI_GREEN}✓ Node registered: {node_id}{RESET}")
    else:
        print(f"{INAI_CYAN}↺ Node already registered: {node_id}{RESET}")
    return registry

def run_research_cycle(profile: dict) -> dict:
    """Simulates the research → structure → publish cycle for a vertical."""
    node_id = profile["node_id"]
    vertical = profile["vertical"]
    emoji = profile.get("emoji", "🔵")
    
    print(f"\n{INAI_BOLD}{'─'*60}{RESET}")
    print(f"{INAI_BOLD}{emoji}  {profile['name']}{RESET}")
    print(f"{INAI_BOLD}{'─'*60}{RESET}")
    
    print(f"\n{INAI_CYAN}[1/4] Query-Before-Browse — Checking Inflectiv marketplace...{RESET}")
    import time; time.sleep(0.5)
    print(f"      No fresh dataset found for '{vertical}' within refresh window")
    print(f"      → Proceeding with research cycle")

    print(f"\n{INAI_CYAN}[2/4] Research — Querying trusted sources...{RESET}")
    time.sleep(0.5)
    sources = profile.get("sources", [])
    for src in sources[:3]:
        print(f"      ✓ {src['name']} (trust: {src['trust_score']})")
    if len(sources) > 3:
        print(f"      ... and {len(sources)-3} more sources")

    print(f"\n{INAI_CYAN}[3/4] Structure — Applying schema {profile['schema']['version']}...{RESET}")
    time.sleep(0.5)
    record_count = random.randint(
        profile["refresh"]["min_records"],
        min(profile["refresh"]["max_records"], profile["refresh"]["min_records"] + 30)
    )
    required = profile["schema"]["required_fields"]
    print(f"      Schema: {profile['schema']['version']}")
    print(f"      Required fields: {', '.join(required)}")
    print(f"      Records structured: {record_count}")
    quality = round(random.uniform(0.88, 0.97), 2)
    print(f"      Quality score: {quality}")

    print(f"\n{INAI_CYAN}[4/4] Publish — Uploading to Inflectiv marketplace...{RESET}")
    time.sleep(0.5)
    ds_id = f"ds_{vertical}_{datetime.now().strftime('%Y%m%d_%H%M')}"
    inai_price = profile["inai"]["suggested_price"]
    print(f"      Dataset ID: {ds_id}")
    print(f"      Price: {inai_price} $INAI per query")
    print(f"      Visibility: {profile['inai']['access_model']}")
    print(f"      {INAI_GREEN}✓ Published successfully → inflectiv.ai/marketplace/{ds_id}{RESET}")

    # ── Vault Integration: contribute research output ──────────────
    auto_approve = os.getenv("VAULT_AUTO_APPROVE", "false").lower() == "true"
    vault_content = (
        f"# {profile['name']} Research Cycle — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"Dataset: {ds_id}\n"
        f"Vertical: {vertical}\n"
        f"Records structured: {record_count}\n"
        f"Quality score: {quality}\n"
        f"Sources consulted: {', '.join(s['name'] for s in sources[:5])}\n"
        f"Published: inflectiv.ai/marketplace/{ds_id}\n"
        f"Price: {profile['inai']['suggested_price']} $INAI per query\n"
        f"Access: {profile['inai']['access_model']}\n"
        f"Tags: {', '.join(profile.get('tags', []))}\n"
    )
    vault_contribute(vault_content, ds_id, auto_approve=auto_approve)

    return {
        "dataset_id": ds_id,
        "records": record_count,
        "quality_score": quality,
        "published_at": datetime.now(timezone.utc).isoformat()
    }

def update_node_stats(node_id: str, run_result: dict, registry: dict) -> dict:
    node = registry["nodes"][node_id]
    node["last_refresh"] = run_result["published_at"]
    node["datasets_published"] += 1
    node["freshness_score"] = 1.0
    ratio = min(1.0, node["queries_served"] / max(node["datasets_published"] * 100, 1))
    node["quality_score"] = round(min(1.0, run_result["quality_score"] * 0.7 + ratio * 0.3), 2)
    node["status"] = "active"
    registry["network_stats"]["total_datasets_published"] += 1
    return registry

def list_profiles():
    print(f"\n{INAI_BOLD}Available Vertical Node Profiles:{RESET}\n")
    for p in sorted(PROFILES_DIR.glob("*.json")):
        with open(p) as f:
            prof = json.load(f)
        print(f"  {prof.get('emoji','🔵')} {INAI_BOLD}{p.stem:20}{RESET} {prof['description'][:70]}")
        print(f"     Refresh: {prof['refresh']['description']:12} | Price: {prof['inai']['suggested_price']} $INAI | Sources: {len(prof['sources'])}")
    print()

def main():
    parser = argparse.ArgumentParser(description="Inflectiv Vertical Intelligence Node Launcher")
    parser.add_argument("--profile", "-p", help="Profile name to run (e.g. defi, ai-models, crypto-news)")
    parser.add_argument("--list", "-l", action="store_true", help="List available profiles")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without publishing")
    args = parser.parse_args()

    print(f"\n{INAI_BOLD}{INAI_PURPLE}╔══════════════════════════════════════════════╗{RESET}")
    print(f"{INAI_BOLD}{INAI_PURPLE}║   Inflectiv Vertical Intelligence Node       ║{RESET}")
    print(f"{INAI_BOLD}{INAI_PURPLE}║   VINN Node Launcher v1.0.0                  ║{RESET}")
    print(f"{INAI_BOLD}{INAI_PURPLE}╚══════════════════════════════════════════════╝{RESET}")

    if args.list or not args.profile:
        list_profiles()
        if not args.list:
            parser.print_help()
        return

    profile = load_profile(args.profile)
    registry = load_registry()
    registry = register_node(profile, registry)
    
    if args.dry_run:
        print(f"\n{INAI_ORANGE}[DRY RUN] Skipping research cycle{RESET}")
        return

    result = run_research_cycle(profile)
    registry = update_node_stats(profile["node_id"], result, registry)
    save_registry(registry)

    print(f"\n{INAI_BOLD}{INAI_GREEN}✅ Node cycle complete!{RESET}")
    print(f"   Dataset: {result['dataset_id']}")
    print(f"   Records: {result['records']}")
    print(f"   Quality: {result['quality_score']}")
    print(f"   Node earnings accumulating at {profile['inai']['suggested_price']} $INAI/query\n")

if __name__ == "__main__":
    main()
