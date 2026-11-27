#!/usr/bin/env python3
"""PreToolUse(Edit|Write|MultiEdit): protect files that change another way. Exit 2 = block."""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def frozen_spec(path: Path) -> bool:
    """Files in an approved or implemented spec version directory are immutable (ADR-0007)."""
    try:
        rel = path.resolve().relative_to(ROOT / "spec")
    except ValueError:
        return False
    if len(rel.parts) < 3:
        return False
    spec_md = ROOT / "spec" / rel.parts[0] / rel.parts[1] / "spec.md"
    if not spec_md.exists():
        return False
    match = re.search(r"^status:\s*(\w+)", spec_md.read_text(), re.M)
    return bool(match and match.group(1) in {"approved", "implemented"})


def reason(file_path: str) -> str | None:
    path = Path(file_path)
    name = path.name
    if name.startswith(".env") and name != ".env.example":
        return ".env files hold secrets and are off-limits. Document variables in .env.example."
    if name in {"uv.lock", "pnpm-lock.yaml"}:
        return f"{name} changes only through the package manager (uv add / pnpm add)."
    posix = path.as_posix()
    if "/apps/web/src/gen/" in posix or posix.endswith(
        "packages/core/schema/agent-spec.schema.json"
    ):
        return "Generated file. Change packages/core/src/ovas_core/spec.py, then run `make gen`."
    if frozen_spec(path):
        return (
            "This spec version is approved and frozen. Bump it first: "
            "python3 scripts/spec_tool.py bump <level> --note '...' --root spec/<feature>"
        )
    return None


def main() -> int:
    file_path = json.load(sys.stdin).get("tool_input", {}).get("file_path", "")
    why = reason(file_path) if file_path else None
    if why:
        print(why, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
