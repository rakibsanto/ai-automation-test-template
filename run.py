#!/usr/bin/env python3
"""run.py — single command to run Mehad Autonomous AI Testing.

Auto-runs install.py the first time if anything is missing.
Always opens a real browser window so you SEE what's happening.

Usage:
    python run.py            # demo: TestQA01Functional with visible browser (~3 min)
    python run.py --ai       # full AI Test Agent v5 — auto-generates from md specs
    python run.py --all      # every QA agent — full suite, ~30 min
    python run.py --headless # same as default but no visible browser
    python run.py --url X    # override BASE_URL (default: dev.prowhats.com/en)
"""

from __future__ import annotations
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.resolve()


def needs_install() -> bool:
    """True when at least one critical dep is missing."""
    try:
        import playwright  # noqa
        import pytest  # noqa
    except ImportError:
        return True
    if shutil.which("ollama") is None:
        return True
    return False


def parse_args(argv: list[str]) -> dict:
    out = {"mode": "demo", "headed": True, "url": None}
    for a in argv:
        if a == "--ai":
            out["mode"] = "ai"
        elif a == "--all":
            out["mode"] = "all"
        elif a == "--headless":
            out["headed"] = False
        elif a.startswith("--url="):
            out["url"] = a.split("=", 1)[1]
        elif a == "--url":
            pass  # next arg
        elif a in ("-h", "--help", "help"):
            print(__doc__)
            sys.exit(0)
    # Handle --url X (space form)
    for i, a in enumerate(argv):
        if a == "--url" and i + 1 < len(argv):
            out["url"] = argv[i + 1]
    return out


def ensure_ollama_serving() -> None:
    """Start ollama serve in background if it isn't already responding."""
    try:
        subprocess.check_output(["ollama", "list"], stderr=subprocess.DEVNULL, timeout=4)
        return
    except Exception:
        pass
    print("→ Starting ollama serve in background...")
    subprocess.Popen(["ollama", "serve"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # Brief wait so the agent's first call doesn't fail
    import time
    for _ in range(10):
        time.sleep(1)
        try:
            subprocess.check_output(["ollama", "list"], timeout=3)
            print("  ✓ ollama serve responding")
            return
        except Exception:
            continue
    print("  ⚠ ollama serve didn't respond in 10s — agent may use fallbacks")


def run_demo(env: dict) -> int:
    """Visible-browser demo: QA-01 Functional. ~45 tests, ~3 min."""
    print("=" * 64)
    print("DEMO MODE — TestQA01Functional with visible browser")
    print(f"Target: {env.get('BASE_URL')}")
    print("=" * 64)
    cmd = [sys.executable, "-m", "pytest",
           "tests/test_qa_comprehensive.py::TestQA01Functional",
           "--browser=chromium",
           "--tb=short", "-v", "--timeout=90",
           "-p", "no:cacheprovider"]
    if env.get("HEADED") == "1":
        cmd.append("--headed")
    return subprocess.call(cmd, env=env)


def run_ai(env: dict) -> int:
    """AI Test Agent v5: auto-generates tests for every spec, runs them.
    The agent itself spawns Playwright; the HEADED env var makes the
    spawned browser visible so you can watch the generated tests run."""
    print("=" * 64)
    print("AI MODE — AI Test Agent v5 (auto-generation + auto-run)")
    print(f"Target: {env.get('BASE_URL')}")
    print(f"Model:  {env.get('AI_MODEL', 'qwen2.5-coder:1.5b')}")
    print("=" * 64)
    cmd = [sys.executable, "-m", "ai_engine.agent"]
    return subprocess.call(cmd, env=env)


def run_all(env: dict) -> int:
    """Every TestQA* class. ~340+ tests, ~30 min."""
    print("=" * 64)
    print("FULL MODE — every QA agent suite")
    print(f"Target: {env.get('BASE_URL')}")
    print("=" * 64)
    cmd = [sys.executable, "-m", "pytest",
           "tests/test_qa_comprehensive.py",
           "--browser=chromium",
           "--tb=short", "-v", "--timeout=90",
           "-p", "no:cacheprovider"]
    if env.get("HEADED") == "1":
        cmd.append("--headed")
    return subprocess.call(cmd, env=env)


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    if needs_install():
        print("First run detected — running installer...\n")
        rc = subprocess.call([sys.executable, str(ROOT / "install.py")])
        if rc != 0:
            return rc
        print()

    ensure_ollama_serving()

    env = os.environ.copy()
    env.setdefault("BASE_URL", args["url"] or "https://dev.prowhats.com/en")
    if args["url"]:
        env["BASE_URL"] = args["url"]
    env["HEADED"] = "1" if args["headed"] else "0"
    # Default to the small first-run model
    env.setdefault("AI_MODEL", "qwen2.5-coder:1.5b")

    if args["mode"] == "ai":
        return run_ai(env)
    if args["mode"] == "all":
        return run_all(env)
    return run_demo(env)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
