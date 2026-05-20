"""
CI Summary Generator — reads reports and writes detailed GitHub Step Summary.

Shows: AI model used, what each test type tested, test data per test case,
       which tests passed/failed, bug tickets found, coverage gaps.

Usage: python scripts/generate_ci_summary.py
Output: writes to $GITHUB_STEP_SUMMARY (GitHub Actions) or stdout (local)
"""

import json, os, sys, re
from pathlib import Path
from datetime import datetime

REPORTS_DIR = Path("reports")
TESTS_DIR   = Path("tests")


def _icon(passed: bool) -> str:
    return "✅" if passed else "❌"


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_pytest_results(spec_name: str) -> dict:
    """Load per-spec pytest JSON report."""
    p = REPORTS_DIR / f"result_test_{spec_name.replace('-','_')}.json"
    if not p.exists():
        p = REPORTS_DIR / f"result_{spec_name.replace('-','_')}.json"
    return _load_json(p)


def _load_test_names_from_file(spec_name: str) -> list[str]:
    """Extract test function names from generated test file."""
    p = TESTS_DIR / f"test_{spec_name.replace('-','_')}.py"
    if not p.exists():
        return []
    try:
        return re.findall(r"def (test_\w+)", p.read_text(encoding="utf-8"))
    except Exception:
        return []


def _get_test_status(test_name: str, pytest_report: dict) -> str:
    """Look up a test's pass/fail status in pytest JSON report."""
    for test in pytest_report.get("tests", []):
        if test.get("nodeid", "").endswith(f"::{test_name}"):
            outcome = test.get("outcome", "unknown")
            return {"passed": "✅ PASS", "failed": "❌ FAIL", "error": "💥 ERROR",
                    "skipped": "⏭ SKIP"}.get(outcome, f"❓ {outcome.upper()}")
    return "⬜ N/A"


def _failure_message(test_name: str, pytest_report: dict) -> str:
    """Extract failure message for a failed test."""
    for test in pytest_report.get("tests", []):
        if test.get("nodeid", "").endswith(f"::{test_name}"):
            if test.get("outcome") in ("failed", "error"):
                call = test.get("call", {})
                longrepr = call.get("longrepr", "")
                # Take last 2 lines of the traceback
                lines = [l for l in longrepr.splitlines() if l.strip()]
                return " · ".join(lines[-2:])[:200] if lines else ""
    return ""


