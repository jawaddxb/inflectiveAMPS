#!/usr/bin/env python3
"""
Inflectiv Living Dataset Connector — Manager CLI
=================================================
"Tell us what you care about. We'll build it, keep it fresh,
and share the $INAI earnings with you."

Commands:
  python manager.py add      --topic "x402 payments" --schedule daily
  python manager.py list     -- show all living datasets
  python manager.py status   -- dashboard view
  python manager.py earnings -- $INAI earnings summary
  python manager.py refresh  --id ld_001 -- manual refresh trigger

Docs: https://inflectiv.gitbook.io/inflectiv
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).parent
INTERESTS_FILE = BASE_DIR / "interests.json"
REGISTRY_FILE  = BASE_DIR / "registry.json"

SCHEDULE_MAP = {
    "hourly":  timedelta(hours=1),
    "daily":   timedelta(days=1),
    "weekly":  timedelta(weeks=1),
}

FRESHNESS_DECAY = {
    "hourly":  24,    # stale after 24 hrs
    "daily":   7,     # stale after 7 days
    "weekly":  30,    # stale after 30 days
}

# ── Helpers ──────────────────────────────────────────────────────────────────

def load_json(path):
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def freshness_bar(score, width=20):
    filled = int(score * width)
    bar = "█" * filled + "░" * (width - filled)
    if score >= 0.8:
        label = "🟢 Fresh"
    elif score >= 0.5:
        label = "🟡 Aging"
    else:
        label = "🔴 Stale"
    return f"[{bar}] {score:.0%}  {label}"

def compute_freshness(last_refreshed_str, schedule):
    """Compute 0.0–1.0 freshness score based on time since last refresh."""
    try:
        last = datetime.fromisoformat(last_refreshed_str.replace('Z', '+00:00'))
        now  = datetime.now(last.tzinfo)
        age_hours = (now - last).total_seconds() / 3600
        stale_at  = FRESHNESS_DECAY.get(schedule, 24)
        return max(0.0, 1.0 - (age_hours / stale_at))
    except Exception:
        return 0.5

# ── Commands ─────────────────────────────────────────────────────────────────

def cmd_add(args):
    data    = load_json(INTERESTS_FILE)
    registry = load_json(REGISTRY_FILE)
    if "interests" not in data:
        data["interests"] = []
    if "living_datasets" not in registry:
        registry["living_datasets"] = []

    topic_id = f"topic_{len(data['interests'])+1:03d}"
    ld_id    = f"ld_{len(registry['living_datasets'])+1:03d}"
    now      = datetime.utcnow().isoformat() + "Z"
    schedule = args.schedule if args.schedule in SCHEDULE_MAP else "daily"
    delta    = SCHEDULE_MAP[schedule]
    next_run = (datetime.utcnow() + delta).isoformat() + "Z"

    interest = {
        "id": topic_id,
        "topic": args.topic,
        "keywords": [k.strip() for k in args.topic.split()[:5]],
        "sources": [],
        "refresh_schedule": schedule,
        "dataset_id": None,
        "visibility": args.visibility if hasattr(args, 'visibility') else "public",
        "price_inai": float(args.price) if hasattr(args, 'price') and args.price else 0.0,
        "active": True
    }
    data["interests"].append(interest)
    save_json(INTERESTS_FILE, data)

    entry = {
        "id": ld_id,
        "topic_id": topic_id,
        "title": f"{args.topic.title()} — Living Dataset",
        "dataset_id": None,
        "version": 0,
        "last_refreshed": now,
        "next_refresh": next_run,
        "refresh_schedule": schedule,
        "refresh_count": 0,
        "query_count": 0,
        "inai_earned": 0.0,
        "freshness_score": 1.0,
        "status": "pending_first_run",
        "file_path": None,
        "changelog": []
    }
    registry["living_datasets"].append(entry)
    save_json(REGISTRY_FILE, registry)

    print(f"\n✅ Interest registered!")
    print(f"   Topic:    {args.topic}")
    print(f"   ID:       {ld_id}")
    print(f"   Schedule: Refresh {schedule}")
    print(f"   Next run: {next_run}")
    print(f"\n🔄 Initial dataset will be built on first scheduled run.")
    print(f"   Or trigger manually: python manager.py refresh --id {ld_id}")
    print(f"\n💸 You'll earn $INAI every time other agents query your dataset.")


def cmd_list(args):
    registry = load_json(REGISTRY_FILE)
    datasets = registry.get("living_datasets", [])

    if not datasets:
        print("\n📭 No living datasets yet. Add one:")
        print("   python manager.py add --topic \"your topic\" --schedule daily")
        return

    print(f"\n{'─'*70}")
    print(f"  📡  INFLECTIV LIVING DATASETS   ({len(datasets)} active)")
    print(f"{'─'*70}")

    total_earned = 0.0
    total_queries = 0

    for d in datasets:
        score = compute_freshness(d["last_refreshed"], d.get("refresh_schedule", "daily"))
        total_earned  += d.get("inai_earned", 0)
        total_queries += d.get("query_count", 0)

        status_icon = {"active": "🟢", "pending_first_run": "⏳", "error": "🔴"}.get(d["status"], "⚪")

        print(f"\n  {status_icon} [{d['id']}] {d['title']}")
        print(f"     Freshness:  {freshness_bar(score)}")
        print(f"     Version:    v{d['version']}   Last refresh: {d['last_refreshed'][:10]}   Next: {d['next_refresh'][:10]}")
        print(f"     Queries:    {d['query_count']:,}   Earned: {d['inai_earned']:.4f} $INAI")
        if d.get("dataset_id"):
            print(f"     Marketplace: https://app.inflectiv.ai/marketplace/{d['dataset_id']}")

    print(f"\n{'─'*70}")
    print(f"  💰 TOTAL EARNED:  {total_earned:.4f} $INAI   |   Total queries: {total_queries:,}")
    print(f"{'─'*70}\n")


def cmd_status(args):
    """Full dashboard view."""
    registry  = load_json(REGISTRY_FILE)
    interests = load_json(INTERESTS_FILE)
    datasets  = registry.get("living_datasets", [])
    topics    = {i["id"]: i for i in interests.get("interests", [])}

    print(f"\n{'═'*70}")
    print(f"  🧠  INFLECTIV CONNECTOR — LIVING DATASETS DASHBOARD")
    print(f"  'Tell us what you care about. We keep it fresh. You earn $INAI.'")
    print(f"{'═'*70}")
    print(f"  Active topics:  {len(datasets)}")
    total_earned = sum(d.get('inai_earned', 0) for d in datasets)
    total_queries = sum(d.get('query_count', 0) for d in datasets)
    total_refreshes = sum(d.get('refresh_count', 0) for d in datasets)
    print(f"  Total $INAI earned:  {total_earned:.4f}")
    print(f"  Total queries served: {total_queries:,}")
    print(f"  Total refreshes run:  {total_refreshes:,}")
    print(f"{'─'*70}")

    for d in datasets:
        t = topics.get(d["topic_id"], {})
        score = compute_freshness(d["last_refreshed"], d.get("refresh_schedule", "daily"))
        status_icon = {"active": "🟢", "pending_first_run": "⏳", "error": "🔴"}.get(d["status"], "⚪")
        print(f"\n  {status_icon}  {d['title']}")
        print(f"     Topic:    {t.get('topic', 'N/A')}")
        print(f"     Schedule: Refresh {d.get('refresh_schedule', 'daily')}")
        print(f"     {freshness_bar(score)}")
        if d.get('changelog'):
            last = d['changelog'][-1]
            print(f"     Last update: {last.get('summary', '')}")
    print(f"\n{'═'*70}\n")


def cmd_refresh(args):
    registry = load_json(REGISTRY_FILE)
    datasets = registry.get("living_datasets", [])
    target = next((d for d in datasets if d["id"] == args.id), None)
    if not target:
        print(f"❌ No dataset found with ID: {args.id}")
        sys.exit(1)

    print(f"\n🔄 Triggering refresh for: {target['title']}")
    print(f"   This will launch the refresh_task.py agent...")
    print(f"   Run: python connector/refresh_task.py --id {args.id}")


def cmd_earnings(args):
    registry = load_json(REGISTRY_FILE)
    datasets = registry.get("living_datasets", [])
    print(f"\n{'─'*50}")
    print(f"  💰  $INAI EARNINGS SUMMARY")
    print(f"{'─'*50}")
    total = 0.0
    for d in datasets:
        earned = d.get('inai_earned', 0)
        total += earned
        print(f"  {d['title'][:35]:35s}  {earned:.4f} $INAI  ({d['query_count']} queries)")
    print(f"{'─'*50}")
    print(f"  {'TOTAL':35s}  {total:.4f} $INAI")
    print(f"{'─'*50}\n")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Inflectiv Living Dataset Connector",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python manager.py add --topic "x402 AI payments" --schedule daily
  python manager.py add --topic "Sui DeFi protocols" --schedule hourly --price 0.5
  python manager.py list
  python manager.py status
  python manager.py earnings
  python manager.py refresh --id ld_001
        """
    )
    sub = parser.add_subparsers(dest="command")

    # add
    p_add = sub.add_parser("add", help="Register a new interest / living dataset")
    p_add.add_argument("--topic", "-t", required=True, help="Topic to track")
    p_add.add_argument("--schedule", "-s", choices=["hourly", "daily", "weekly"], default="daily")
    p_add.add_argument("--visibility", "-v", choices=["public", "private", "paid"], default="public")
    p_add.add_argument("--price", "-p", default=0.0, help="Price in $INAI (for paid datasets)")

    # list
    sub.add_parser("list", help="List all living datasets")

    # status
    sub.add_parser("status", help="Full dashboard view")

    # earnings
    sub.add_parser("earnings", help="$INAI earnings summary")

    # refresh
    p_ref = sub.add_parser("refresh", help="Manually trigger a dataset refresh")
    p_ref.add_argument("--id", required=True, help="Living dataset ID (e.g. ld_001)")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    {"add": cmd_add, "list": cmd_list, "status": cmd_status,
     "earnings": cmd_earnings, "refresh": cmd_refresh}[args.command](args)


if __name__ == "__main__":
    main()
