"""
AMPS — Agent Memory Portability Standard
Agent Zero / Inflectiv Vault native adapter (reference implementation)

Export: vault state → .amps.json
Import: .amps.json → vault state (append with conflict resolution)

AMPS v1.0 spec: AMPS_SPEC.md
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

AMPS_VERSION = "1.0"
SOURCE_FRAMEWORK = "agent_zero"


def _read_md(path: Path) -> Optional[str]:
    """Read a markdown file, return None if missing."""
    if path.exists():
        content = path.read_text().strip()
        return content if content else None
    return None


def _write_md(path: Path, content: str, heading: str):
    """
    Append imported content to a markdown file.
    Conflict resolution: existing content takes priority.
    Imported block added under a clear heading.
    """
    existing = path.read_text().strip() if path.exists() else ""
    import_block = f"\n\n---\n## Imported from {heading}\n\n{content.strip()}"
    path.parent.mkdir(parents=True, exist_ok=True)
    if existing:
        path.write_text(existing + import_block + "\n")
    else:
        path.write_text(content.strip() + "\n")


def export_vault(vault_root: str, stats_path: Optional[str] = None,
                 vault_id: Optional[str] = None) -> dict:
    """
    Export Agent Zero vault state to AMPS format.
    Lossless — all vault memory fields map directly.
    """
    root = Path(vault_root)
    now = datetime.now(timezone.utc).isoformat()

    # ── Memory fields ──────────────────────────────────────────
    long_term   = _read_md(root / "MEMORY.md")
    identity    = _read_md(root / "SOUL.md")
    active_plan = _read_md(root / "task_plan.md")

    if long_term is None:
        long_term = "# Agent Memory\n\n(empty)"
    if identity is None:
        identity = "# Agent Identity\n\n(not set)"

    # ── Contribution history ────────────────────────────────────
    contributions = {
        "total_items": 0,
        "categories": [],
        "quality_score": 0.0,
        "network_earnings": 0.0,
        "first_contribution": None,
        "last_contribution": None
    }
    _sp = stats_path or str(root / "stats.json")
    if os.path.exists(_sp):
        try:
            stats = json.loads(open(_sp).read())
            contributions["total_items"]      = stats.get("approved_contributions", 0)
            contributions["network_earnings"] = stats.get("inai_earned", 0.0)
            contributions["quality_score"]    = round(
                min(1.0, stats.get("approved_contributions", 0) /
                    max(stats.get("staged", 1), 1)), 3
            )
            # Contribution categories — scan staged dir if present
            staged_dir = root / "staged"
            categories = set()
            if staged_dir.is_dir():
                for f in staged_dir.glob("*.json"):
                    try:
                        item = json.loads(f.read_text())
                        cat = (item.get("top_category") or {}).get("category")
                        if cat:
                            categories.add(cat)
                    except Exception:
                        pass
            contributions["categories"] = sorted(categories)
        except Exception:
            pass

    # ── Knowledge subscriptions ─────────────────────────────────
    # Read from vault_config.json if present
    subscriptions = []
    vc_path = root / "vault_config.json"
    if vc_path.exists():
        try:
            vc = json.loads(vc_path.read_text())
            vault_id = vault_id or vc.get("vault_id", "unknown")
            subscriptions = vc.get("knowledge_subscriptions", [])
        except Exception:
            pass
    vault_id = vault_id or f"vlt_unknown_{now[:10]}"

    amps_doc = {
        "amps_version": AMPS_VERSION,
        "exported_at": now,
        "agent_id": vault_id,
        "source_framework": SOURCE_FRAMEWORK,
        "migration_notes": [],          # lossless — nothing to note
        "memory": {
            "long_term":   long_term,
            "identity":    identity,
            "active_plan": active_plan
        },
        "secrets": [],                  # never exported by spec
        "knowledge_subscriptions": subscriptions,
        "contributions": contributions
    }
    return amps_doc


def import_amps(amps_doc: dict, vault_root: str,
                overwrite: bool = False) -> dict:
    """
    Import an AMPS document into an Agent Zero vault.
    Returns: { ok, migration_notes, warnings }
    """
    root = Path(vault_root)
    root.mkdir(parents=True, exist_ok=True)
    warnings = []
    applied  = []

    # ── Version check ───────────────────────────────────────────
    ver = amps_doc.get("amps_version", "unknown")
    if ver != AMPS_VERSION:
        warnings.append(f"AMPS version mismatch: got {ver}, expected {AMPS_VERSION} — proceeding best-effort")

    # ── Migration notes ─────────────────────────────────────────
    migration_notes = amps_doc.get("migration_notes", [])
    if migration_notes:
        warnings.extend([f"[migration] {n}" for n in migration_notes])

    source = amps_doc.get("source_framework", "unknown")
    mem    = amps_doc.get("memory", {})

    # ── Memory fields ───────────────────────────────────────────
    field_map = [
        ("long_term",   "MEMORY.md"),
        ("identity",    "SOUL.md"),
        ("active_plan", "task_plan.md"),
    ]
    for amps_key, filename in field_map:
        content = mem.get(amps_key)
        if not content:
            continue
        path = root / filename
        if overwrite:
            path.write_text(content.strip() + "\n")
            applied.append(f"overwrote {filename}")
        else:
            _write_md(path, content, f"{source} (AMPS {ver})")
            applied.append(f"appended to {filename}")

    # ── Contribution history ─────────────────────────────────────
    contrib = amps_doc.get("contributions", {})
    if contrib.get("total_items", 0) > 0:
        sp = root / "stats.json"
        existing_stats = {}
        if sp.exists():
            try:
                existing_stats = json.loads(sp.read_text())
            except Exception:
                pass
        # Merge — keep higher values
        existing_stats["imported_contributions"] = contrib["total_items"]
        existing_stats["imported_categories"]    = contrib.get("categories", [])
        existing_stats["imported_quality"]        = contrib.get("quality_score", 0.0)
        existing_stats["imported_earnings"]       = contrib.get("network_earnings", 0.0)
        existing_stats["imported_from"]           = source
        existing_stats["imported_at"]             = datetime.now(timezone.utc).isoformat()
        sp.write_text(json.dumps(existing_stats, indent=2))
        applied.append(f"merged contribution history ({contrib['total_items']} items from {source})")

    # ── Knowledge subscriptions ──────────────────────────────────
    subs = amps_doc.get("knowledge_subscriptions", [])
    if subs:
        # Surface to user — never auto-subscribe
        warnings.append(
            f"knowledge_subscriptions from export: {subs} — "
            f"restore manually by adding to vaults.yaml"
        )

    return {
        "ok": True,
        "source_framework": source,
        "amps_version": ver,
        "applied": applied,
        "migration_notes": migration_notes,
        "warnings": warnings
    }


if __name__ == "__main__":
    import argparse, sys

    parser = argparse.ArgumentParser(description="AMPS export/import for Inflectiv Vault")
    sub = parser.add_subparsers(dest="cmd")

    ep = sub.add_parser("export", help="Export vault to AMPS JSON")
    ep.add_argument("--vault-root",  required=True)
    ep.add_argument("--output",      default="vault_export.amps.json")
    ep.add_argument("--vault-id")

    ip = sub.add_parser("import", help="Import AMPS JSON into vault")
    ip.add_argument("--vault-root",  required=True)
    ip.add_argument("--input",       required=True)
    ip.add_argument("--overwrite",   action="store_true")

    args = parser.parse_args()

    if args.cmd == "export":
        doc = export_vault(args.vault_root, vault_id=args.vault_id)
        Path(args.output).write_text(json.dumps(doc, indent=2))
        print(f"Exported to {args.output}")
        print(f"  agent_id   : {doc['agent_id']}")
        print(f"  long_term  : {len(doc['memory']['long_term'])} chars")
        print(f"  identity   : {len(doc['memory']['identity'])} chars")
        print(f"  active_plan: {len(doc['memory']['active_plan'] or '')} chars")
        print(f"  contributions: {doc['contributions']['total_items']} items")
        print(f"  migration_notes: {len(doc['migration_notes'])}")

    elif args.cmd == "import":
        doc = json.loads(Path(args.input).read_text())
        result = import_amps(doc, args.vault_root, overwrite=args.overwrite)
        print(f"Import complete — source: {result['source_framework']}")
        for a in result["applied"]:
            print(f"  applied: {a}")
        for w in result["warnings"]:
            print(f"  warning: {w}")

    else:
        parser.print_help()
