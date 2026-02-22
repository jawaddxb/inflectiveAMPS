"""
Vault Query Engine — unified multi-vault search with conflict detection.
Checks: personal vault → shared vaults → VINN network.
Returns results + also_found for transparent conflict surfacing.
"""
import os
import json
import re
import hashlib
from datetime import datetime, timezone
from typing import Optional
from memory_store import MemoryStore

TAXONOMY_PATH = os.path.join(os.path.dirname(__file__), "taxonomy.json")
KNOWLEDGE_VAULTS_ROOT = os.environ.get("VAULT_KNOWLEDGE_PATH", os.path.join(os.path.dirname(__file__), "knowledge_vaults"))
INFLECTIV_API = os.environ.get("INFLECTIV_API_URL", "https://api.inflectiv.ai")
INFLECTIV_KEY = os.environ.get("INFLECTIV_API_KEY", "")


def _load_taxonomy() -> dict:
    if os.path.exists(TAXONOMY_PATH):
        with open(TAXONOMY_PATH) as f:
            return json.load(f)
    return {}


def _ts_sort_key(item: dict) -> str:
    return item.get("timestamp", "1970-01-01T00:00:00Z")


def _deduplicate(results: list) -> tuple[list, list]:
    """
    Given a flat list of results, return (primary, also_found).
    Primary = highest-confidence per unique topic (recency wins on tie).
    also_found = conflicting/duplicate entries surfaced transparently.
    """
    seen: dict[str, dict] = {}   # content_key → best result
    conflicts: list = []

    for item in results:
        # content fingerprint: hash of full content for accurate deduplication
        key = hashlib.sha256(item["content"].strip().lower().encode()).hexdigest()
        if key not in seen:
            seen[key] = item
        else:
            # keep more recent, surface older as conflict
            existing = seen[key]
            if _ts_sort_key(item) > _ts_sort_key(existing):
                conflicts.append(existing)
                seen[key] = item
            else:
                conflicts.append(item)

    primary = sorted(seen.values(), key=_ts_sort_key, reverse=True)
    return primary, conflicts


