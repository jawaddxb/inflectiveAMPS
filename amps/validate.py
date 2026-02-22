"""
AMPS Validator — validate an .amps.json file against the v1.0 schema.

Usage:
    python validate.py path/to/export.amps.json
    python validate.py path/to/export.amps.json --strict
    python validate.py path/to/export.amps.json --summary
"""
import json
import sys
import argparse
from pathlib import Path
from datetime import datetime

SCHEMA_PATH = Path(__file__).parent / "schema" / "amps_v1.schema.json"

REQUIRED_FIELDS = [
    "amps_version", "exported_at", "agent_id", "source_framework",
    "migration_notes", "memory", "secrets", "contributions"
]
REQUIRED_MEMORY = ["long_term", "identity"]
KNOWN_FRAMEWORKS = {"agent_zero", "autogpt", "crewai", "langgraph", "llamaindex", "openclaw", "custom"}


def _validate_jsonschema(doc: dict) -> list:
    """Validate against the JSON schema if jsonschema is available. Returns errors list."""
    try:
        import jsonschema
    except ImportError:
        return []  # graceful degradation — fall through to manual checks
    if not SCHEMA_PATH.exists():
        return []
    schema = json.loads(SCHEMA_PATH.read_text())
    errors = []
    validator = jsonschema.Draft202012Validator(schema)
    for err in validator.iter_errors(doc):
        path = ".".join(str(p) for p in err.absolute_path) if err.absolute_path else "(root)"
        errors.append(f"schema: {path} — {err.message}")
    return errors


