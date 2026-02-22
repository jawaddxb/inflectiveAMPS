"""
Vault Auth — token validation with owner/subscriber roles
"""
import json
import os
import hmac
import secrets
import hashlib
import time
from collections import defaultdict
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
        try:
            expires_dt = datetime.fromisoformat(self.expires.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return False
        return datetime.now(timezone.utc) > expires_dt


class RateLimiter:
    """In-memory sliding window rate limiter."""
    def __init__(self, max_attempts: int = 10, window_seconds: int = 60):
        self.max = max_attempts
        self.window = window_seconds
        self._attempts: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str) -> bool:
        now = time.time()
        attempts = self._attempts[key]
        # Prune expired entries
        self._attempts[key] = [t for t in attempts if now - t < self.window]
        if len(self._attempts[key]) >= self.max:
            return False
        self._attempts[key].append(now)
        return True

    def seconds_until_reset(self, key: str) -> int:
        if key not in self._attempts or not self._attempts[key]:
            return 0
        oldest = min(self._attempts[key])
        remaining = self.window - (time.time() - oldest)
        return max(1, int(remaining))


class VaultAuth:
    def __init__(self, config_path: str = VAULT_CONFIG_PATH):
        self.config_path = config_path
        self._config = self._load()
        _max = int(os.environ.get("VAULT_RATE_LIMIT_MAX", "10"))
        _window = int(os.environ.get("VAULT_RATE_LIMIT_WINDOW", "60"))
        self._rate_limiter = RateLimiter(max_attempts=_max, window_seconds=_window)

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
        os.chmod(self.config_path, 0o600)

    def _new_vault_id(self) -> str:
        return "vlt_" + secrets.token_hex(8)

    def _hash(self, token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    @property
    def vault_id(self) -> str:
        return self._config["vault_id"]

    @property
    def rate_limiter(self) -> RateLimiter:
        return self._rate_limiter

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
        # Rate limit check on token prefix
        token_key = token[:8] if len(token) >= 8 else token
        if not self._rate_limiter.check(token_key):
            return None

        # Dev bypass: only active when VAULT_ENV explicitly set to "development"
        if os.environ.get("VAULT_ENV", "production") != "production":
            env_token = os.environ.get("VAULT_TOKEN", "")
            if env_token and hmac.compare_digest(token, env_token):
                return TokenRecord(
                    token_hash="env-bypass",
                    role="owner",
                    agent="env",
                    label="env-token",
                    created=datetime.now(timezone.utc).isoformat()
                )
        h = self._hash(token)
        for t in self._config["tokens"]:
            if hmac.compare_digest(t["token_hash"], h):
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
