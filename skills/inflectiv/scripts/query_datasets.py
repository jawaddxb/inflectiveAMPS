#!/usr/bin/env python3
"""
Inflectiv Dataset Query Tool
============================
Query the Inflectiv.ai Intelligence Marketplace for structured datasets.

Part of the Inflectiv Agent Node skill for OpenClaw-compatible agents.
Implements the Query-Before-Browse pattern: check structured datasets
before falling back to web browsing.

Usage:
    python query_datasets.py --query "DeFi TVL data 2025" --api-key YOUR_KEY
    python query_datasets.py --dataset-id ds_abc123 --query "what protocols are listed?"
    python query_datasets.py --query "test" --demo

Docs: https://inflectiv.gitbook.io/inflectiv
"""

import argparse
import json
import os
import sys
from typing import Optional

try:
    import requests
except ImportError:
    print("[ERROR] requests not installed. Run: pip install requests", file=sys.stderr)
    sys.exit(1)


INFLECTIV_BASE_URL = os.environ.get("INFLECTIV_BASE_URL", "https://api.inflectiv.ai/v1")
DEFAULT_LIMIT = 5


# ── Demo mode mock data ──────────────────────────────────────────────────────

MOCK_RESULTS = {
    "status": "success",
    "query": "{query}",
    "results": [
        {
            "id": "ds_demo_001",
            "title": "DeFi Protocol TVL Data Q4 2025",
            "description": "Structured TVL, volume and APY data for top 100 DeFi protocols across Ethereum, Sui, and Solana.",
            "relevance_score": 0.92,
            "format": "json+csv",
            "size_mb": 4.2,
            "last_updated": "2026-01-15",
            "access": "free",
            "publisher": "inflectiv-core",
            "marketplace_url": "https://app.inflectiv.ai/marketplace/ds_demo_001",
            "preview": {
                "rows": 3,
                "sample": [
                    {"protocol": "Uniswap V4", "tvl_usd": 8200000000, "chain": "ethereum"},
                    {"protocol": "Cetus", "tvl_usd": 920000000, "chain": "sui"},
                    {"protocol": "Turbos", "tvl_usd": 340000000, "chain": "sui"}
                ]
            }
        },
        {
            "id": "ds_demo_002",
            "title": "Sui Ecosystem Project Directory 2026",
            "description": "Comprehensive list of 500+ projects building on Sui with categories, funding, and status.",
            "relevance_score": 0.74,
            "format": "json",
            "size_mb": 1.8,
            "last_updated": "2026-02-01",
            "access": "free",
            "publisher": "sui-community-dao",
            "marketplace_url": "https://app.inflectiv.ai/marketplace/ds_demo_002",
            "preview": None
        }
    ],
    "total_results": 2,
    "query_cost_inai": 0.0,
    "recommendation": "High relevance match found. Recommend using ds_demo_001 directly (score: 0.92). Skip web browsing."
}


# ── API client ───────────────────────────────────────────────────────────────

