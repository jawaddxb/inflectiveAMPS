"""AMPS Adapter -- LangGraph. Lossiness: BEST-EFFORT."""
import json
from datetime import datetime, timezone
from pathlib import Path
from .base import AMPSAdapter, empty_amps
NL = "\n"
NL2 = "\n\n"
class LangGraphAdapter(AMPSAdapter):
    FRAMEWORK = "langgraph"
    def __init__(self, checkpointer=None, checkpoint_dir=None, graph=None, thread_id="default", system_prompt=None):
        self.checkpointer   = checkpointer
        self.checkpoint_dir = Path(checkpoint_dir) if checkpoint_dir else None
        self.graph = graph
        self.thread_id = thread_id
        self.system_prompt = system_prompt
    def _from_checkpointer(self):
        parts, notes = [], []
        try:
            config = {"configurable": {"thread_id": self.thread_id}}
            ckpt = self.checkpointer.get(config)
            if not ckpt: notes.append("no checkpoint for thread_id=" + self.thread_id); return parts, notes
            state = ckpt.get("channel_values", {})
            messages = state.get("messages", [])
            ai_msgs, human_msgs = [], []
            for msg in messages:
                mt = getattr(msg,"type","") or (msg.get("type","") if isinstance(msg,dict) else "")
                mc = getattr(msg,"content","") or (msg.get("content","") if isinstance(msg,dict) else str(msg))
                if mt in ("ai","assistant"): ai_msgs.append(mc)
                elif mt == "human": human_msgs.append(mc)
            if ai_msgs:
                parts.append("## Agent Outputs")
                parts.extend([str(m)[:500] for m in ai_msgs[-20:] if m])
            if human_msgs:
                parts.append("## Conversation Context")
                parts.extend(["Human: " + str(m)[:300] for m in human_msgs[-10:] if m])
            notes.append("checkpoint: " + str(len(messages)) + " messages")
            notes.append("graph topology not portable")
            for k in (k for k in state if k != "messages"):
                notes.append("state field " + repr(k) + " dropped")
        except Exception as ex:
            notes.append("checkpointer error: " + str(ex))
        return parts, notes
    def _from_dir(self):
        parts, notes = [], []
        if not self.checkpoint_dir or not self.checkpoint_dir.exists(): return parts, notes
        for f in sorted(self.checkpoint_dir.glob("*.json"))[-20:]:
            try:
                data = json.loads(f.read_text())
                if isinstance(data, dict):
                    c = data.get("content") or data.get("output") or data.get("text")
                    if c: parts.append("## " + f.stem + NL + str(c)[:500])
                elif isinstance(data, list):
                    for item in data[-5:]:
                        c = item.get("content","") if isinstance(item,dict) else ""
                        if c: parts.append(str(c)[:300])
            except Exception: pass
        if parts: notes.append("dir: " + str(len(parts)) + " checkpoint files")
        return parts, notes
    def export(self, agent_id=None, system_prompt=None, **kwargs):
        if system_prompt is None: system_prompt = self.system_prompt
        doc = empty_amps(agent_id or "langgraph_" + self.thread_id, self.FRAMEWORK)
        notes, lt = [], []
        if self.checkpointer:
            p, n = self._from_checkpointer(); lt.extend(p); notes.extend(n)
        elif self.checkpoint_dir:
            p, n = self._from_dir(); lt.extend(p); notes.extend(n)
        else:
            notes.append("no checkpointer or checkpoint_dir provided")
        doc["memory"]["long_term"] = ("# Agent Memory (LangGraph)" + NL2 + NL2.join(lt)) if lt else "# Agent Memory" + NL2 + "(empty)"
        doc["memory"]["identity"] = ("# Agent Identity (LangGraph)" + NL2 + system_prompt) if system_prompt else "# Agent Identity" + NL2 + "(not set)"
        notes.append("import: AMPS injected as initial HumanMessage")
        doc["migration_notes"] = notes
        doc['secrets'] = []  # Enforce: secrets NEVER exported — AMPS spec §2.1
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
        cp = []
        if identity:  cp.append("=== Imported Identity (" + source + ") ===" + NL + identity)
        if lt:        cp.append("=== Imported Knowledge (" + source + ") ===" + NL + lt[:4000])
        if plan:      cp.append("=== Imported Plan (" + source + ") ===" + NL + plan)
        context = NL2.join(cp)
        ts = datetime.now(timezone.utc).isoformat()
        initial_messages = [{"type":"human","content":"[AMPS Import from " + source + " at " + ts + "]" + NL2 + context}] if context else []
        applied.append("initial_messages ready (" + str(len(initial_messages)) + " msg)")
        applied.append("apply: graph.invoke(messages=result['initial_messages'] + msgs)")
        return {"ok": True, "source_framework": source, "amps_version": ver,
                "initial_messages": initial_messages, "context": context,
                "applied": applied, "migration_notes": notes, "warnings": warnings}