def generate_summary() -> str:
    summary   = _load_json(REPORTS_DIR / "summary.json")
    data_log  = _load_json(REPORTS_DIR / "test_data_log.json")

    out = []
    W = out.append

    # ── Header ────────────────────────────────────────────────────────────────
    W("## 🤖 Autonomous AI Test Agent")
    W("")

    run_time  = summary.get("timestamp", data_log.get("timestamp", "N/A"))
    model     = summary.get("model",    data_log.get("model_used", "N/A"))
    base_url  = summary.get("base_url", data_log.get("base_url",   "N/A"))
    total_p   = summary.get("total_passed",  0)
    total_f   = summary.get("total_failed",  0)
    total_t   = summary.get("total_tests",   0)
    total_b   = summary.get("total_bugs",    0)
    pass_rate = f"{(total_p/total_t*100):.0f}%" if total_t else "N/A"

    model_chain = summary.get("model_chain", [model])

    W("### Run Overview")
    W("")
    W("| Field | Value |")
    W("|-------|-------|")
    W(f"| 🕐 Run Time | `{run_time}` |")
    W(f"| 🤖 Primary AI Model | `{model}` |")
    W(f"| 🔗 Target URL | `{base_url}` |")
    W(f"| 📊 Tests | `{total_p} passed / {total_f} failed / {total_t} total` |")
    W(f"| 📈 Pass Rate | `{pass_rate}` |")
    W(f"| 🐛 Bug Tickets | `{total_b}` |")
    W(f"| 🏗️ Architecture | `v5 — 22 test types, 14-model chain, compiled specs` |")
    W("")

    # ── Model chain ───────────────────────────────────────────────────────────
    W("### 🔗 AI Model Fallback Chain")
    W("")
    W("*If one model fails, the next is tried automatically. All are free/open-source.*")
    W("")
    W("| # | Model | Size | Purpose |")
    W("|---|-------|------|---------|")
    model_info = [
        ("qwen2.5-coder:7b",    "4.7 GB", "Best code quality"),
        ("qwen2.5-coder:1.5b",  "986 MB", "CI primary (fast download)"),
        ("deepseek-coder:6.7b", "3.8 GB", "Excellent code model"),
        ("codellama:7b",        "3.8 GB", "Meta code model"),
        ("mistral:7b",          "4.1 GB", "Strong general model"),
        ("phi4:3.8b",           "2.3 GB", "Microsoft Phi-4"),
        ("llama3.2:3b",         "2.0 GB", "Meta 3B"),
        ("phi3.5",              "2.2 GB", "Microsoft Phi-3.5"),
        ("gemma2:2b",           "1.6 GB", "Google Gemma2"),
        ("llama3.2:1b",         "1.3 GB", "Meta 1B"),
        ("tinyllama:1.1b",      "637 MB", "Ultra-tiny fallback"),
        ("qwen2.5:0.5b",        "395 MB", "Smallest fallback"),
    ]
    for i, (m, size, purpose) in enumerate(model_info, 1):
        active = " ← **active**" if m == model else ""
        W(f"| {i} | `{m}` | {size} | {purpose}{active} |")
    W("")

    # ── Per-spec results ──────────────────────────────────────────────────────
    specs_data = data_log.get("specs", {})
    specs_tested = summary.get("specs_tested", list(specs_data.keys()))

    if not specs_tested:
        W("*No spec results found.*")
        W("")
    else:
        for spec_name in specs_tested:
            pytest_report = _load_pytest_results(spec_name)
            spec_log      = specs_data.get(spec_name, {})
            types_log     = spec_log.get("types", {})
            total_in_spec = spec_log.get("total_tests", 0)

            s = pytest_report.get("summary", {})
            sp = s.get("passed", 0)
            sf = s.get("failed", 0) + s.get("error", 0)

            W(f"---")
            W(f"### 📄 Spec: `{spec_name}` — {_icon(sf == 0)} {sp} passed / {sf} failed")
            W("")

            # ── Per-type breakdown ─────────────────────────────────────────────
            if types_log:
                W("#### Test Types & Test Data Used")
                W("")

                type_labels = {
                    "smoke":          "🔥 Smoke",
                    "functional":     "⚙️  Functional",
                    "validation":     "✔️  Validation",
                    "negative":       "🚫 Negative",
                    "boundary":       "📐 Boundary",
                    "data_driven":    "📋 Data Driven",
                    "deep_form":      "📝 Deep Form",
                    "api_network":    "🌐 API/Network",
                    "accessibility":  "♿ Accessibility",
                    "responsive":     "📱 Responsive",
                    "navigation":     "🧭 Navigation",
                    "session_auth":   "🔐 Session/Auth",
                    "performance":    "⚡ Performance",
                    "console_errors": "🖥️  Console Errors",
                    "error_states":   "💥 Error States",
                    "visual":         "👁️  Visual",
                    "cross_browser":  "🌍 Cross-Browser",
                    "i18n":           "🌏 i18n",
                    "rate_limiting":  "🚦 Rate Limiting",
                    "cookie_storage": "🍪 Cookie/Storage",
                    "security":       "🔒 Security",
                    "template":       "📋 Template (zero-AI fallback)",
                }

                for type_name, tdata in types_log.items():
                    label = type_labels.get(type_name, f"🧪 {type_name}")
                    tc    = tdata.get("test_count", len(tdata.get("tests", [])))
                    W(f"<details>")
                    W(f"<summary>{label} — {tc} test(s)</summary>")
                    W("")

                    # Test data table
                    data_hints = tdata.get("test_data", [])
                    if data_hints:
                        W("**Test Data Used:**")
                        W("")
                        W("| # | Test Data |")
                        W("|---|-----------|")
                        for j, hint in enumerate(data_hints, 1):
                            W(f"| {j} | `{hint[:120]}` |")
                        W("")

                    # Test function table with status
                    tests = tdata.get("tests", [])
                    if tests and pytest_report:
                        W("**Test Results:**")
                        W("")
                        W("| Status | Test Name | Failure Message |")
                        W("|--------|-----------|-----------------|")
                        for t in tests:
                            status = _get_test_status(t, pytest_report)
                            msg    = _failure_message(t, pytest_report)
                            msg_cell = f"`{msg}`" if msg else "—"
                            W(f"| {status} | `{t}` | {msg_cell} |")
                        W("")

                    W(f"</details>")
                    W("")

            # ── All failing tests quick list ───────────────────────────────────
            failed_tests = [
                t for t in pytest_report.get("tests", [])
                if t.get("outcome") in ("failed", "error")
            ]
            if failed_tests:
                W("#### ❌ Failing Tests")
                W("")
                W("| Test | Error |")
                W("|------|-------|")
                for t in failed_tests:
                    nodeid = t.get("nodeid", "").split("::")[-1]
                    call   = t.get("call", {})
                    longrepr = call.get("longrepr", "")
                    lines  = [l for l in longrepr.splitlines() if l.strip()]
                    short  = " · ".join(lines[-2:])[:200] if lines else "no details"
                    W(f"| `{nodeid}` | `{short}` |")
                W("")

    # ── Bug tickets summary ────────────────────────────────────────────────────
    bug_report = _load_json(REPORTS_DIR / "bug-report.json") if (REPORTS_DIR / "bug-report.json").exists() else {}
    all_bugs = []
    for r in [_load_json(REPORTS_DIR / f"result_test_{s.replace('-','_')}.json")
              for s in specs_tested]:
        all_bugs.extend(r.get("bugs", []))

    if total_b > 0:
        W("---")
        W(f"### 🐛 Bug Tickets Found: {total_b}")
        W("")
        W("*Download the `bug-report-N` artifact for the full HTML report with screenshots.*")
        W("")

    # ── Coverage gaps ─────────────────────────────────────────────────────────
    for spec_name in specs_tested:
        gaps_file = REPORTS_DIR / f"gaps_{spec_name}.txt"
        if gaps_file.exists():
            gaps_text = gaps_file.read_text(encoding="utf-8").strip()
            if gaps_text and "No significant gaps" not in gaps_text:
                W("---")
                W(f"### 🔍 Coverage Gaps: `{spec_name}`")
                W("")
                W("```")
                W(gaps_text[:1500])
                W("```")
                W("")

    # ── Footer ────────────────────────────────────────────────────────────────
    W("---")
    W("")
    W("**Artifacts available for download:**")
    W("- `bug-report-N` — Full HTML report with screenshots and evidence panels")
    W("- `screenshots-N` — Per-failure screenshots")
    W("- `ai-generated-tests-N` — All generated test files")
    W("- `compiled-specs-N` — Compiled spec JSON files")
    W("- `full-reports-N` — All reports including gaps and memory")
    W("")
    W("> *Tests generated by [Autonomous AI Test Agent](https://github.com/rakibsanto/ai-automation-test-template) — change any `.md` spec file and CI re-runs all tests automatically.*")

    return "\n".join(out)


def main():
    summary_text = generate_summary()

    # Always save to ci_summary.md — the workflow reads this and appends to GITHUB_STEP_SUMMARY
    out_path = Path("reports") / "ci_summary.md"
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(summary_text, encoding="utf-8")
    print(f"[CI SUMMARY] Saved to {out_path} ({len(summary_text)} chars)")

    # Local run (no CI env) — print to stdout so user can see it
    if not os.getenv("GITHUB_STEP_SUMMARY") and not os.getenv("CI"):
        print(summary_text)


if __name__ == "__main__":
    main()
