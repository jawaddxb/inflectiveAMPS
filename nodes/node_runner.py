#!/usr/bin/env python3
"""
Inflectiv Vertical Intelligence Node — Continuous Runner
Runs a vertical profile in a loop, respecting the refresh cadence from profile config.
Usage: python nodes/node_runner.py --profile defi [--continuous] [--once]
"""

import argparse
import json
import os
import sys
import time
import signal
import threading
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).parent.parent
PROFILES_DIR = BASE / "profiles"
LAUNCHER = BASE / "nodes" / "node_launcher.py"

RUNNING = True

def signal_handler(sig, frame):
    global RUNNING
    print("\n⏹  Shutdown signal received — stopping node gracefully...")
    RUNNING = False

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


REFRESH_SECONDS = {
    "hourly": 3600,
    "every_2_hours": 7200,
    "every_6_hours": 21600,
    "every_12_hours": 43200,
    "daily": 86400,
    "weekly": 604800,
}


def load_profile(profile_id: str) -> dict:
    path = PROFILES_DIR / f"{profile_id}.json"
    if not path.exists():
        print(f"❌ Profile not found: {profile_id}")
        sys.exit(1)
    return json.loads(path.read_text())


def banner(profile: dict, interval_secs: int):
    emoji = profile.get("emoji", "⬡")
    name = profile.get("name", "Unknown Node")
    niche = profile.get("niche", "")
    wallet = os.getenv("WALLET_ADDRESS", "not set")[:12] + "..."
    hrs = interval_secs // 3600
    mins = (interval_secs % 3600) // 60
    interval_str = f"{hrs}h" if hrs else f"{mins}m"
    print(f"""
╔══════════════════════════════════════════════════════╗
║  {emoji}  {name:<44} ║
║  Niche   : {niche:<43} ║
║  Refresh : every {interval_str:<38} ║
║  Wallet  : {wallet:<43} ║
║  Mode    : continuous                                ║
╚══════════════════════════════════════════════════════╝
""")


def run_cycle(profile_id: str):
    """Run one research + publish cycle via node_launcher."""
    import subprocess
    result = subprocess.run(
        [sys.executable, str(LAUNCHER), "--profile", profile_id],
        capture_output=False
    )
    return result.returncode == 0


def run_continuous(profile_id: str, interval_secs: int):
    """Loop forever, running a cycle then sleeping."""
    global RUNNING
    cycle = 0
    while RUNNING:
        cycle += 1
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n{'─'*54}")
        print(f"🔄  Cycle #{cycle} starting at {now}")
        print(f"{'─'*54}")
        success = run_cycle(profile_id)
        if success:
            print(f"\n✅  Cycle #{cycle} complete")
        else:
            print(f"\n⚠️   Cycle #{cycle} encountered errors — will retry next interval")
        next_run = datetime.fromtimestamp(time.time() + interval_secs)
        print(f"⏰  Next run at: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
        # Sleep in small chunks so SIGTERM is handled quickly
        elapsed = 0
        while elapsed < interval_secs and RUNNING:
            time.sleep(min(10, interval_secs - elapsed))
            elapsed += 10
    print("\n👋  Node stopped cleanly.")



def start_api_server(profile_id: str, port: int = 8765):
    """Start the REST+A2A API server in a background thread."""
    try:
        import uvicorn
        from nodes.node_api import create_app
        app = create_app(profile_id)
        print(f"🌐 API server starting on port {port}")
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")
    except Exception as e:
        print(f"⚠️  API server could not start: {e}")


def main():
    parser = argparse.ArgumentParser(description="Inflectiv Vertical Intelligence Node Runner")
    parser.add_argument("--profile", required=True, help="Vertical profile ID (e.g. defi)")
    parser.add_argument("--continuous", action="store_true", help="Run continuously on schedule")
    parser.add_argument("--once", action="store_true", help="Run a single cycle and exit")
    parser.add_argument("--interval", type=int, default=None, help="Override refresh interval in seconds")
    args = parser.parse_args()

    profile = load_profile(args.profile)
    refresh_key = os.getenv("REFRESH_OVERRIDE") or profile.get("refresh_schedule", "daily")
    interval_secs = args.interval or REFRESH_SECONDS.get(refresh_key, 86400)

    if args.once or (not args.continuous):
        print(f"▶️  Running single cycle for profile: {args.profile}")
        ok = run_cycle(args.profile)
        sys.exit(0 if ok else 1)
    else:
        banner(profile, interval_secs)
        # Start API server in background thread
        api_port = int(os.getenv("PORT", 8765))
        api_thread = threading.Thread(
            target=start_api_server,
            args=(args.profile, api_port),
            daemon=True
        )
        api_thread.start()
        print(f"🌐 API live → http://0.0.0.0:{api_port}/a2a")
        print(f"📖 Docs    → http://0.0.0.0:{api_port}/docs")
        print("")
        run_continuous(args.profile, interval_secs)


if __name__ == "__main__":
    main()


# ── Vault integration (flywheel) ─────────────────────────────
import os, requests as _req

def _vault_contribute(summary: str, node_name: str = "node_runner"):
    """Auto-contribute node research summary to local vault."""
    vault_url   = os.environ.get("VAULT_URL", "")
    vault_token = os.environ.get("VAULT_TOKEN", "")
    if not vault_url or not vault_token:
        return
    try:
        resp = _req.post(
            vault_url.rstrip("/") + "/vault/contribute",
            json={"content": summary, "source": node_name},
            headers={"Authorization": "Bearer " + vault_token},
            timeout=10,
        )
        data = resp.json()
        category = data.get("category", "unknown")
        conf     = data.get("confidence", 0)
        cid      = data.get("contribution_id", "?")
        print(f"Vault: staged {category} ({conf:.0%} confidence) → id {cid[:8]}...")
        if os.environ.get("VAULT_AUTO_APPROVE", "").lower() in ("1", "true", "yes"):
            _req.post(
                vault_url.rstrip("/") + "/vault/contribute/" + cid + "/approve",
                headers={"Authorization": "Bearer " + vault_token},
                timeout=10,
            )
            print("Vault: auto-approved → +0.5 $INAI")
    except Exception as ex:
        print(f"Vault contribute skipped: {ex}")
