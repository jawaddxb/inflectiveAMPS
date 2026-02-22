"""
Inflectiv Vault Client SDK — multi-vault support
One interface: personal vault + N knowledge vaults
"""
import json
import os
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Optional


class VaultError(Exception):
    pass


@dataclass
class VaultResult:
    content: str
    source: str
    source_type: str
    timestamp: str
    file: str = ""
    line: int = 0
    dataset: str = ""

    def __str__(self) -> str:
        return f"[{self.source}|{self.source_type}] {self.content}"


@dataclass
class QueryResponse:
    results: list
    also_found: list
    sources_checked: list
    total_hits: int

    def primary(self) -> Optional[VaultResult]:
        return self.results[0] if self.results else None


class SingleVault:
    """Connection to a single vault instance."""
    def __init__(self, url: str, token: str, name: str = "vault",
                 role: str = "owner", timeout: int = 10):
        url = url.rstrip("/")
        if not url.startswith("http"):
            url = f"http://{url}"
        self.url = url
        self.token = token
        self.name = name
        self.role = role
        self.timeout = timeout

    def _req(self, method: str, path: str, body: dict = None) -> dict:
        url = self.url + path
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            url, data=data, method=method,
            headers={
                "Content-Type": "application/json",
                "X-Vault-Token": self.token
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body_text = e.read().decode(errors="replace")
            raise VaultError(f"HTTP {e.code} {path}: {body_text}") from e
        except urllib.error.URLError as e:
            raise VaultError(f"Cannot reach vault at {self.url}: {e.reason}") from e

    def ping(self) -> bool:
        try:
            r = self._req("GET", "/health")
            return r.get("status") == "ok"
        except VaultError:
            return False

    def query_raw(self, q: str) -> dict:
        return self._req("POST", "/vault/query", {"q": q, "include_network": False})


class VaultClient:
    """
    Multi-vault client — personal vault + N knowledge vaults.

    Config format (vaults.yaml or dict):
        personal:
          url: http://localhost:8766
          token: vtok_...
          role: owner
        knowledge_vaults:
          - name: defi_intel
            url: http://localhost:8766
            token: vtok_subscriber_...
            role: subscriber

    Single-vault shorthand (backwards compatible):
        VaultClient(url, token)
    """

    KNOWN_RESULT_FIELDS = {"content", "source", "source_type", "timestamp", "file", "line", "dataset"}

    def __init__(self, url_or_config=None, token: str = None, timeout: int = 10):
        self.timeout = timeout
        self._vaults: list = []   # ordered: personal first, then knowledge vaults
        self._personal: Optional[SingleVault] = None

        if isinstance(url_or_config, str) and token:
            # Backwards-compatible single vault
            v = SingleVault(url_or_config, token, name="personal", role="owner", timeout=timeout)
            self._personal = v
            self._vaults = [v]
        elif isinstance(url_or_config, dict):
            self._load_config(url_or_config)
        elif isinstance(url_or_config, str) and url_or_config.endswith((".yaml", ".yml", ".json")):
            self._load_config_file(url_or_config)

    def _load_config(self, cfg: dict):
        """Load from config dict."""
        if "personal" in cfg:
            p = cfg["personal"]
            v = SingleVault(p["url"], p["token"], name="personal",
                           role=p.get("role", "owner"), timeout=self.timeout)
            self._personal = v
            self._vaults.append(v)
        for kv in cfg.get("knowledge_vaults", []):
            v = SingleVault(kv["url"], kv["token"],
                           name=kv.get("name", "knowledge"),
                           role=kv.get("role", "subscriber"),
                           timeout=self.timeout)
            self._vaults.append(v)

    def _load_config_file(self, path: str):
        """Load from YAML or JSON config file."""
        if path.endswith(".json"):
            with open(path) as f:
                cfg = json.load(f)
        else:
            try:
                import yaml
                with open(path) as f:
                    cfg = yaml.safe_load(f)
            except ImportError:
                raise VaultError("PyYAML required for .yaml config: pip install pyyaml")
        self._load_config(cfg)

    @property
    def personal(self) -> Optional[SingleVault]:
        return self._personal

    def ping(self) -> bool:
        """Ping the personal vault."""
        if not self._personal:
            return False
        return self._personal.ping()

    def ping_all(self) -> dict:
        """Ping all connected vaults."""
        return {v.name: v.ping() for v in self._vaults}

    def _make_result(self, r: dict, vault_name: str) -> VaultResult:
        filtered = {k: v for k, v in r.items() if k in self.KNOWN_RESULT_FIELDS}
        # Override source with vault name for clarity in multi-vault context
        if "source" not in filtered:
            filtered["source"] = vault_name
        if "content" not in filtered:
            filtered["content"] = ""
        if "source_type" not in filtered:
            filtered["source_type"] = "unknown"
        if "timestamp" not in filtered:
            filtered["timestamp"] = ""
        return VaultResult(**filtered)

    def query(self, q: str) -> QueryResponse:
        """
        Query all connected vaults.
        Priority: personal vault first (wins on conflict), then knowledge vaults in order.
        Returns merged QueryResponse with conflicts in also_found.
        """
        all_results = []
        all_conflicts = []
        sources_checked = []
        seen_content_keys = {}  # normalised content → first source (for conflict detection)

        for vault in self._vaults:
            try:
                raw = vault.query_raw(q)
            except VaultError:
                continue

            for r in raw.get("results", []):
                result = self._make_result(r, vault.name)
                norm_key = result.content[:60].lower().strip()

                if norm_key in seen_content_keys:
                    # Conflict: same content from different vault
                    all_conflicts.append(result)
                else:
                    seen_content_keys[norm_key] = vault.name
                    all_results.append(result)

            sources_checked.append({"vault": vault.name, "role": vault.role,
                                     "hits": raw.get("total_hits", 0)})

        return QueryResponse(
            results=all_results,
            also_found=all_conflicts,
            sources_checked=sources_checked,
            total_hits=len(all_results)
        )

    def memory(self, filename: str = "MEMORY.md") -> str:
        """Read a memory file from personal vault."""
        if not self._personal:
            raise VaultError("No personal vault configured")
        r = self._personal._req("GET", f"/vault/memory/{filename}")
        return r.get("content", "")

    def remember(self, filename: str, content: str) -> bool:
        """Write to a memory file in personal vault."""
        if not self._personal:
            raise VaultError("No personal vault configured")
        r = self._personal._req("POST", f"/vault/memory/{filename}", {"content": content})
        return r.get("written", False)

    def context(self) -> dict:
        """Load full agent context (MEMORY.md + SOUL.md + task_plan.md)."""
        if not self._personal:
            raise VaultError("No personal vault configured")
        return self._personal._req("GET", "/vault/memory/context").get("context", {})

    def secret(self, key: str) -> str:
        """Retrieve a decrypted secret from personal vault."""
        if not self._personal:
            raise VaultError("No personal vault configured")
        return self._personal._req("GET", f"/vault/secrets/{key}").get("value", "")

    def store_secret(self, key: str, value: str, label: str = "") -> bool:
        """Store an encrypted secret in personal vault."""
        if not self._personal:
            raise VaultError("No personal vault configured")
        r = self._personal._req("POST", "/vault/secrets", {"key": key, "value": value, "label": label})
        return r.get("stored", False)

    def contribute(self, content: str) -> dict:
        """Stage a contribution to be reviewed and published to VINN."""
        if not self._personal:
            raise VaultError("No personal vault configured")
        return self._personal._req("POST", "/vault/contribute", {"content": content})


    def pending(self) -> list:
        """Return list of staged contributions awaiting approval"""
        if not self.personal:
            return []
        r = self.personal._req("GET", "/vault/contribute/pending")
        return r.get("pending", [])

    def approve(self, contribution_id: str) -> dict:
        """Approve a staged contribution — publishes to VINN, credits $INAI"""
        if not self.personal:
            return {"error": "no personal vault"}
        return self.personal._req("POST", f"/vault/pending/{contribution_id}/approve")

    def reject(self, contribution_id: str) -> dict:
        """Reject and discard a staged contribution"""
        if not self.personal:
            return {"error": "no personal vault"}
        return self.personal._req("DELETE", f"/vault/pending/{contribution_id}")

    def contribute_and_approve(self, content: str) -> dict:
        """Contribute content and immediately auto-approve (trust mode)"""
        c = self.contribute(content)
        cid = c.get("contribution_id")
        if cid:
            approval = self.approve(cid)
            c["approved"] = approval
        return c

    def export(self) -> dict:
        """Export vault state as AMPS v1.0 document (GET /vault/export)"""
        if not self.personal:
            return {"error": "no personal vault configured"}
        return self.personal._req("GET", "/vault/export")

    def import_amps(self, amps_doc: dict, overwrite: bool = False) -> dict:
        """Import an AMPS document into this vault (POST /vault/import)"""
        if not self.personal:
            return {"error": "no personal vault configured"}
        return self.personal._req("POST", "/vault/import",
                                   {"amps_doc": amps_doc, "overwrite": overwrite})

    def migrate_to(self, destination_url: str, destination_token: str,
                   overwrite: bool = False) -> dict:
        """
        Migrate this vault's AMPS export directly to a remote vault.
        One-call vault migration.
        """
        amps_doc = self.export()
        if "error" in amps_doc:
            return amps_doc
        # POST to remote vault
        import urllib.request, json as _json
        payload = _json.dumps({"amps_doc": amps_doc, "overwrite": overwrite}).encode()
        req = urllib.request.Request(
            f"{destination_url.rstrip('/')}/vault/import",
            data=payload,
            headers={"Content-Type": "application/json",
                     "X-Vault-Token": destination_token},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = _json.loads(resp.read())
        result["source_agent_id"] = amps_doc.get("agent_id")
        result["contributions_migrated"] = amps_doc.get("contributions", {}).get("total_items", 0)
        return result

    def stats(self) -> dict:
        """Get personal vault stats: ratio, $INAI earned, access tier."""
        if not self._personal:
            raise VaultError("No personal vault configured")
        return self._personal._req("GET", "/vault/stats")

    def create_subscriber_token(self, agent: str, label: str = "",
                                expires: str = None) -> str:
        """Create a read-only subscriber token (for sharing knowledge vault access)."""
        if not self._personal:
            raise VaultError("No personal vault configured")
        r = self._personal._req("POST", "/vault/tokens",
                                {"role": "subscriber", "agent": agent,
                                 "label": label, "expires": expires})
        return r.get("token", "")