def query_marketplace(
    query: str,
    api_key: str,
    dataset_id: Optional[str] = None,
    limit: int = DEFAULT_LIMIT,
    min_relevance: float = 0.0,
    output_format: str = "json",
    base_url: str = INFLECTIV_BASE_URL,
) -> dict:
    """Query the Inflectiv marketplace for datasets matching the query."""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-Client": "inflectiv-agent-node/1.0.0",
    }

    if dataset_id:
        # Query a specific dataset
        endpoint = f"{base_url}/datasets/{dataset_id}/query"
        payload = {"query": query}
    else:
        # Search the marketplace
        endpoint = f"{base_url}/marketplace/search"
        payload = {
            "query": query,
            "limit": limit,
            "min_relevance": min_relevance,
        }

    try:
        response = requests.post(endpoint, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        return {
            "status": "error",
            "error": "Cannot connect to Inflectiv API. Check INFLECTIV_BASE_URL or network.",
            "endpoint": endpoint,
        }
    except requests.exceptions.Timeout:
        return {"status": "error", "error": "Request timed out after 30 seconds."}
    except requests.exceptions.HTTPError as e:
        return {
            "status": "error",
            "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}",
        }


# ── Output formatters ────────────────────────────────────────────────────────

def format_text(data: dict) -> str:
    """Human-readable text output."""
    if data.get("status") == "error":
        return f"❌ Error: {data['error']}"

    lines = []
    results = data.get("results", [])
    query = data.get("query", "")
    total = data.get("total_results", len(results))

    lines.append(f"\n🔍 Inflectiv Query: '{query}'")
    lines.append(f"📊 Found {total} dataset(s)\n")
    lines.append("-" * 60)

    for i, r in enumerate(results, 1):
        score = r.get("relevance_score", 0)
        score_icon = "🟢" if score >= 0.7 else ("🟡" if score >= 0.4 else "🔴")
        lines.append(f"{i}. {r['title']}")
        lines.append(f"   {score_icon} Relevance: {score:.2f}  |  ID: {r['id']}")
        lines.append(f"   📝 {r['description'][:120]}")
        lines.append(f"   🏷️  Format: {r.get('format','N/A')}  |  Access: {r.get('access','free')}  |  Updated: {r.get('last_updated','N/A')}")
        lines.append(f"   🔗 {r.get('marketplace_url','')}")
        if r.get("preview") and r["preview"].get("sample"):
            lines.append(f"   👁️  Preview (first {r['preview']['rows']} rows):")
            for row in r["preview"]["sample"][:2]:
                lines.append(f"      {row}")
        lines.append("")

    if data.get("recommendation"):
        lines.append(f"💡 {data['recommendation']}")

    cost = data.get("query_cost_inai", 0)
    lines.append(f"\n💸 Query cost: {cost} $INAI")
    return "\n".join(lines)


# ── CLI ──────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Query the Inflectiv.ai Intelligence Marketplace",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python query_datasets.py --query "Sui DeFi TVL" --api-key sk_...
  python query_datasets.py --dataset-id ds_abc --query "list all protocols" --api-key sk_...
  python query_datasets.py --query "test" --demo
  python query_datasets.py --query "AI agents" --limit 10 --min-relevance 0.5 --output-format json

Docs: https://inflectiv.gitbook.io/inflectiv
    """
    )
    parser.add_argument("--query", "-q", required=True, help="Search query or question")
    parser.add_argument("--api-key", "-k", default=os.environ.get("INFLECTIV_API_KEY"), help="Inflectiv API key (or set INFLECTIV_API_KEY env var)")
    parser.add_argument("--dataset-id", "-d", default=None, help="Query a specific dataset by ID")
    parser.add_argument("--limit", "-l", type=int, default=DEFAULT_LIMIT, help=f"Max results to return (default: {DEFAULT_LIMIT})")
    parser.add_argument("--min-relevance", type=float, default=0.0, help="Minimum relevance score filter (0.0–1.0)")
    parser.add_argument("--output-format", "-o", choices=["json", "text"], default="text", help="Output format (default: text)")
    parser.add_argument("--base-url", default=INFLECTIV_BASE_URL, help="Inflectiv API base URL")
    parser.add_argument("--demo", action="store_true", help="Run in demo mode with mock data (no API key needed)")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.demo:
        data = json.loads(json.dumps(MOCK_RESULTS).replace("{query}", args.query))
    else:
        if not args.api_key:
            print("[ERROR] API key required. Use --api-key or set INFLECTIV_API_KEY.", file=sys.stderr)
            print("Get your key at: https://app.inflectiv.ai", file=sys.stderr)
            sys.exit(1)
        data = query_marketplace(
            query=args.query,
            api_key=args.api_key,
            dataset_id=args.dataset_id,
            limit=args.limit,
            min_relevance=args.min_relevance,
            output_format=args.output_format,
            base_url=args.base_url,
        )

    if args.output_format == "json":
        print(json.dumps(data, indent=2))
    else:
        print(format_text(data))

    # Exit with error code if API returned error
    if data.get("status") == "error":
        sys.exit(1)


if __name__ == "__main__":
    main()
