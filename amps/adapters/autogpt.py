"""AMPS Adapter -- AutoGPT. Lossiness: BEST-EFFORT."""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from .base import AMPSAdapter, empty_amps
NL = "\n"
NL2 = "\n\n"
class AutoGPTAdapter(AMPSAdapter):
    FRAMEWORK = "autogpt"
    def __init__(self, workspace_dir):
        self.workspace = Path(workspace_dir)
    def export(self, agent_id=None, **kwargs):
        doc = empty_amps(agent_id or "autogpt_" + self.workspace.name, self.FRAMEWORK)
        notes, lt, id_parts = [], [], []
        mf = self.workspace / "memory_summary.json"
        if mf.exists():
            try:
                mem = json.loads(mf.read_text())
                entries = mem if isinstance(mem, list) else [mem]
                for e in entries:
                    txt = (e.get("content") or e.get("text") or str(e)) if isinstance(e,dict) else str(e)
                    lt.append(txt.strip())
                notes.append("memory_summary.json: " + str(len(entries)) + " entries exported")
            except Exception as ex:
                notes.append("memory_summary.json error: " + str(ex))
        for cfg_name in ("agent_config.json", "auto-gpt.json", "config.json"):
            cf = self.workspace / cfg_name
            if cf.exists():
                try:
                    cfg = json.loads(cf.read_text())
                    role = cfg.get("role") or cfg.get("ai_role") or cfg.get("name") or "AutoGPT Agent"
                    goals = cfg.get("goals") or cfg.get("ai_goals") or []
                    id_parts.append("# Agent Identity")
                    id_parts.append("Role: " + role)
                    if goals:
                        id_parts.append("Goals:")
                        id_parts.extend(["- " + str(g) for g in goals])
                    tools = cfg.get("plugins") or cfg.get("tools") or []
                    constraints = cfg.get("constraints") or []
                    if tools:
                        notes.append(str(len(tools)) + " plugin/tool configs not portable")
                        lt.append("## AutoGPT Tool Configs" + NL + json.dumps(tools, indent=2))
                    if constraints:
                        notes.append(str(len(constraints)) + " constraint(s) in long_term")
                        lt.append("## Constraints" + NL + NL.join("- " + str(c) for c in constraints))
                    break
                except Exception as ex:
                    notes.append(cfg_name + " error: " + str(ex))
        for h in ("command_history.json", "history.json"):
            if (self.workspace / h).exists():
                notes.append("command history not exported: " + h)
                break
        doc["memory"]["long_term"] = ("# Agent Memory" + NL2 + NL2.join(lt)) if lt else "# Agent Memory" + NL2 + "(empty)"
        doc["memory"]["identity"] = NL.join(id_parts) if id_parts else "# Agent Identity" + NL2 + "(not set)"
        doc["migration_notes"] = notes
        return doc
    def import_amps(self, amps_doc, overwrite=False, **kwargs):
        self.workspace.mkdir(parents=True, exist_ok=True)
        applied, warnings = [], []
        source = amps_doc.get("source_framework", "unknown")
        ver    = amps_doc.get("amps_version", "?")
        mem    = amps_doc.get("memory", {})
        notes  = amps_doc.get("migration_notes", [])
        if notes: warnings.extend(["[migration] " + n for n in notes])
        lt = mem.get("long_term")
        if lt:
            mf = self.workspace / "memory_summary.json"
            existing = []
            if mf.exists() and not overwrite:
                try:
                    existing = json.loads(mf.read_text())
                    if not isinstance(existing, list): existing = []
                except Exception: pass
            entry = {"source": "amps_from_" + source,
                     "imported_at": datetime.now(timezone.utc).isoformat(),
                     "amps_version": ver, "content": lt}
            mf.write_text(json.dumps([entry] + existing, indent=2))
            applied.append("long_term -> memory_summary.json")
        identity = mem.get("identity")
        if identity:
            cf = self.workspace / "agent_config.json"
            cfg = {}
            if cf.exists() and not overwrite:
                try: cfg = json.loads(cf.read_text())
                except Exception: pass
            cfg["amps_imported_identity"] = identity
            cfg["amps_source"] = source
            if "role" not in cfg: cfg["role"] = "Agent (imported from " + source + " via AMPS)"
            cf.write_text(json.dumps(cfg, indent=2))
            applied.append("identity -> agent_config.json")
        subs = amps_doc.get("knowledge_subscriptions", [])
        if subs: warnings.append("knowledge_subscriptions not applicable in AutoGPT")
        return {"ok": True, "source_framework": source, "amps_version": ver,
                "applied": applied, "migration_notes": notes, "warnings": warnings}
