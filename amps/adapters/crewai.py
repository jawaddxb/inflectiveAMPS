"""AMPS Adapter -- CrewAI. Lossiness: BEST-EFFORT."""
import json
from datetime import datetime, timezone
from pathlib import Path
from .base import AMPSAdapter, empty_amps
NL = "\n"
NL2 = "\n\n"
class CrewAIAdapter(AMPSAdapter):
    FRAMEWORK = "crewai"
    def __init__(self, agents=None, crew=None, output_dir=None):
        self.agents = agents or []
        self.crew = crew
        self.output_dir = Path(output_dir) if output_dir else None
    def _ag(self, a):
        if hasattr(a, "__dict__"):
            return {"role": getattr(a,"role",""), "goal": getattr(a,"goal",""),
                    "backstory": getattr(a,"backstory",""),
                    "tools": [str(t) for t in getattr(a,"tools",[])]}
        return dict(a)
    def export(self, agent_id=None, **kwargs):
        doc = empty_amps(agent_id or "crewai_" + str(id(self.crew)), self.FRAMEWORK)
        notes, id_parts, lt = [], [], []
        for i, raw in enumerate(self.agents):
            ag = self._ag(raw)
            role = ag.get("role") or "unknown"
            goal = ag.get("goal") or ""
            bs   = ag.get("backstory") or ""
            tools = ag.get("tools") or []
            id_parts.append("## Agent " + str(i+1) + ": " + role)
            id_parts.append("Goal: " + goal)
            if bs: id_parts.append("Backstory: " + bs)
            if tools:
                notes.append("Agent " + str(i+1) + " (" + role + ") had " + str(len(tools)) + " tool(s) -- not portable")
                lt.append("## Agent " + str(i+1) + " Tools" + NL + NL.join("- " + str(t) for t in tools))
        if self.crew and hasattr(self.crew, "tasks"):
            for task in self.crew.tasks:
                out = getattr(task, "output", None)
                if out:
                    desc = getattr(task, "description", "Task")[:60]
                    lt.append("## Task Output: " + desc + NL + str(out)[:2000])
            notes.append("Crew topology not portable")
        if self.output_dir and self.output_dir.is_dir():
            for f in sorted(self.output_dir.glob("*.json"))[-10:]:
                try:
                    data = json.loads(f.read_text())
                    lt.append("## Saved Output (" + f.stem + ")" + NL + json.dumps(data,indent=2)[:1000])
                except Exception: pass
        doc["memory"]["identity"]  = ("# CrewAI Agent Identities" + NL2 + NL2.join(id_parts)) if id_parts else None
        doc["memory"]["long_term"] = ("# Task Knowledge" + NL2 + NL2.join(lt)) if lt else "# Agent Memory" + NL2 + "(empty)"
        doc["migration_notes"] = notes
        return doc
    def import_amps(self, amps_doc, **kwargs):
        applied, warnings = [], []
        source = amps_doc.get("source_framework", "unknown")
        ver    = amps_doc.get("amps_version", "?")
        mem    = amps_doc.get("memory", {})
        notes  = amps_doc.get("migration_notes", [])
        if notes: warnings.extend(["[migration] " + n for n in notes])
        lt       = mem.get("long_term", "")
        identity = mem.get("identity", "")
        plan     = mem.get("active_plan", "")
        bp = []
        if identity:  bp.append("[Imported identity from " + source + "]" + NL + identity)
        if lt:        bp.append("[Imported knowledge from " + source + "]" + NL + lt[:3000])
        if plan:      bp.append("[Imported plan from " + source + "]" + NL + plan)
        backstory_extension = NL2.join(bp)
        agent_memory = {"amps_source": source, "amps_version": ver,
                        "imported_at": datetime.now(timezone.utc).isoformat(),
                        "long_term": lt, "identity": identity}
        applied.append("backstory_extension ready (" + str(len(backstory_extension)) + " chars)")
        applied.append("agent_memory dict ready")
        return {"ok": True, "source_framework": source, "amps_version": ver,
                "backstory_extension": backstory_extension, "agent_memory": agent_memory,
                "raw_identity": identity, "applied": applied,
                "migration_notes": notes, "warnings": warnings}
