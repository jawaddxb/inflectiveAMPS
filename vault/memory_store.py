"""
Vault Memory Store — file-based Memory as Documentation (MAD) layer
Handles MEMORY.md, SOUL.md, task_plan.md, daily logs
Supports optional transparent Fernet encryption at rest.
"""
import os
import sys
import json
import secrets as _secrets
from datetime import datetime, timezone
from typing import Optional

MEMORY_ROOT = os.environ.get("VAULT_MEMORY_PATH", "/vault/memory")

CORE_FILES = ["MEMORY.md", "SOUL.md", "task_plan.md", "notes.md"]

# Fernet prefix — base64-encoded Fernet tokens always start with this
_FERNET_PREFIX = b"gAAAAA"


def _derive_memory_key(master_password: str, memory_root: str) -> bytes:
    """Derive a Fernet key from master password using PBKDF2 with a memory-specific salt."""
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    import base64

    salt_path = os.path.join(memory_root, ".mem_salt")
    if os.path.exists(salt_path):
        with open(salt_path, "rb") as f:
            salt = f.read()
    else:
        salt = _secrets.token_bytes(32)
        with open(salt_path, "wb") as f:
            f.write(salt)
        os.chmod(salt_path, 0o600)

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=600_000,
    )
    raw_key = kdf.derive(master_password.encode())
    # Fernet requires a url-safe base64-encoded 32-byte key
    return base64.urlsafe_b64encode(raw_key)


