#!/usr/bin/env python3
"""install.py — one-shot cross-OS setup for Raad Autonomous AI Testing.

Installs everything a cloner needs to run the project from scratch:
  · Python deps  (pip install -r requirements.txt)
  · Playwright Chromium (with Linux system libs)
  · Ollama  (Homebrew on macOS, install.sh on Linux, manual on Windows)
  · A small AI model so the agent has something to call

Usage:
    python install.py            # full install
    python install.py --check    # report what's missing, don't install
    python install.py --big      # also pull qwen2.5-coder:7b (~5GB)

Idempotent — safe to re-run; skips components already in place.
"""

from __future__ import annotations
import os
import platform
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
PY_MIN = (3, 10)

# Default first-run model — small (~1GB), runs on any machine. The 7b model
# gives better generated code but is opt-in via --big.
DEFAULT_MODEL = "qwen2.5-coder:1.5b"
BIG_MODELS = ["qwen2.5-coder:7b"]


def info(msg: str) -> None: print(f"\n→ {msg}")
def ok(msg: str)  -> None: print(f"  ✓ {msg}")
def warn(msg: str) -> None: print(f"  ⚠ {msg}")
def err(msg: str) -> None: print(f"  ✗ {msg}", file=sys.stderr)


# ── Probes ────────────────────────────────────────────────────────────────────

def check_python() -> None:
    if sys.version_info < PY_MIN:
        v = ".".join(str(p) for p in PY_MIN)
        err(f"Python {v}+ required. Current: {sys.version.split()[0]}")
        sys.exit(1)
    ok(f"Python {sys.version.split()[0]}")


def have_python_dep(name: str) -> bool:
    try:
        __import__(name)
        return True
    except ImportError:
        return False


def have_ollama() -> bool:
    return shutil.which("ollama") is not None


def ollama_models() -> list[str]:
    try:
        out = subprocess.check_output(["ollama", "list"], text=True, timeout=10)
        return [line.split()[0] for line in out.strip().splitlines()[1:] if line.strip()]
    except Exception:
        return []


def have_playwright_browser() -> bool:
    """True if any chromium is installed in the Playwright cache."""
    sys_name = platform.system()
    if sys_name == "Darwin":
        cache = Path.home() / "Library/Caches/ms-playwright"
    elif sys_name == "Windows":
        cache = Path.home() / "AppData/Local/ms-playwright"
    else:
        cache = Path.home() / ".cache/ms-playwright"
    if not cache.exists():
        return False
    return any(p.is_dir() and p.name.startswith("chromium") for p in cache.iterdir())


# ── Install steps ─────────────────────────────────────────────────────────────

def run_pip() -> None:
    info("Installing Python dependencies (pip install -r requirements.txt)")
    cmd = [sys.executable, "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")]
    rc = subprocess.run(cmd).returncode
    if rc != 0:
        err("pip install failed — fix the error above and re-run")
        sys.exit(1)
    ok("Python dependencies installed")


def install_playwright() -> None:
    if have_playwright_browser():
        ok("Playwright Chromium already installed")
        return
    info("Installing Playwright Chromium")
    cmd = [sys.executable, "-m", "playwright", "install", "chromium"]
    if platform.system() == "Linux":
        cmd.append("--with-deps")  # apt-get system libs Playwright needs
    rc = subprocess.run(cmd).returncode
    if rc != 0:
        warn("playwright install returned non-zero — browser may still work")
    else:
        ok("Playwright Chromium installed")


