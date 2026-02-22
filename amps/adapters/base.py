"""
AMPS Adapter Base Class
All framework adapters inherit from AMPSAdapter.
"""
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional
import json

AMPS_VERSION = "1.0"


def empty_amps(agent_id: str, source_framework: str) -> dict:
    """Return a blank AMPS document skeleton."""
    return {
        "amps_version": AMPS_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "agent_id": agent_id,
        "source_framework": source_framework,
        "migration_notes": [],
        "memory": {
            "long_term":   None,
            "identity":    None,
            "active_plan": None,
        },
        "secrets": [],   # NEVER populated — by spec
        "knowledge_subscriptions": [],
        "contributions": {
            "total_items":         0,
            "categories":          [],
            "quality_score":       0.0,
            "network_earnings":    0.0,
            "first_contribution": None,
            "last_contribution":  None,
        }
    }


class AMPSAdapter(ABC):
    """
    Abstract base for all AMPS adapters.

    Implement `export()` and `import_amps()` for each framework.
    The lossiness contract:
      - Agent Zero (native): lossless
      - All others:          best-effort; use migration_notes for anything dropped
    """

    FRAMEWORK = "custom"  # override in subclass

    @abstractmethod
    def export(self, **kwargs) -> dict:
        """
        Export framework state to AMPS dict.
        Must return a valid AMPS document.
        Secrets MUST NOT be included.
        """
        ...

    @abstractmethod
    def import_amps(self, amps_doc: dict, **kwargs) -> dict:
        """
        Import an AMPS document into the framework.
        Must return:
          { ok, applied: list[str], migration_notes: list[str], warnings: list[str] }
        """
        ...

    def validate(self, doc: dict) -> list:
        """Basic structural validation. Returns list of error strings (empty = valid)."""
        errors = []
        for field in ("amps_version", "exported_at", "agent_id", "source_framework",
                      "migration_notes", "memory", "secrets", "contributions"):
            if field not in doc:
                errors.append(f"missing required field: {field}")
        if "memory" in doc:
            for mf in ("long_term", "identity"):
                if mf not in doc["memory"]:
                    errors.append(f"missing memory.{mf}")
        if doc.get("secrets") != []:
            errors.append("secrets must always be [] — credentials must not be exported")
        return errors