class MemoryStore:
    def __init__(self, memory_root: str = MEMORY_ROOT, encryption_key: str = None):
        """
        Args:
            memory_root: Path to memory directory.
            encryption_key: Master password for at-rest encryption. If None, no encryption.
        """
        self.root = memory_root
        self.logs_dir = os.path.join(memory_root, "logs")
        os.makedirs(self.root, mode=0o700, exist_ok=True)
        os.makedirs(self.logs_dir, mode=0o700, exist_ok=True)

        # Encryption setup
        self._fernet = None
        if encryption_key:
            try:
                from cryptography.fernet import Fernet
                fernet_key = _derive_memory_key(encryption_key, self.root)
                self._fernet = Fernet(fernet_key)
            except ImportError:
                print("[vault] WARNING: cryptography not installed — memory encryption disabled",
                      file=sys.stderr)

        self._init_defaults()
        if self._fernet:
            self._migrate_plaintext_files()

    def _encrypt(self, content: str) -> bytes:
        """Encrypt content string to Fernet token bytes."""
        if self._fernet:
            return self._fernet.encrypt(content.encode())
        return content.encode()

    def _decrypt(self, raw: bytes) -> str:
        """Decrypt Fernet token bytes to content string, or pass through plaintext."""
        if self._fernet and raw.startswith(_FERNET_PREFIX):
            return self._fernet.decrypt(raw).decode()
        # Not encrypted (plaintext) — return as-is
        return raw.decode()

    def _migrate_plaintext_files(self):
        """One-time migration: encrypt any existing plaintext memory files."""
        for root, dirs, fnames in os.walk(self.root):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for fname in fnames:
                if fname.startswith("."):
                    continue
                full = os.path.join(root, fname)
                try:
                    with open(full, "rb") as f:
                        raw = f.read()
                    if not raw or raw.startswith(_FERNET_PREFIX):
                        continue  # Already encrypted or empty
                    # Plaintext — encrypt and rewrite
                    encrypted = self._fernet.encrypt(raw)
                    with open(full, "wb") as f:
                        f.write(encrypted)
                    os.chmod(full, 0o600)
                    rel = os.path.relpath(full, self.root)
                    print(f"[vault] Migrated plaintext → encrypted: {rel}", file=sys.stderr)
                except Exception as e:
                    rel = os.path.relpath(full, self.root)
                    print(f"[vault] WARNING: could not migrate {rel}: {e}", file=sys.stderr)

    def _init_defaults(self):
        """Seed default files if they don't exist"""
        defaults = {
            "MEMORY.md": "# Agent Memory\n\n_No memories yet. This file grows as your agent works._\n",
            "SOUL.md": "# Agent Soul\n\n## Identity\nI am an intelligent agent connected to the Inflectiv network.\n\n## Principles\n- I prefer structured data over raw web scraping\n- I check my vault before searching the web\n- I contribute valuable intelligence to the network\n",
            "task_plan.md": "# Active Task Plan\n\n_No active task._\n",
            "notes.md": "# Working Notes\n\n_Notes from current research session._\n"
        }
        for fname, content in defaults.items():
            fpath = os.path.join(self.root, fname)
            if not os.path.exists(fpath):
                with open(fpath, "wb") as f:
                    f.write(self._encrypt(content))
                os.chmod(fpath, 0o600)

    def _resolve(self, filename: str) -> str:
        """Resolve a filename to full path, rejecting path traversal attempts."""
        joined = os.path.join(self.root, filename)
        real = os.path.realpath(joined)
        root_real = os.path.realpath(self.root)
        if not real.startswith(root_real + os.sep) and real != root_real:
            raise PermissionError(f"Path traversal denied: {filename}")
        return real

    def read(self, filename: str) -> Optional[str]:
        path = self._resolve(filename)
        if not os.path.exists(path):
            return None
        with open(path, "rb") as f:
            raw = f.read()
        return self._decrypt(raw)

    def write(self, filename: str, content: str, mode: str = "write") -> dict:
        path = self._resolve(filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if mode == "append":
            existing = self.read(filename) or ""
            content_full = existing + f"\n{content}\n"
            with open(path, "wb") as f:
                f.write(self._encrypt(content_full))
        elif filename.startswith("logs/"):
            existing = self.read(filename) or ""
            content_full = existing + f"\n---\n*{datetime.now(timezone.utc).isoformat()}*\n\n{content}\n"
            with open(path, "wb") as f:
                f.write(self._encrypt(content_full))
        else:
            with open(path, "wb") as f:
                f.write(self._encrypt(content))
        os.chmod(path, 0o600)
        return {"file": filename, "size": os.path.getsize(path), "written": len(content)}

    def append(self, filename: str, content: str) -> dict:
        path = self._resolve(filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        existing = self.read(filename) or ""
        content_full = existing + f"\n{content}\n"
        with open(path, "wb") as f:
            f.write(self._encrypt(content_full))
        os.chmod(path, 0o600)
        return {"file": filename, "size": os.path.getsize(path)}

    def today_log(self) -> str:
        """Return today's log filename"""
        return f"logs/{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.md"

    def load_session_context(self) -> dict:
        """Load files auto-included at session start: MEMORY.md + last 2 daily logs"""
        context = {}
        for fname in ["MEMORY.md", "SOUL.md", "task_plan.md"]:
            content = self.read(fname)
            if content:
                context[fname] = content
        # today + yesterday logs
        from datetime import timedelta
        for delta in [0, 1]:
            day = (datetime.now(timezone.utc) - timedelta(days=delta)).strftime("%Y-%m-%d")
            log = f"logs/{day}.md"
            content = self.read(log)
            if content:
                context[log] = content
        return context

    def list_files(self) -> list:
        files = []
        for root, dirs, fnames in os.walk(self.root):
            # skip hidden
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for fname in fnames:
                if fname.startswith("."):
                    continue
                full = os.path.join(root, fname)
                rel = os.path.relpath(full, self.root)
                files.append({
                    "file": rel,
                    "size": os.path.getsize(full),
                    "modified": datetime.fromtimestamp(
                        os.path.getmtime(full), tz=timezone.utc
                    ).isoformat()
                })
        return sorted(files, key=lambda x: x["file"])

    def search(self, query: str) -> list:
        """Token-based search across all memory files — all query tokens must appear"""
        results = []
        # split into tokens, ignore short stopwords
        tokens = [t for t in query.lower().split() if len(t) > 2]
        if not tokens:
            return results
        for item in self.list_files():
            content = self.read(item["file"])
            if not content:
                continue
            content_lower = content.lower()
            # file must contain ALL tokens (anywhere)
            if not all(t in content_lower for t in tokens):
                continue
            # find lines that contain ANY token
            lines = [
                (i+1, line.strip())
                for i, line in enumerate(content.splitlines())
                if line.strip() and any(t in line.lower() for t in tokens)
            ]
            if lines:
                results.append({
                    "file": item["file"],
                    "matches": lines[:5],
                    "source": "personal_vault",
                    "timestamp": item["modified"]
                })
        return results
