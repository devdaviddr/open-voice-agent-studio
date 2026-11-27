#!/usr/bin/env python3
"""PreToolUse(Bash): block commands that bypass review or leak secrets. Exit 2 = blocked."""

import json
import re
import sys

RULES = [
    (
        r"\bgit\s+push\b.*(\s--force\b|\s-f\b|\s--force-with-lease\b).*\b(main|master)\b"
        r"|\bgit\s+push\b.*\b(main|master)\b.*(\s--force\b|\s-f\b|\s--force-with-lease\b)",
        "Force-pushing main is blocked. Push a branch and open a pull request.",
    ),
    (
        r"\bgit\s+(commit|push)\b.*--no-verify",
        "--no-verify skips the project's checks. Fix the failing check instead.",
    ),
    (
        r"(>>?|\btee\b(\s+-a)?)\s*\S*\.env(\.[\w-]+)?(?=[\s;&|)]|$)(?<!\.example)",
        "Writing .env files from the shell is blocked; they hold secrets. Edit .env.example "
        "for documentation, and ask the user to set real values.",
    ),
]


def main() -> int:
    command = json.load(sys.stdin).get("tool_input", {}).get("command", "")
    for pattern, message in RULES:
        if re.search(pattern, command):
            print(message, file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
