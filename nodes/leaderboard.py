#!/usr/bin/env python3
"""
Inflectiv VINN Network Leaderboard
Usage: python leaderboard.py
       python leaderboard.py --vertical defi
       python leaderboard.py --top 5
       python leaderboard.py --json
"""
import json, argparse, sys
from pathlib import Path
from datetime import datetime, timezone

REGISTRY_FILE = Path(__file__).parent / "node_registry.json"

P = "\033[95m"; O = "\033[93m"; G = "\033[92m"
C = "\033[96m"; R = "\033[91m"; B = "\033[1m"; X = "\033[0m"
DIM = "\033[2m"

def load_registry():
    with open(REGISTRY_FILE) as f:
        return json.load(f)

def freshness_bar(score, width=12):
    filled = int(score * width)
    bar = "█" * filled + "░" * (width - filled)
    color = G if score > 0.8 else O if score > 0.5 else R
    return f"{color}{bar}{X}"

def quality_stars(score):
    stars = int(round(score * 5))
    return f"{O}{'★'*stars}{'☆'*(5-stars)}{X}"

def status_badge(status):
    if status == "active": return f"{G}● LIVE{X}"
    if status == "inactive": return f"{R}● IDLE{X}"
    return f"{O}● {status.upper()}{X}"

def score_color(val):
    if val >= 0.9: return G
    if val >= 0.75: return O
    return R

def format_inai(val):
    if val >= 1000: return f"{val/1000:.1f}K"
    return f"{val:.2f}"

def print_header(stats):
    print(f"\n{B}{P}{'═'*72}{X}")
    print(f"{B}{P}  ██╗███╗   ██╗███████╗██╗      ███████╗ ██████╗████████╗██╗██╗   ██╗{X}")
    print(f"{B}{P}  ██║████╗  ██║██╔════╝██║      ██╔════╝██╔════╝╚══██╔══╝██║██║   ██║{X}")
    print(f"{B}{P}  ██║██╔██╗ ██║█████╗  ██║      █████╗  ██║        ██║   ██║██║   ██║{X}")
    print(f"{B}{P}  ██║██║╚██╗██║██╔══╝  ██║      ██╔══╝  ██║        ██║   ██║╚██╗ ██╔╝{X}")
    print(f"{B}{P}  ██║██║ ╚████║██║     ███████╗ ███████╗╚██████╗   ██║   ██║ ╚████╔╝ {X}")
    print(f"{B}{P}  ╚═╝╚═╝  ╚═══╝╚═╝     ╚══════╝ ╚══════╝ ╚═════╝   ╚═╝   ╚═╝  ╚═══╝  {X}")
    print(f"{B}{P}  Vertical Intelligence Node Network — Leaderboard{X}")
    print(f"{B}{P}{'═'*72}{X}")
    print(f"  {DIM}Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}{X}")
    print()
    s = stats
    print(f"  {B}Network Stats:{X}")
    print(f"  {'Active Nodes':<22} {G}{B}{s['active_nodes']}/{s['total_nodes']}{X}")
    print(f"  {'Total Datasets Published':<22} {C}{B}{s['total_datasets_published']:,}{X}")
    print(f"  {'Total Queries Served':<22} {C}{B}{s['total_queries_served']:,}{X}")
    print(f"  {'Total $INAI Earned':<22} {O}{B}{s['total_inai_earned']:,.2f} $INAI{X}")
    print(f"  {'Network Freshness':<22} {freshness_bar(s['network_freshness_avg'])} {s['network_freshness_avg']:.0%}")
    print()

def print_leaderboard(nodes, top=None):
    ranked = sorted(nodes.values(), key=lambda n: n["quality_score"], reverse=True)
    if top: ranked = ranked[:top]
    
    print(f"{B}{'─'*72}{X}")
    print(f"  {B}{'#':<3} {'Node':<34} {'Score':<8} {'Queries':<9} {'$INAI':<10} {'Status'}{X}")
    print(f"{B}{'─'*72}{X}")
    
    medals = ["🥇","🥈","🥉"]
    for i, node in enumerate(ranked):
        rank = medals[i] if i < 3 else f" {i+1}."
        name = f"{node['emoji']} {node['name']}"
        if len(name) > 32: name = name[:31] + "…"
        sc = node["quality_score"]
        score_str = f"{score_color(sc)}{sc:.2f}{X}"
        queries = f"{node['queries_served']:,}"
        earnings = f"{O}{format_inai(node['earnings_inai'])}{X}"
        status = status_badge(node["status"])
        print(f"  {rank:<4} {name:<34} {score_str:<18} {queries:<9} {earnings:<20} {status}")
        print(f"       {DIM}{node['description'][:62]}…{X}")
        print(f"       Freshness: {freshness_bar(node['freshness_score'], 10)}  "
              f"Quality: {quality_stars(node['quality_score'])}  "
              f"Refresh: {node['refresh_description']}  "
              f"Price: {O}{node['inai_price']} $INAI{X}")
        if i < len(ranked) - 1:
            print(f"  {DIM}{'·'*68}{X}")
    print(f"{B}{'─'*72}{X}")

def main():
    parser = argparse.ArgumentParser(description="Inflectiv VINN Leaderboard")
    parser.add_argument("--vertical", "-v", help="Filter by vertical")
    parser.add_argument("--top", "-t", type=int, help="Show top N nodes")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    parser.add_argument("--status", "-s", help="Filter by status (active/inactive)")
    args = parser.parse_args()

    reg = load_registry()
    nodes = reg["nodes"]
    
    if args.status:
        nodes = {k:v for k,v in nodes.items() if v["status"] == args.status}
    if args.vertical:
        nodes = {k:v for k,v in nodes.items() if args.vertical.lower() in v["vertical"].lower()}
    
    if args.json:
        ranked = sorted(nodes.values(), key=lambda n: n["quality_score"], reverse=True)
        print(json.dumps(ranked[:args.top] if args.top else ranked, indent=2))
        return

    print_header(reg["network_stats"])
    if not nodes:
        print(f"  {R}No nodes match your filter.{X}\n")
        return
    print_leaderboard(nodes, args.top)
    print(f"\n  {DIM}Deploy your own node: python nodes/node_launcher.py --list{X}")
    print(f"  {DIM}VINN Network — inflectiv.ai | Powered by $INAI{X}\n")

if __name__ == "__main__":
    main()
