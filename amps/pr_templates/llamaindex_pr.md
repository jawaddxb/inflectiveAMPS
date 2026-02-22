## Add AMPS Memory Portability Support

**What this PR does:** Adds `amps-llamaindex` adapter enabling LlamaIndex users to export document store content to [AMPS format](https://github.com/inflectiv/amps) and import from any AMPS-compatible framework.

### The Problem

LlamaIndex's `SimpleDocumentStore` and `ChatMemoryBuffer` accumulate valuable knowledge, but:
- That knowledge is stored in framework-specific formats
- Switching index types or frameworks requires re-ingesting all documents
- No standard way to export "what the agent knows" as portable, readable context

### AMPS Integration

```python
from amps.adapters.llamaindex import LlamaIndexAdapter

# Export from storage context
adapter = LlamaIndexAdapter(
    storage_context=storage_ctx,
    system_prompt="You are a research assistant..."
)
doc = adapter.export()

# Import into new index
from llama_index.core import Document, VectorStoreIndex
result = adapter.import_amps(foreign_doc)
docs = [Document(text=d["text"], metadata=d["metadata"])
        for d in result["documents"]]
index = VectorStoreIndex.from_documents(docs)

# Or import directly into an existing index
adapter.import_amps(foreign_doc, index=existing_index)
```

### What Transfers
- Document text content from docstore → `memory.long_term`
- Chat history from `ChatMemoryBuffer` → appended to `long_term`
- All imported documents tagged with `amps_import: true` metadata

### Lossiness Contract
- **Not portable:** vector embeddings (re-computed on import), index type, query engine config
- `migration_notes` documents all dropped fields — nothing silently lost
- Embeddings are deterministic — re-computation is lossless for retrieval quality

### Files Changed
- `llama_index/amps_adapter.py` — ~240 lines, zero new dependencies for export
- `docs/memory_portability.md`

**Spec:** https://github.com/inflectiv/amps | **License:** MIT
