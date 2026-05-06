"""
Standalone HTML report generator — runs with `if: always()` in CI.

Reads whatever partial data exists in reports/ and always produces a
bug-report.html, even when the agent step was cancelled or timed out.
"""
from __future__ import annotations
import json, sys, re
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

REPORTS_DIR = ROOT / "reports"
TESTS_DIR   = ROOT / "tests"


def _load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_pytest_result(spec_name: str) -> dict:
    """Try both naming conventions for the per-spec pytest JSON report."""
    for stem in (f"result_test_{spec_name.replace('-','_')}",
                 f"result_{spec_name.replace('-','_')}"):
        p = REPORTS_DIR / f"{stem}.json"
        if p.exists():
            return _load(p), str(p)
    return {}, ""


def _parse_gaps(spec_name: str) -> str:
    p = REPORTS_DIR / f"gaps_{spec_name}.txt"
    return p.read_text(encoding="utf-8").strip() if p.exists() else ""


def build_all_results(summary: dict, data_log: dict) -> dict:
    """
    Reconstruct the all_results dict that generate_report() expects,
    using whatever JSON files survived the (possibly cancelled) run.
    """
    specs_tested = summary.get("specs_tested", list(data_log.get("specs", {}).keys()))

    # If nothing at all — make one placeholder entry so report isn't blank
    if not specs_tested:
        return {
            "no_data": {
                "status":  "generation_failed",
                "passed":  0, "failed": 0, "total": 0,
                "bugs":    [],
                "gaps":    "Job may have been cancelled before any specs completed.",
                "partial": True,
            }
        }

    all_results: dict = {}
    for spec_name in specs_tested:
        pytest_data, report_path = _load_pytest_result(spec_name)
        s = pytest_data.get("summary", {})
        passed = s.get("passed", 0)
        failed = s.get("failed", 0) + s.get("error", 0)
        total  = s.get("total", 0)

        # Reconstruct basic bug stubs from the pytest failed tests
        bugs = []
        for t in pytest_data.get("tests", []):
            if t.get("outcome") not in ("failed", "error"):
                continue
            nodeid   = t.get("nodeid", "")
            fn_name  = nodeid.split("::")[-1].split("[")[0]
            call     = t.get("call", {})
            longrepr = call.get("longrepr", "")
            lines    = [l for l in longrepr.splitlines() if l.strip()]
            short    = "\n".join(lines[-5:]) if lines else "No details"
            bugs.append({
                "id":            f"BUG-{spec_name[:3].upper()}-{len(bugs)+1:03d}",
                "severity":      "MEDIUM",
                "priority":      "P2",
                "title":         f"Test failed: {fn_name}",
                "test_name":     fn_name,
                "page_url":      summary.get("base_url", ""),
                "description":   f"Playwright test `{fn_name}` failed during CI run.",
                "expected":      "Test should pass without errors",
                "actual":        lines[-1][:300] if lines else "Assertion failed",
                "error_message": short[:500],
                "traceback":     longrepr[:2000],
                "timestamp":     datetime.now().isoformat(),
                "steps":         [],
                "screenshot_b64": "",
                "browser":       "Chromium",
                "viewport":      "1280x720",
                "env":           "Staging",
            })

        all_results[spec_name] = {
            "status":      "passed" if failed == 0 and total > 0 else "failed",
            "passed":      passed,
            "failed":      failed,
            "total":       total,
            "bugs":        bugs,
            "gaps":        _parse_gaps(spec_name),
            "json_report": report_path or None,
        }

    return all_results


def main():
    REPORTS_DIR.mkdir(exist_ok=True)

    summary  = _load(REPORTS_DIR / "summary.json")
    data_log = _load(REPORTS_DIR / "test_data_log.json")

    model    = summary.get("model",    data_log.get("model_used", "unknown"))
    base_url = summary.get("base_url", data_log.get("base_url",  "https://beta-stg.fagun.ai"))
    partial  = summary.get("partial",  False)

    all_results = build_all_results(summary, data_log)

    print(f"[HTML REPORT] Specs: {list(all_results.keys())}")
    for name, r in all_results.items():
        print(f"  {name}: {r['passed']} passed / {r['failed']} failed / {r['total']} total")

    from ai_engine.reporter import generate_report
    out = generate_report(all_results, base_url, model)

    # Stamp the report as partial when agent was cancelled mid-run
    if partial:
        html = out.read_text(encoding="utf-8")
        banner = """
<div style="background:#3d2000;border:2px solid #f0883e;border-radius:8px;
            padding:14px 20px;margin:0 0 24px;color:#f0883e;font-size:14px;font-weight:600">
  ⚠️ Partial run — CI agent was cancelled or timed out before all specs completed.
  Results shown are from specs that finished. Download artifacts for raw data.
</div>"""
        html = html.replace('<div class="wrap">', f'<div class="wrap">{banner}', 1)
        out.write_text(html, encoding="utf-8")

    print(f"✅ HTML report → {out}  ({'PARTIAL' if partial else 'COMPLETE'})")


if __name__ == "__main__":
    main()
