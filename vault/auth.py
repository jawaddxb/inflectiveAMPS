"""
Vault Auth — token validation with owner/subscriber roles
"""
import json
import os
import secrets
import hashlib
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Optional

VAULT_CONFIG_PATH = os.environ.get("VAULT_CONFIG", os.path.join(os.environ.get("VAULT_ROOT", "/vault"), "vault_config.json"))

@dataclass
class TokenRecord:
    token_hash: str
    role: str           # "owner" | "subscriber"
    agent: str
    label: str
    created: str
    expires: Optional[str] = None  # ISO timestamp or None

    def is_expired(self) -> bool:
        if not self.expires:
            return False
        return datetime.now(timezone.utc).isoformat() > self.expires

class VaultAuth:
    def __init__(self, config_path: str = VAULT_CONFIG_PATH):
        self.config_path = config_path
        self._config = self._load()

    def _load(self) -> dict:
        if os.path.exists(self.config_path):
            cfg = json.load(open(self.config_path))
            # Backfill created_at if missing (existing vaults)
            if "created_at" not in cfg:
                cfg["created_at"] = datetime.now(timezone.utc).isoformat()
                os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
                with open(self.config_path, "w") as f:
                    json.dump(cfg, f, indent=2)
            return cfg
        return {"vault_id": self._new_vault_id(),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "tokens": []}

    def _save(self):
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump(self._config, f, indent=2)

    def _new_vault_id(self) -> str:
        return "vlt_" + secrets.token_hex(8)

    def _hash(self, token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    @property
    def vault_id(self) -> str:
        return self._config["vault_id"]

    def create_token(self, role: str = "owner", agent: str = "default",
                     label: str = "", expires: Optional[str] = None) -> str:
        token = "vtok_" + secrets.token_urlsafe(32)
        record = TokenRecord(
            token_hash=self._hash(token),
            role=role,
            agent=agent,
            label=label or f"{role}-{agent}",
            created=datetime.now(timezone.utc).isoformat(),
            expires=expires
        )
        self._config["tokens"].append(asdict(record))
        self._save()
        return token

    def validate(self, token: str) -> Optional[TokenRecord]:
        # Dev bypass: only active when VAULT_ENV != "production"
        if os.environ.get("VAULT_ENV", "development") != "production":
            env_token = os.environ.get("VAULT_TOKEN", "")
            if env_token and token == env_token:
                return TokenRecord(
                    token_hash="env-bypass",
                    role="owner",
                    agent="env",
                    label="env-token",
                    created=datetime.now(timezone.utc).isoformat()
                )
        h = self._hash(token)
        for t in self._config["tokens"]:
            if t["token_hash"] == h:
                record = TokenRecord(**t)
                if record.is_expired():
                    return None
                return record
        return None

    def revoke(self, token: str) -> bool:
        h = self._hash(token)
        before = len(self._config["tokens"])
        self._config["tokens"] = [t for t in self._config["tokens"] if t["token_hash"] != h]
        if len(self._config["tokens"]) < before:
            self._save()
            return True
        return False

    def list_tokens(self) -> list:
        return [
            {k: v for k, v in t.items() if k != "token_hash"}
            for t in self._config["tokens"]
        ]
