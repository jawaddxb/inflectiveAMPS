#!/usr/bin/env python3
"""
Inflectiv Dataset Publisher
============================
Publish structured datasets to the Inflectiv.ai Intelligence Marketplace.

Implements the Publish-Back pipeline: after an agent discovers or generates
structured data, this tool uploads it to the marketplace so other agents
can benefit — and the publisher earns $INAI.

Usage:
    python publish_dataset.py --title "My Dataset" --files data.json --api-key KEY
    python publish_dataset.py --title "Test" --files file.txt --demo

Docs: https://inflectiv.gitbook.io/inflectiv
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import List

try:
    import requests
except ImportError:
    print("[ERROR] requests not installed. Run: pip install requests", file=sys.stderr)
    sys.exit(1)


INFLECTIV_BASE_URL = os.environ.get("INFLECTIV_BASE_URL", "https://api.inflectiv.ai/v1")
MAX_FILE_SIZE_MB = 50


# ── Demo mode ────────────────────────────────────────────────────────────────

def demo_publish(title: str, files: List[str], visibility: str, price_inai: float) -> dict:
    """Simulate publishing a dataset (demo mode, no API call)."""
    total_size = sum(Path(f).stat().st_size for f in files if Path(f).exists())
    dataset_id = f"ds_demo_{int(time.time()) % 100000:05d}"
    return {
        "status": "success",
        "demo_mode": True,
        "dataset": {
            "id": dataset_id,
            "title": title,
            "visibility": visibility,
            "price_inai": price_inai,
            "files_uploaded": [Path(f).name for f in files if Path(f).exists()],
            "total_size_bytes": total_size,
            "created_at": "2026-02-21T12:00:00Z",
            "marketplace_url": f"https://app.inflectiv.ai/marketplace/{dataset_id}",
            "api_endpoint": f"https://api.inflectiv.ai/v1/datasets/{dataset_id}/query",
            "status": "processing",
        },
        "message": "[DEMO] Dataset published successfully. In production, it will appear in the marketplace within 2-5 minutes after processing.",
        "inai_earned_estimate": price_inai * 10 if visibility == "paid" else 0,
    }


# ── API client ────────────────────────────────────────────────────────────────

def publish_dataset(
    title: str,
    files: List[str],
    api_key: str,
    description: str = "",
    visibility: str = "public",
    price_inai: float = 0.0,
    tags: List[str] = None,
    base_url: str = INFLECTIV_BASE_URL,
) -> dict:
    """Upload files and create a new dataset on the Inflectiv marketplace."""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "X-Client": "inflectiv-agent-node/1.0.0",
    }

    # Validate files
    valid_files = []
    for filepath in files:
        p = Path(filepath)
        if not p.exists():
            print(f"[WARN] File not found, skipping: {filepath}", file=sys.stderr)
            continue
        size_mb = p.stat().st_size / (1024 * 1024)
        if size_mb > MAX_FILE_SIZE_MB:
            print(f"[WARN] File too large ({size_mb:.1f}MB > {MAX_FILE_SIZE_MB}MB), skipping: {filepath}", file=sys.stderr)
            continue
        valid_files.append(p)

    if not valid_files:
        return {"status": "error", "error": "No valid files to upload."}

    print(f"📤 Uploading {len(valid_files)} file(s) to Inflectiv...", file=sys.stderr)

    # Step 1: Create dataset record
    create_endpoint = f"{base_url}/datasets"
    payload = {
        "title": title,
        "description": description,
        "visibility": visibility,
        "price_inai": price_inai,
        "tags": tags or [],
        "source": "inflectiv-agent-node",
    }

    try:
        resp = requests.post(create_endpoint, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        dataset = resp.json()
        dataset_id = dataset.get("id")
        upload_url = dataset.get("upload_url")
    except requests.exceptions.ConnectionError:
        return {"status": "error", "error": "Cannot connect to Inflectiv API. Check network or INFLECTIV_BASE_URL."}
    except requests.exceptions.HTTPError as e:
        return {"status": "error", "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"}

    # Step 2: Upload files
    uploaded = []
    for p in valid_files:
        print(f"  ↑ {p.name} ({p.stat().st_size / 1024:.1f} KB)", file=sys.stderr)
        try:
            file_endpoint = upload_url or f"{base_url}/datasets/{dataset_id}/files"
            with open(p, "rb") as fh:
                file_resp = requests.post(
                    file_endpoint,
                    files={"file": (p.name, fh)},
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=60,
                )
                file_resp.raise_for_status()
                uploaded.append(p.name)
        except Exception as e:
            print(f"  [WARN] Failed to upload {p.name}: {e}", file=sys.stderr)

    # Step 3: Finalize
    try:
        finalize_endpoint = f"{base_url}/datasets/{dataset_id}/finalize"
        fin_resp = requests.post(finalize_endpoint, headers=headers, timeout=30)
        fin_resp.raise_for_status()
    except Exception as e:
        print(f"[WARN] Finalize step failed: {e}", file=sys.stderr)

    return {
        "status": "success",
        "dataset": {
            "id": dataset_id,
            "title": title,
            "visibility": visibility,
            "price_inai": price_inai,
            "files_uploaded": uploaded,
            "marketplace_url": f"https://app.inflectiv.ai/marketplace/{dataset_id}",
            "api_endpoint": f"{base_url}/datasets/{dataset_id}/query",
        },
        "message": "Dataset published. It will appear in the marketplace within 2-5 minutes.",
    }


# ── Output ────────────────────────────────────────────────────────────────────

def format_result(data: dict, output_format: str) -> str:
    if output_format == "json":
        return json.dumps(data, indent=2)

    if data.get("status") == "error":
        return f"❌ Error: {data['error']}"

    d = data.get("dataset", {})
    lines = [
        f"\n✅ Dataset Published Successfully!",
        f"   ID:    {d.get('id')}",
        f"   Title: {d.get('title')}",
        f"   Visibility: {d.get('visibility')}  |  Price: {d.get('price_inai', 0)} $INAI",
        f"   Files: {', '.join(d.get('files_uploaded', []))}",
        f"",
        f"   🔗 Marketplace: {d.get('marketplace_url')}",
        f"   🔌 API Endpoint: {d.get('api_endpoint')}",
        f"",
        f"   💬 {data.get('message', '')}",
    ]
    if data.get("demo_mode"):
        lines.insert(1, "   ⚠️  DEMO MODE — No actual upload performed")
    return "\n".join(lines)


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Publish structured datasets to the Inflectiv.ai marketplace",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python publish_dataset.py --title "DeFi Research" --files data.json --api-key sk_...
  python publish_dataset.py --title "Agent Report" --files r.md d.csv --visibility paid --price-inai 1.0 --api-key sk_...
  python publish_dataset.py --title "Test" --files README.md --demo

Docs: https://inflectiv.gitbook.io/inflectiv
    """
    )
    parser.add_argument("--title", "-t", required=True, help="Dataset title")
    parser.add_argument("--files", "-f", nargs="+", required=True, help="Files to upload")
    parser.add_argument("--api-key", "-k", default=os.environ.get("INFLECTIV_API_KEY"), help="Inflectiv API key")
    parser.add_argument("--description", "-D", default="", help="Dataset description")
    parser.add_argument("--visibility", "-v", choices=["public", "private", "paid"], default="public", help="Dataset visibility (default: public)")
    parser.add_argument("--price-inai", type=float, default=0.0, help="Price in $INAI for paid datasets")
    parser.add_argument("--tags", nargs="*", default=[], help="Tags for discoverability")
    parser.add_argument("--output-format", "-o", choices=["json", "text"], default="text")
    parser.add_argument("--base-url", default=INFLECTIV_BASE_URL)
    parser.add_argument("--demo", action="store_true", help="Demo mode — no actual upload")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.demo:
        data = demo_publish(args.title, args.files, args.visibility, args.price_inai)
    else:
        if not args.api_key:
            print("[ERROR] API key required. Use --api-key or set INFLECTIV_API_KEY.", file=sys.stderr)
            print("Get your key at: https://app.inflectiv.ai", file=sys.stderr)
            sys.exit(1)
        data = publish_dataset(
            title=args.title,
            files=args.files,
            api_key=args.api_key,
            description=args.description,
            visibility=args.visibility,
            price_inai=args.price_inai,
            tags=args.tags,
            base_url=args.base_url,
        )

    print(format_result(data, args.output_format))
    if data.get("status") == "error":
        sys.exit(1)


if __name__ == "__main__":
    main()