def install_ollama() -> None:
    if have_ollama():
        ok(f"Ollama already installed: {shutil.which('ollama')}")
        return
    info("Installing Ollama")
    sys_name = platform.system()
    if sys_name == "Darwin":
        if shutil.which("brew"):
            rc = subprocess.run(["brew", "install", "ollama"]).returncode
            if rc != 0:
                err("brew install ollama failed")
                sys.exit(1)
        else:
            print("  No Homebrew detected. Install manually:")
            print("    https://ollama.com/download/mac")
            print("  Then re-run: python install.py")
            sys.exit(1)
    elif sys_name == "Linux":
        print("  Running official installer (curl https://ollama.com/install.sh | sh)")
        rc = subprocess.run("curl -fsSL https://ollama.com/install.sh | sh",
                             shell=True).returncode
        if rc != 0:
            err("Ollama install script failed — see https://ollama.com/download/linux")
            sys.exit(1)
    elif sys_name == "Windows":
        print("  Windows: download and run the official installer:")
        print("    https://ollama.com/download/windows")
        print("  After install, re-open your terminal and run: python install.py")
        sys.exit(1)
    else:
        err(f"Unsupported OS: {sys_name}")
        sys.exit(1)
    if not have_ollama():
        err("Ollama still not on PATH — open a fresh terminal and re-run install.py")
        sys.exit(1)
    ok("Ollama installed")


def ensure_ollama_serving() -> bool:
    try:
        subprocess.check_output(["ollama", "list"], stderr=subprocess.STDOUT, timeout=8)
        ok("Ollama service is responding")
        return True
    except Exception:
        info("Starting `ollama serve` in background")
        try:
            subprocess.Popen(["ollama", "serve"],
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
        except Exception as e:
            warn(f"Could not auto-start ollama serve ({e}). Run it manually: ollama serve")
            return False
        # Poll for up to 12 s
        for _ in range(12):
            time.sleep(1)
            try:
                subprocess.check_output(["ollama", "list"], timeout=5)
                ok("Ollama service started")
                return True
            except Exception:
                continue
        warn("`ollama serve` didn't respond in 12s — start it manually in another terminal: ollama serve")
        return False


def pull_model(name: str) -> None:
    if any(m == name or m.startswith(name + ":") for m in ollama_models()):
        ok(f"Model already present: {name}")
        return
    info(f"Pulling model: {name} (downloads a few hundred MB to ~5 GB depending on size)")
    rc = subprocess.run(["ollama", "pull", name]).returncode
    if rc != 0:
        warn(f"Failed to pull {name} — agent will use deterministic fallbacks for missing types")
    else:
        ok(f"Pulled {name}")


# ── Modes ─────────────────────────────────────────────────────────────────────

def report_status() -> None:
    """--check mode: print what's missing, don't install anything."""
    print("Status:")
    print(f"  Python      : {sys.version.split()[0]}"
          + (" (OK)" if sys.version_info >= PY_MIN else " — TOO OLD"))
    print(f"  pytest      : {'INSTALLED' if have_python_dep('pytest') else 'missing'}")
    print(f"  playwright  : {'INSTALLED' if have_python_dep('playwright') else 'missing'}")
    print(f"  ollama  pkg : {'INSTALLED' if have_python_dep('ollama') else 'missing'}")
    print(f"  Playwright Chromium : {'INSTALLED' if have_playwright_browser() else 'missing'}")
    print(f"  Ollama binary : {'INSTALLED' if have_ollama() else 'missing'}")
    if have_ollama():
        models = ollama_models()
        print(f"  Ollama models : {len(models)} pulled  {models[:5]}")


def main(argv: list[str]) -> int:
    if "--check" in argv:
        report_status()
        return 0
    print("=" * 64)
    print("Raad Autonomous AI Testing — installer")
    print(f"OS: {platform.system()} {platform.machine()}   Python: {sys.version.split()[0]}")
    print("=" * 64)
    check_python()
    run_pip()
    install_playwright()
    install_ollama()
    ensure_ollama_serving()
    pull_model(DEFAULT_MODEL)
    if "--big" in argv:
        for m in BIG_MODELS:
            pull_model(m)
    print()
    print("=" * 64)
    print("Install complete.  Run the project with:")
    print()
    print("    python run.py            # demo: visible browser, ~3 min")
    print("    python run.py --ai       # AI Test Agent v5 — auto-generates tests")
    print("    python run.py --all      # every QA agent (full suite, ~30 min)")
    print("=" * 64)
    if "--big" not in argv:
        print()
        print(f"Tip: pull a stronger model for better AI-generated tests:")
        for m in BIG_MODELS:
            print(f"    ollama pull {m}     # ~5 GB, slower but smarter")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
