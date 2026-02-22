"""AMPS Adapter -- LlamaIndex. Lossiness: BEST-EFFORT."""
import json
from datetime import datetime, timezone
from pathlib import Path
from .base import AMPSAdapter, empty_amps
NL = "\n"
NL2 = "\n\n"
class LlamaIndexAdapter(AMPSAdapter):
    FRAMEWORK = "llamaindex"
    def __init__(self, storage_context=None, index=None, persist_dir=None, memory=None, system_prompt=None):
        self.storage_context = storage_context
        self.index = index
        self.persist_dir = Path(persist_dir) if persist_dir else None
        self.memory = memory
        self.system_prompt = system_prompt
    def _from_storage(self):
        parts, notes = [], []
        try:
            ds = getattr(self.storage_context, "docstore", None)
            if not ds and self.index:
                sc = getattr(self.index, "_storage_context", None)
                ds = getattr(sc, "docstore", None)
            if not ds: return parts, notes
            docs = ds.docs if hasattr(ds, "docs") else {}
            for doc_id, node in list(docs.items())[:50]:
                text = getattr(node,"text","") or getattr(node,"content","")
                if text and text.strip():
                    meta = getattr(node, "metadata", {}) or {}
                    src  = meta.get("file_name") or meta.get("source") or doc_id[:16]
                    parts.append("## " + src + NL + text.strip()[:1000])
            notes.append("docstore: " + str(len(docs)) + " nodes")
            notes.append("embeddings not portable -- re-computed on import")
        except Exception as ex:
            notes.append("docstore error: " + str(ex))
        return parts, notes
    def _from_dir(self):
        parts, notes = [], []
        if not self.persist_dir or not self.persist_dir.exists(): return parts, notes
        for fname in ("docstore.json", "default__vector_store.json"):
            fpath = self.persist_dir / fname
            if not fpath.exists(): continue
            try:
                data = json.loads(fpath.read_text())
                docs = data.get("docstore",{}).get("docs",{}) or data.get("embedding_dict",{})
                for doc_id, node in list(docs.items())[:30]:
                    text = (node.get("text","") if isinstance(node,dict) else str(node)[:500])
                    if text.strip(): parts.append("## node:" + doc_id[:12] + NL + text.strip()[:800])
                notes.append(fname + ": " + str(len(docs)) + " nodes")
                break
            except Exception as ex: notes.append(fname + " error: " + str(ex))
        return parts, notes
    def _from_memory(self):
        parts, notes = [], []
        try:
            msgs = (self.memory.get_all() if hasattr(self.memory,"get_all")
                    else getattr(self.memory, "chat_history", []))
            if msgs:
                parts.append("## Chat History")
                for m in msgs[-20:]:
                    role    = getattr(m, "role", str(m)[:10])
                    content = getattr(m, "content", str(m))
                    parts.append(str(role) + ": " + str(content)[:300])
                notes.append("ChatMemoryBuffer: " + str(len(msgs)) + " messages")
        except Exception as ex: notes.append("memory error: " + str(ex))
        return parts, notes
    def export(self, agent_id=None, system_prompt=None, **kwargs):
        if system_prompt is None: system_prompt = self.system_prompt
        doc = empty_amps(agent_id or "llamaindex_" + str(id(self.index)), self.FRAMEWORK)
        notes, lt = [], []
        if self.storage_context or self.index:
            p, n = self._from_storage(); lt.extend(p); notes.extend(n)
        elif self.persist_dir:
            p, n = self._from_dir(); lt.extend(p); notes.extend(n)
        if self.memory:
            p, n = self._from_memory(); lt.extend(p); notes.extend(n)
        if not lt: notes.append("no source provided -- long_term empty")
        doc["memory"]["long_term"] = ("# Document Knowledge (LlamaIndex)" + NL2 + NL2.join(lt)) if lt else "# Agent Memory" + NL2 + "(empty)"
        doc["memory"]["identity"] = ("# Agent Identity (LlamaIndex)" + NL2 + system_prompt) if system_prompt else "# Agent Identity" + NL2 + "(not set)"
        notes.append("import: content added as Document nodes")
        doc["migration_notes"] = notes
        doc['secrets'] = []  # Enforce: secrets NEVER exported — AMPS spec §2.1
        return doc
    def import_amps(self, amps_doc, index=None, **kwargs):
        applied, warnings = [], []
        source = amps_doc.get("source_framework", "unknown")
        ver    = amps_doc.get("amps_version", "?")
        mem    = amps_doc.get("memory", {})
        notes  = amps_doc.get("migration_notes", [])
        if notes: warnings.extend(["[migration] " + n for n in notes])
        ts = datetime.now(timezone.utc).isoformat()
        base_meta = {"amps_import": True, "amps_source": source, "amps_version": ver, "imported_at": ts}
        documents = []
        for field, label in (("long_term","memory"),("identity","identity"),("active_plan","plan")):
            content = mem.get(field)
            if content:
                documents.append({"text": content, "metadata": dict(base_meta, amps_field=field, label=label)})
        if index is not None:
            try:
                from llama_index.core import Document as LIDoc
                for d in documents: index.insert(LIDoc(text=d["text"], metadata=d["metadata"]))
                applied.append(str(len(documents)) + " doc(s) inserted into index")
            except ImportError: warnings.append("llama_index not installed")
            except Exception as ex: warnings.append("index.insert error: " + str(ex))
        else:
            applied.append(str(len(documents)) + " document dicts ready")
            applied.append("apply: VectorStoreIndex.from_documents(...)")
        return {"ok": True, "source_framework": source, "amps_version": ver,
                "documents": documents, "applied": applied,
                "migration_notes": notes, "warnings": warnings}
