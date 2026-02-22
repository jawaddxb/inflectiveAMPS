"""
AMPS Adapter -- Agent Zero / Inflectiv Vault (Native, Lossless)
Reference implementation for AMPS v1.0.

Usage:
    from amps.adapters.agent_zero import AgentZeroAdapter
    adapter = AgentZeroAdapter(vault_root="/path/to/vault")
    doc = adapter.export()
    result = adapter.import_amps(foreign_doc)
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .base import AMPSAdapter, empty_amps


class AgentZeroAdapter(AMPSAdapter):
    FRAMEWORK = "agent_zero"

    def __init__(self, vault_root: str, stats_path: Optional[str] = None):
        self.root = Path(vault_root)
        self.stats_path = stats_path or str(self.root / "stats.json")

    def _read_md(self, filename: str) -> Optional[str]:
        p = self.root / filename
        if p.exists():
            content = p.read_text().strip()
            return content or None
        return None

    def _write_md(self, filename: str, content: str, source_heading: str,
                  overwrite: bool = False):
        p = self.root / filename
        p.parent.mkdir(parents=True, exist_ok=True)
        if overwrite or not p.exists():
            p.write_text(content.strip() + "\n")
        else:
            existing = p.read_text().strip()
            block = ("\n\n---\n"
                     f"## Imported from {source_heading}\n\n"
                     + content.strip())
            p.write_text(existing + block + "\n")

    def _load_stats(self) -> dict:
        try:
            return json.loads(Path(self.stats_path).read_text())
        except Exception:
            return {}

    def export(self, agent_id: Optional[str] = None, **kwargs) -> dict:
        """Lossless export from Agent Zero / Inflectiv Vault."""
        doc = empty_amps(
            agent_id or f"vlt_{self.root.name}",
            self.FRAMEWORK
        )
        doc["memory"]["long_term"]   = self._read_md("MEMORY.md")
        doc["memory"]["identity"]    = self._read_md("SOUL.md")
        doc["memory"]["active_plan"] = self._read_md("task_plan.md")

        # knowledge_subscriptions from vaults.yaml if present
        vaults_yaml = self.root / "vaults.yaml"
        if vaults_yaml.exists():
            try:
                import yaml
                cfg = yaml.safe_load(vaults_yaml.read_text()) or {}
                doc["knowledge_subscriptions"] = [
                    v.get("name", str(i)) for i, v in enumerate(cfg.get("vaults", []))
                ]
            except Exception:
                pass

        # contributions from stats.json
        stats = self._load_stats()
        approved  = stats.get("approved_contributions", 0)
        staged    = stats.get("staged", 0)
        total     = approved + staged
        earnings  = approved * 0.5
        quality   = (approved / total) if total > 0 else 0.0
        doc["contributions"] = {
            "total_items":        total,
            "categories":         stats.get("categories", []),
            "quality_score":      round(quality, 3),
            "network_earnings":   earnings,
            "first_contribution": stats.get("first_contribution"),
            "last_contribution":  stats.get("last_contribution"),
        }
        return doc

    def import_amps(self, amps_doc: dict, overwrite: bool = False, **kwargs) -> dict:
        """Lossless import into Agent Zero / Inflectiv Vault."""
        self.root.mkdir(parents=True, exist_ok=True)
        applied, warnings = [], []
        source  = amps_doc.get("source_framework", "unknown")
        ver     = amps_doc.get("amps_version", "?")
        mem     = amps_doc.get("memory", {})
        notes   = amps_doc.get("migration_notes", [])
        heading = f"AMPS {ver} / {source}"

        if notes:
            warnings.extend([f"[migration] {n}" for n in notes])

        for md_file, field in (("MEMORY.md", "long_term"),
                               ("SOUL.md",   "identity"),
                               ("task_plan.md", "active_plan")):
            content = mem.get(field)
            if content:
                self._write_md(md_file, content, heading, overwrite)
                applied.append(f"{md_file} <- memory.{field}")

        # Merge contribution history
        incoming = amps_doc.get("contributions", {})
        if incoming.get("total_items", 0) > 0:
            stats = self._load_stats()
            stats["imported_contributions"] = incoming
            Path(self.stats_path).parent.mkdir(parents=True, exist_ok=True)
            Path(self.stats_path).write_text(json.dumps(stats, indent=2))
            applied.append(f"contributions history merged ({incoming['total_items']} items)")

        subs = amps_doc.get("knowledge_subscriptions", [])
        if subs:
            applied.append(f"knowledge_subscriptions noted: {subs} -- configure vaults.yaml to activate")

        return {
            "ok": True,
            "source_framework": source,
            "amps_version": ver,
            "applied": applied,
            "migration_notes": notes,
            "warnings": warnings
        }
