"""Tests for the Claude Code hooks in .claude/hooks (M0 AC-14, AC-18; MVP AC-20)."""

import json
import subprocess
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HOOKS = ROOT / ".claude" / "hooks"


def run(hook: str, payload: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(HOOKS / hook)], input=json.dumps(payload), capture_output=True, text=True, cwd=ROOT
    )


@pytest.mark.parametrize(
    "command",
    [
        "git push --force origin main",
        "git push -f origin main",
        "git push origin main --force-with-lease",
        "git commit --no-verify -m wip",
        "echo KEY=1 > .env",
        "echo KEY=1 >> .env.local",
        "printf x | tee .env",
    ],
)
def test_guard_bash_blocks(command):
    result = run("guard-bash.py", {"tool_input": {"command": command}})
    assert result.returncode == 2, command
    assert result.stderr


@pytest.mark.parametrize(
    "command",
    [
        "git push -u origin mvp/1-foundation",
        "git push --force origin feature/x",
        "echo KEY= >> .env.example",
        "make check",
    ],
)
def test_guard_bash_allows(command):
    assert run("guard-bash.py", {"tool_input": {"command": command}}).returncode == 0


@pytest.mark.parametrize(
    "path",
    [
        ".env",
        ".env.production",
        "uv.lock",
        "pnpm-lock.yaml",
        "apps/web/src/gen/agent-spec.ts",
        "packages/core/schema/agent-spec.schema.json",
    ],
)
def test_guard_files_blocks(path):
    result = run("guard-files.py", {"tool_input": {"file_path": str(ROOT / path)}})
    assert result.returncode == 2, path


def test_guard_files_blocks_frozen_spec(tmp_path, monkeypatch):
    frozen = ROOT / "spec" / "zz-hooktest" / "1.0.0"
    frozen.mkdir(parents=True)
    try:
        (frozen / "spec.md").write_text("---\nstatus: approved\n---\n")
        result = run("guard-files.py", {"tool_input": {"file_path": str(frozen / "plan.md")}})
        assert result.returncode == 2
        (frozen / "spec.md").write_text("---\nstatus: draft\n---\n")
        result = run("guard-files.py", {"tool_input": {"file_path": str(frozen / "plan.md")}})
        assert result.returncode == 0
    finally:
        for f in frozen.iterdir():
            f.unlink()
        frozen.rmdir()
        frozen.parent.rmdir()


@pytest.mark.parametrize("path", [".env.example", "services/api/src/ovas_api/main.py", "README.md"])
def test_guard_files_allows(path):
    assert run("guard-files.py", {"tool_input": {"file_path": str(ROOT / path)}}).returncode == 0


def test_format_hook_formats_python_quickly(tmp_path):
    target = ROOT / "packages" / "core" / "src" / "ovas_core" / "_hooktest.py"
    target.write_text("x=( 1,\n2 )\n")
    try:
        start = time.monotonic()
        result = run("format-file.sh", {"tool_input": {"file_path": str(target)}})
        elapsed = time.monotonic() - start
        assert result.returncode == 0, result.stderr
        assert target.read_text() == "x = (1, 2)\n"
        assert elapsed < 3, f"format hook took {elapsed:.1f}s"
    finally:
        target.unlink()


def test_format_hook_reports_lint_errors():
    target = ROOT / "packages" / "core" / "src" / "ovas_core" / "_hooktest_bad.py"
    target.write_text("def f():\n    return undefined_name\n")
    try:
        result = run("format-file.sh", {"tool_input": {"file_path": str(target)}})
        assert result.returncode == 2
        assert "undefined_name" in result.stderr
    finally:
        target.unlink()
