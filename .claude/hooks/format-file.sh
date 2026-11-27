#!/bin/sh
# PostToolUse(Edit|Write|MultiEdit): format and lint the file Claude just changed.
# Remaining problems go back to Claude on stderr with exit 2 so it fixes them.
input=$(cat)
file=$(printf '%s' "$input" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))')
[ -f "$file" ] || exit 0
cd "$(dirname "$0")/../.." || exit 0
case "$file" in
  */apps/web/src/gen/*) exit 0 ;;
  *.py)
    uv run --quiet ruff format --quiet "$file" >/dev/null 2>&1
    out=$(uv run --quiet ruff check --fix --quiet "$file" 2>&1) || { printf 'ruff found problems in %s:\n%s\n' "$file" "$out" >&2; exit 2; }
    ;;
  *.ts|*.tsx|*.css|*.json)
    pnpm exec prettier --config .prettierrc.json --log-level warn --write "$file" >/dev/null 2>&1
    case "$file" in
      *.ts|*.tsx)
        out=$(cd apps/web && pnpm exec oxlint --deny-warnings -A react/only-export-components "$file" 2>&1) || { printf 'oxlint found problems in %s:\n%s\n' "$file" "$out" >&2; exit 2; }
        ;;
    esac
    ;;
esac
exit 0