class QueryEngine:
    def __init__(self, personal_store: MemoryStore, vault_configs: Optional[list] = None):
        """
        vault_configs: list of dicts with keys:
          { "name": str, "path": str, "type": "shared"|"knowledge" }
        """
        self.personal = personal_store
        self.vault_configs = vault_configs or []
        self.taxonomy = _load_taxonomy()

    def _search_memory_store(self, store: MemoryStore, query: str,
                              source_name: str, source_type: str) -> list:
        raw = store.search(query)
        results = []
        for hit in raw:
            for lineno, line in hit["matches"]:
                results.append({
                    "content": line,
                    "file": hit["file"],
                    "line": lineno,
                    "source": source_name,
                    "source_type": source_type,
                    "timestamp": hit["timestamp"]
                })
        return results

    def _search_knowledge_vault(self, vault_path: str, vault_name: str,
                                 query: str) -> list:
        """Search a local knowledge vault directory"""
        store = MemoryStore(memory_root=vault_path)
        return self._search_memory_store(store, query, vault_name, "knowledge_vault")

    def _search_remote_vault(self, url: str, token: str,
                             vault_name: str, query: str) -> list:
        """
        v1.1: Query a remote vault over HTTP.
        Calls POST {url}/vault/query on the remote FastAPI vault server.
        Falls back gracefully if unreachable.
        """
        if url.startswith("http://"):
            import sys
            print(f"[vault] WARNING: remote vault '{vault_name}' uses HTTP — "
                  f"token will be sent in plaintext. Use HTTPS in production.",
                  file=sys.stderr)
        try:
            import urllib.request
            payload = json.dumps({"q": query, "include_network": False}).encode()
            req = urllib.request.Request(
                f"{url.rstrip('/')}/vault/query",
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Vault-Token": token
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read())
            results = []
            for item in data.get("results", []):
                results.append({
                    "content":     item.get("content", ""),
                    "file":        item.get("file", ""),
                    "line":        item.get("line", 0),
                    "source":      vault_name,
                    "source_type": "remote_vault",
                    "timestamp":   item.get("timestamp",
                                            datetime.now(timezone.utc).isoformat()),
                    "remote_url":  url
                })
            return results
        except Exception as e:
            # Remote vault unreachable — degrade gracefully, log once
            import sys
            print(f"[vault] remote vault {vault_name} ({url}) unreachable: {e}",
                  file=sys.stderr)
            return []


    def _search_inflectiv(self, query: str) -> list:
        """Query Inflectiv VINN network — returns structured results"""
        if not INFLECTIV_KEY:
            return []
        try:
            import urllib.request
            payload = json.dumps({"query": query, "limit": 10}).encode()
            req = urllib.request.Request(
                f"{INFLECTIV_API}/v1/query",
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": INFLECTIV_KEY
                }
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
                results = []
                for item in data.get("results", []):
                    results.append({
                        "content": str(item.get("content", item)),
                        "source": "inflectiv_vinn",
                        "source_type": "network",
                        "timestamp": item.get("timestamp",
                                               datetime.now(timezone.utc).isoformat()),
                        "dataset": item.get("dataset", "")
                    })
                return results
        except Exception:
            return []

    def classify(self, text: str) -> list:
        """Classify text against taxonomy — returns list of matching categories"""
        matches = []
        text_lower = text.lower()
        for category, cfg in self.taxonomy.get("categories", {}).items():
            score = 0
            matched_terms = []
            for term in cfg.get("terms", []):
                if term.lower() in text_lower:
                    score += 1
                    matched_terms.append(term)
            if score > 0:
                confidence = min(1.0, score / max(3, len(cfg.get("terms", [])) * 0.3))
                matches.append({
                    "category": category,
                    "vinn": cfg.get("vinn", ""),
                    "confidence": round(confidence, 3),
                    "matched_terms": matched_terms
                })
        matches.sort(key=lambda x: x["confidence"], reverse=True)
        return matches

    def query(self, q: str, include_network: bool = True) -> dict:
        """
        Unified vault query:
        1. Personal vault (highest priority)
        2. Shared/knowledge vaults (config order)
        3. Inflectiv VINN network (if enabled)
        Returns: { results, also_found, sources_checked, query }
        """
        all_results = []
        sources_checked = []

        # 1. Personal vault
        personal_hits = self._search_memory_store(
            self.personal, q, "personal", "personal_vault"
        )
        all_results.extend(personal_hits)
        sources_checked.append({"name": "personal", "hits": len(personal_hits)})

        # 2. Connected vaults (shared / knowledge)
        kv_root = KNOWLEDGE_VAULTS_ROOT
        if os.path.isdir(kv_root):
            for vault_dir in sorted(os.listdir(kv_root)):
                vault_path = os.path.join(kv_root, vault_dir)
                if os.path.isdir(vault_path):
                    hits = self._search_knowledge_vault(vault_path, vault_dir, q)
                    all_results.extend(hits)
                    sources_checked.append({"name": vault_dir, "hits": len(hits)})

        # User-configured shared vaults — local path OR remote URL (v1.1)
        for vc in self.vault_configs:
            vc_name = vc.get("name", "shared")
            if vc.get("url"):  # v1.1: remote HTTP vault
                hits = self._search_remote_vault(
                    vc["url"], vc.get("token", ""), vc_name, q
                )
                all_results.extend(hits)
                sources_checked.append({"name": vc_name,
                                         "hits": len(hits),
                                         "type": "remote_vault"})
            elif os.path.isdir(vc.get("path", "")):
                hits = self._search_knowledge_vault(
                    vc["path"], vc_name, q
                )
                all_results.extend(hits)
                sources_checked.append({"name": vc_name, "hits": len(hits),
                                         "type": "local_vault"})

        # 3. Inflectiv VINN network
        if include_network:
            network_hits = self._search_inflectiv(q)
            all_results.extend(network_hits)
            sources_checked.append({"name": "inflectiv_vinn",
                                     "hits": len(network_hits)})

        # Deduplicate + surface conflicts
        primary, also_found = _deduplicate(all_results)

        return {
            "query": q,
            "results": primary[:20],
            "also_found": also_found[:10],
            "total_hits": len(all_results),
            "sources_checked": sources_checked,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
