"""
Vault Memory Store — file-based Memory as Documentation (MAD) layer
Handles MEMORY.md, SOUL.md, task_plan.md, daily logs
"""
import os
import json
from datetime import datetime, timezone
from typing import Optional

MEMORY_ROOT = os.environ.get("VAULT_MEMORY_PATH", "/vault/memory")

CORE_FILES = ["MEMORY.md", "SOUL.md", "task_plan.md", "notes.md"]

class MemoryStore:
    def __init__(self, memory_root: str = MEMORY_ROOT):
        self.root = memory_root
        self.logs_dir = os.path.join(memory_root, "logs")
        os.makedirs(self.root, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)
        self._init_defaults()

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
                with open(fpath, "w") as f:
                    f.write(content)

    def _resolve(self, filename: str) -> str:
        """Resolve a filename to full path, handling logs/YYYY-MM-DD.md"""
        if filename.startswith("logs/"):
            return os.path.join(self.root, filename)
        return os.path.join(self.root, filename)

    def read(self, filename: str) -> Optional[str]:
        path = self._resolve(filename)
        if not os.path.exists(path):
            return None
        with open(path) as f:
            return f.read()

    def write(self, filename: str, content: str) -> dict:
        path = self._resolve(filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        # Check if appending to log (daily logs use append semantics)
        is_log = filename.startswith("logs/")
        mode = "a" if is_log else "w"
        with open(path, mode) as f:
            if is_log:
                f.write(f"\n---\n*{datetime.now(timezone.utc).isoformat()}*\n\n{content}\n")
            else:
                f.write(content)
        return {"file": filename, "size": os.path.getsize(path), "written": len(content)}

    def append(self, filename: str, content: str) -> dict:
        path = self._resolve(filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a") as f:
            f.write(f"\n{content}\n")
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