def validate(doc: dict, strict: bool = False) -> tuple:
    """Returns (errors: list, warnings: list)"""
    errors, warnings = [], []

    # JSON Schema validation (if jsonschema is installed)
    schema_errors = _validate_jsonschema(doc)
    if schema_errors:
        errors.extend(schema_errors)
        return errors, warnings  # schema errors are authoritative — skip manual checks

    # Required fields (manual fallback when jsonschema not available)
    for f in REQUIRED_FIELDS:
        if f not in doc:
            errors.append(f"MISSING required field: {f}")

    if errors:  # stop early if structure broken
        return errors, warnings

    # amps_version
    if doc["amps_version"] != "1.0":
        errors.append(f'amps_version must be "1.0", got "{doc["amps_version"]}"')

    # exported_at — ISO 8601 check
    try:
        datetime.fromisoformat(doc["exported_at"].replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        errors.append(f"exported_at is not a valid ISO 8601 timestamp: {doc['exported_at']}")

    # agent_id
    if not doc["agent_id"]:
        errors.append("agent_id must not be empty")

    # source_framework
    if doc["source_framework"] not in KNOWN_FRAMEWORKS:
        if strict:
            errors.append(f"unknown source_framework: {doc['source_framework']}"
                          f" — valid: {sorted(KNOWN_FRAMEWORKS)}")
        else:
            warnings.append(f"unknown source_framework: {doc['source_framework']} — use 'custom' for non-standard frameworks")

    # memory fields
    mem = doc["memory"]
    if not isinstance(mem, dict):
        errors.append("memory must be an object")
    else:
        for mf in REQUIRED_MEMORY:
            if mf not in mem:
                errors.append(f"MISSING required memory field: memory.{mf}")
            elif mem[mf] is not None and not isinstance(mem[mf], str):
                errors.append(f"memory.{mf} must be a string or null, got {type(mem[mf]).__name__}")
        if "active_plan" in mem and mem["active_plan"] is not None:
            if not isinstance(mem["active_plan"], str):
                errors.append("memory.active_plan must be a string or null")
        extra_mem = set(mem.keys()) - {"long_term", "identity", "active_plan"}
        if extra_mem:
            warnings.append(f"unknown memory fields (will be ignored by importers): {extra_mem}")

    # secrets — MUST be empty
    if doc["secrets"] != []:
        errors.append("SECURITY: secrets must always be [] — credentials must never be exported")

    # migration_notes
    if not isinstance(doc["migration_notes"], list):
        errors.append("migration_notes must be an array")

    # contributions
    contrib = doc.get("contributions", {})
    if isinstance(contrib, dict):
        qs = contrib.get("quality_score")
        if qs is not None and not (0.0 <= qs <= 1.0):
            warnings.append(f"contributions.quality_score {qs} outside 0-1 range")

    # Substantive warnings (skip known default values from fresh vault exports)
    _DEFAULT_LT = {"# Agent Memory\n\n(empty)", "# Agent Memory\n\n_No memories yet. This file grows as your agent works._"}
    _DEFAULT_ID = {"# Agent Identity\n\n(not set)", "# Agent Soul\n\n## Identity\nI am an intelligent agent connected to the Inflectiv network."}
    mem = doc.get("memory", {})
    lt = mem.get("long_term", "")
    if not lt:
        warnings.append("memory.long_term is empty — export may not have captured any knowledge")
    elif lt.strip() in _DEFAULT_LT:
        pass  # default value from fresh vault — not a warning
    if not mem.get("identity"):
        warnings.append("memory.identity is not set — agent personality will not be migrated")
    elif mem.get("identity", "").strip() in _DEFAULT_ID:
        pass  # default value from fresh vault — not a warning
    if doc.get("migration_notes"):
        warnings.append(f"{len(doc['migration_notes'])} migration note(s) — review before import")

    return errors, warnings


def score(doc: dict, errors: list, warnings: list) -> int:
    """AMPS compatibility score 0-100."""
    s = 100
    s -= len(errors) * 20
    s -= len(warnings) * 5
    mem = doc.get("memory", {})
    if not mem.get("long_term") or "(empty)" in str(mem.get("long_term", "")):
        s -= 15
    if not mem.get("identity") or "(not set)" in str(mem.get("identity", "")):
        s -= 10
    if not mem.get("active_plan"):
        s -= 5
    contrib = doc.get("contributions", {})
    if contrib.get("total_items", 0) > 0:
        s += 5  # bonus for contribution history
    return max(0, min(100, s))


def main():
    parser = argparse.ArgumentParser(description="Validate an AMPS v1.0 export file")
    parser.add_argument("file", help="Path to .amps.json file")
    parser.add_argument("--strict", action="store_true",
                        help="Treat warnings as errors")
    parser.add_argument("--summary", action="store_true",
                        help="Summary output only (for CI)")
    args = parser.parse_args()

    path = Path(args.file)
    if not path.exists():
        print(f"ERROR: file not found: {path}", file=sys.stderr)
        sys.exit(2)

    try:
        doc = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        print(f"ERROR: invalid JSON: {e}", file=sys.stderr)
        sys.exit(2)

    errors, warnings = validate(doc, strict=args.strict)
    s = score(doc, errors, warnings)

    if args.summary:
        status = "PASS" if not errors else "FAIL"
        print(f"{status} | score={s} | errors={len(errors)} | warnings={len(warnings)} | {path.name}")
        sys.exit(0 if not errors else 1)

    print("\n AMPS Validator v1.0")
    print(f" File   : {path}")
    print(f" Agent  : {doc.get('agent_id', '?')  }")
    print(f" Source : {doc.get('source_framework', '?')}")
    print(f" Score  : {s}/100")
    print()

    if errors:
        print(f" ERRORS ({len(errors)}):")
        for e in errors:
            print(f"   ✗ {e}")
    if warnings:
        print(f" WARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"   ⚠  {w}")
    if not errors and not warnings:
        print(" ✓ Valid AMPS document — no issues found")
    elif not errors:
        print(f" ✓ Valid AMPS document ({len(warnings)} warning(s))")
    else:
        print(f" ✗ Invalid AMPS document ({len(errors)} error(s))")

    print()
    sys.exit(0 if not errors else 1)


if __name__ == "__main__":
    main()
