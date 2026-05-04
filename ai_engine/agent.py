"""
Markopolo Autonomous AI Test Agent
------------------------------------
No API keys. No manual scripts. No hardcoded selectors.

Pipeline per spec:
  THINK → GENERATE → EXECUTE → REFLECT/FIX → BUG ANALYSIS → GAP DETECT → REPORT
"""

import os
import sys
import json
import ast
import re
import base64
import subprocess
from pathlib import Path
from datetime import datetime

import ollama

# Support both `python ai_engine/agent.py` and `python -m ai_engine.agent`
try:
    from ai_engine.reporter import generate_report
except ImportError:
    from reporter import generate_report

# ── Config ────────────────────────────────────────────────────────────────────
BASE_URL     = os.getenv("BASE_URL",  "https://beta-stg.markopolo.ai")
AI_MODEL     = os.getenv("AI_MODEL",  "qwen2.5-coder:1.5b")
SPECS_DIR    = Path("specs")
TESTS_DIR    = Path("tests")
REPORTS_DIR  = Path("reports")
SHOTS_DIR    = Path("reports/screenshots")
MAX_GEN_RETRIES = 3
MAX_FIX_RETRIES = 2

BUG_COUNTER = [0]   # mutable so nested functions can increment


# ── System prompts ────────────────────────────────────────────────────────────

TEST_GEN_PROMPT = """You are a world-class QA automation engineer. You write Playwright (Python/pytest) tests.

PLAYWRIGHT RULES:
1. Imports: import os, import time, import pytest, from playwright.sync_api import Page, expect
2. BASE_URL = os.getenv("BASE_URL", "https://beta-stg.markopolo.ai")
3. Test functions start with test_
4. Navigation: page.goto(url) then page.wait_for_load_state("networkidle")
5. Selector priority: get_by_role > get_by_label > get_by_placeholder > locator('input[type]')
6. Assertions: expect(locator).to_be_visible(), expect(page).to_have_url(), expect(locator).to_contain_text()
7. Unique emails: f"qa_{int(time.time())}@mailinator.com"
8. Passwords: os.getenv("TEST_PASSWORD", "Test@1234!")
9. Every test must be independent — no shared state

TEST TYPES TO GENERATE:
- Functional (all user flows), Validation (empty/invalid/boundary inputs),
  Edge Cases (XSS, SQLi, special chars, very long inputs),
  Navigation (all links), Error States, Accessibility (labels/aria),
  Responsive (375px mobile viewport via page.set_viewport_size)

OUTPUT: valid Python code only. No markdown fences. No explanation text.
"""

BUG_ANALYST_PROMPT = """You are a senior QA lead writing formal bug tickets for a development team.
Be precise, technical, and actionable. Developers should be able to reproduce and fix with no extra info."""


# ── AI calls ──────────────────────────────────────────────────────────────────

def ai_call(system: str, user: str, max_tokens: int = 2048) -> str:
    try:
        resp = ollama.chat(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            options={"temperature": 0.05, "num_predict": max_tokens},
        )
        return resp["message"]["content"]
    except Exception as e:
        print(f"  [AI] Ollama error: {e}")
        return ""


# ── Code helpers ──────────────────────────────────────────────────────────────

def clean_code(raw: str) -> str:
    raw = raw.strip()
    raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    return raw.strip()


def is_valid_python(code: str) -> tuple[bool, str]:
    try:
        ast.parse(code)
        return True, ""
    except SyntaxError as e:
        return False, f"line {e.lineno}: {e.msg}"


def ensure_imports(code: str) -> str:
    lines = []
    if "import os"              not in code: lines.append("import os")
    if "import time"            not in code: lines.append("import time")
    if "import pytest"          not in code: lines.append("import pytest")
    if "from playwright.sync_api" not in code:
        lines.append("from playwright.sync_api import Page, expect")
    if "BASE_URL" not in code:
        lines.append(f'BASE_URL = os.getenv("BASE_URL", "{BASE_URL}")')
    return ("\n".join(lines) + "\n\n" + code) if lines else code


# ── Test generation ───────────────────────────────────────────────────────────

def generate_tests(spec_path: Path) -> str | None:
    spec = spec_path.read_text()
    page_name = spec_path.stem
    prompt = f"""
Read the specification for "{page_name}" and generate a COMPLETE pytest+Playwright test file.

Cover ALL of the following — do not skip any:
- Every User Flow (numbered steps)
- Every Edge Case (EC-XX rows)
- Every Validation Rule (valid AND invalid inputs)
- All Error States and their messages
- All Navigation links
- Security inputs (XSS, SQLi) from Test Data section
- One mobile viewport test at 375px

SPECIFICATION:
{spec}

Write the complete Python test file now.
"""
    for attempt in range(1, MAX_GEN_RETRIES + 1):
        print(f"    [GENERATE] Attempt {attempt}/{MAX_GEN_RETRIES}...")
        code = clean_code(ai_call(TEST_GEN_PROMPT, prompt))
        if not code:
            continue
        valid, err = is_valid_python(code)
        if valid:
            print(f"    [GENERATE] ✅ {len(code.splitlines())} lines generated")
            return code
        print(f"    [GENERATE] ❌ Syntax error {err}")
        prompt = f"Fix this Python syntax error: {err}\n\nCode:\n{code}\n\nReturn corrected file only."
    return None


def fix_tests(test_code: str, failure_output: str) -> str | None:
    prompt = f"""Fix the failing Playwright tests below.

Common causes:
1. Wrong selector → use role/label/placeholder instead of CSS
2. Element not ready → add expect(locator).to_be_visible(timeout=15000)
3. Wrong URL → verify BASE_URL path
4. Wrong assertion text → match what app actually shows
5. Timing → add wait_for_load_state("networkidle") after navigation

FAILED TEST CODE:
{test_code}

FAILURE OUTPUT:
{failure_output[:3000]}

Return the COMPLETE corrected test file. Python code only.
"""
    for attempt in range(1, MAX_FIX_RETRIES + 1):
        print(f"    [FIX] Attempt {attempt}/{MAX_FIX_RETRIES}...")
        code = clean_code(ai_call(TEST_GEN_PROMPT, prompt))
        valid, err = is_valid_python(code)
        if valid:
            print("    [FIX] ✅ Fixed code generated")
            return code
        print(f"    [FIX] ❌ Syntax error in fix: {err}")
    return None


# ── Test execution ────────────────────────────────────────────────────────────

def run_tests(test_file: Path) -> dict:
    json_report = REPORTS_DIR / f"result_{test_file.stem}.json"
    cmd = [
        sys.executable, "-m", "pytest",
        str(test_file), "-v", "--tb=long", "--no-header",
        "--json-report", f"--json-report-file={json_report}",
        "--timeout=60",
    ]
    env = {**os.environ, "BASE_URL": BASE_URL, "PWDEBUG": "0"}

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=600)
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "total": 0, "passed": 0, "failed": 1,
                "output": "Timed out after 600s", "returncode": -1, "json_report": None}

    output = proc.stdout + "\n" + proc.stderr
    passed = failed = total = 0

    if json_report.exists():
        try:
            s = json.loads(json_report.read_text()).get("summary", {})
            passed = s.get("passed", 0)
            failed = s.get("failed", 0) + s.get("error", 0)
            total  = s.get("total", 0)
        except Exception:
            pass

    if total == 0:
        for line in output.splitlines():
            for num, status in re.findall(r"(\d+) (passed|failed|error)", line):
                if status == "passed":             passed = int(num)
                elif status in ("failed", "error"): failed += int(num)
        total = passed + failed

    return {
        "status": "passed" if proc.returncode == 0 else "failed",
        "total": total, "passed": passed, "failed": failed,
        "output": output,
        "json_report": str(json_report) if json_report.exists() else None,
        "returncode": proc.returncode,
    }


# ── Screenshot helpers ────────────────────────────────────────────────────────

def load_screenshot_index() -> dict:
    idx_file = SHOTS_DIR / "_index.json"
    if idx_file.exists():
        try:
            return json.loads(idx_file.read_text())
        except Exception:
            pass
    return {}


def screenshot_to_b64(path: str) -> str | None:
    try:
        data = Path(path).read_bytes()
        return "data:image/png;base64," + base64.b64encode(data).decode()
    except Exception:
        return None


# ── AI bug analysis ───────────────────────────────────────────────────────────

def ai_analyze_failure(test_name: str, error_msg: str, traceback: str,
                       spec_snippet: str, page_url: str) -> dict:
    prompt = f"""
Write a formal bug ticket for this test failure.

TEST NAME: {test_name}
PAGE URL:  {page_url}
ERROR:     {error_msg}
TRACEBACK (last lines):
{traceback[-1500:]}

RELEVANT SPEC:
{spec_snippet[:1500]}

Use EXACTLY this format (copy the labels verbatim):
SEVERITY: [CRITICAL|HIGH|MEDIUM|LOW]
PRIORITY: [P0|P1|P2|P3]
TITLE: one-line specific title
DESCRIPTION: 2–3 sentence explanation of the bug
STEPS:
1. step one
2. step two
3. step three
EXPECTED: what the spec says should happen
ACTUAL: what actually happened per the error
ROOT_CAUSE: 1–2 sentences on the likely technical cause
SUGGESTED_FIX: specific actionable fix for the developer
"""
    raw = ai_call(BUG_ANALYST_PROMPT, prompt, max_tokens=1024)
    return _parse_bug_analysis(raw, test_name, page_url)


def _parse_bug_analysis(text: str, test_name: str, page_url: str) -> dict:
    def extract(label: str, stop_labels: list[str]) -> str:
        stop = "|".join(re.escape(s) for s in stop_labels)
        m = re.search(
            rf"{label}:\s*(.+?)(?=(?:{stop}):|$)", text,
            re.DOTALL | re.IGNORECASE,
        )
        return m.group(1).strip() if m else ""

    severity = extract("SEVERITY", []).split()[0].upper() if extract("SEVERITY", []) else "MEDIUM"
    if severity not in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
        severity = "MEDIUM"

    priority_raw = extract("PRIORITY", ["TITLE"]).split()[0].upper()
    priority = priority_raw if re.match(r"P[0-3]", priority_raw) else "P2"

    steps_block = re.search(r"STEPS:\n((?:\d+\..+\n?)+)", text, re.MULTILINE)
    steps = re.findall(r"\d+\.\s*(.+)", steps_block.group(1)) if steps_block else [
        f"Navigate to {page_url}",
        "Perform the action described in the test",
        "Observe the result",
    ]

    BUG_COUNTER[0] += 1
    return {
        "id":            f"BUG-{BUG_COUNTER[0]:03d}",
        "test_name":     test_name,
        "severity":      severity,
        "priority":      priority,
        "title":         extract("TITLE",       ["DESCRIPTION"]) or test_name.replace("_", " ").title(),
        "description":   extract("DESCRIPTION", ["STEPS"]),
        "steps":         steps,
        "expected":      extract("EXPECTED",    ["ACTUAL"]),
        "actual":        extract("ACTUAL",      ["ROOT_CAUSE"]),
        "root_cause":    extract("ROOT_CAUSE",  ["SUGGESTED_FIX"]),
        "suggested_fix": extract("SUGGESTED_FIX", []),
        "page_url":      page_url,
    }


# ── Bug ticket builder ────────────────────────────────────────────────────────

def build_bug_tickets(spec_content: str, json_report_path: str | None,
                      screenshot_index: dict) -> list[dict]:
    if not json_report_path or not Path(json_report_path).exists():
        return []

    try:
        report_data = json.loads(Path(json_report_path).read_text())
    except Exception:
        return []

    bugs = []
    for test in report_data.get("tests", []):
        if test.get("outcome") not in ("failed", "error"):
            continue

        node_id   = test.get("nodeid", "")
        test_name = node_id.split("::")[-1]
        call      = test.get("call", {})
        crash     = call.get("crash", {})
        error_msg = crash.get("message", "")
        traceback = call.get("longrepr", "") or "\n".join(
            f"{t.get('path','')}: {t.get('message','')}" for t in call.get("traceback", [])
        )
        page_url  = BASE_URL

        # Find screenshot
        shot_info    = screenshot_index.get(node_id, {})
        shot_path    = shot_info.get("path", "")
        page_url     = shot_info.get("url", BASE_URL) or BASE_URL
        screenshot_b64 = screenshot_to_b64(shot_path) if shot_path else None
        timestamp    = shot_info.get("timestamp", datetime.now().isoformat())

        # AI generates the bug fields
        print(f"    [BUG-AI] Analyzing failure: {test_name}")
        bug = ai_analyze_failure(test_name, error_msg, traceback, spec_content, page_url)

        # Enrich with runtime data
        bug.update({
            "node_id":        node_id,
            "error_message":  error_msg,
            "traceback":      traceback,
            "screenshot_b64": screenshot_b64,
            "screenshot_path": shot_path,
            "duration":       f"{call.get('duration', 0):.2f}s",
            "timestamp":      timestamp,
            "browser":        "Chromium",
            "viewport":       "1280×720",
            "env":            "Staging",
        })
        bugs.append(bug)

    return bugs


# ── Gap detection ─────────────────────────────────────────────────────────────

def detect_gaps(spec_content: str, test_code: str, results: dict) -> str:
    prompt = f"""
Review this test specification and the test code written for it.
Identify EVERY requirement, user flow, edge case, and validation rule that is NOT covered.

For each gap write:
- [MISSING] <what was not tested> — <why it matters> — <how to add it>

SPECIFICATION:
{spec_content[:3000]}

TEST CODE WRITTEN:
{test_code[:2000]}

Stats: {results.get('passed', 0)} passed, {results.get('failed', 0)} failed, {results.get('total', 0)} total.

List every gap. Be specific and actionable.
"""
    return ai_call(BUG_ANALYST_PROMPT, prompt)


# ── Main agent ────────────────────────────────────────────────────────────────

class AutonomousTestAgent:

    def __init__(self):
        self.all_results: dict[str, dict] = {}
        TESTS_DIR.mkdir(exist_ok=True)
        REPORTS_DIR.mkdir(exist_ok=True)

    def run(self):
        self._banner()
        specs = sorted(SPECS_DIR.glob("*.md"))
        if not specs:
            print("[ERROR] No .md spec files in specs/")
            sys.exit(1)

        for spec_path in specs:
            self._process(spec_path)

        self._final_report()

    # ── Per-spec pipeline ─────────────────────────────────────────────────────

    def _process(self, spec_path: Path):
        name = spec_path.stem
        print(f"\n{'━'*62}")
        print(f"  SPEC: {spec_path.name}")
        print(f"{'━'*62}")

        spec_content = spec_path.read_text()
        test_file    = TESTS_DIR / f"test_{name.replace('-', '_')}.py"

        # ── Phase 1: Generate ─────────────────────────────────────────────────
        print("\n  [THINK] AI reading spec and generating tests...")
        code = generate_tests(spec_path)

        if code is None:
            print(f"  [ERROR] Code generation failed for {name}")
            self.all_results[name] = {
                "status": "generation_failed", "total": 0, "passed": 0, "failed": 0,
                "bugs": [], "gaps": "Generation failed — no tests were run.",
            }
            return

        code = ensure_imports(code)
        test_file.write_text(code)
        print(f"  [SAVE]  {test_file}")

        # ── Phase 2: Execute ──────────────────────────────────────────────────
        print("\n  [EXECUTE] Running tests...")
        results = run_tests(test_file)
        self._show(results)

        # ── Phase 3: Fix failures ─────────────────────────────────────────────
        if results["failed"] > 0:
            print(f"\n  [REFLECT] {results['failed']} failure(s) — AI fixing...")
            fixed = fix_tests(code, results["output"])
            if fixed:
                code = ensure_imports(fixed)
                test_file.write_text(code)
                print("  [EXECUTE] Re-running fixed tests...")
                results = run_tests(test_file)
                self._show(results)
                if results["failed"] == 0:
                    print("  [FIX] ✅ All failures resolved!")
                else:
                    print(f"  [FIX] ⚠️  {results['failed']} still failing")

        # ── Phase 4: Build bug tickets ────────────────────────────────────────
        bugs = []
        if results["failed"] > 0:
            print(f"\n  [BUG-ANALYSIS] AI generating bug tickets for {results['failed']} failure(s)...")
            shot_index = load_screenshot_index()
            bugs = build_bug_tickets(spec_content, results.get("json_report"), shot_index)
            print(f"  [BUG-ANALYSIS] {len(bugs)} bug ticket(s) created")

        # ── Phase 5: Coverage gaps ────────────────────────────────────────────
        print("\n  [GAPS] Detecting coverage gaps...")
        gaps = detect_gaps(spec_content, code, results)
        (REPORTS_DIR / f"gaps_{name}.md").write_text(
            f"# Coverage Gaps — {name}\n\nGenerated: {datetime.now().isoformat()}\n\n{gaps}"
        )

        results.update({"bugs": bugs, "gaps": gaps, "spec_name": name})
        self.all_results[name] = results

    # ── Final report ──────────────────────────────────────────────────────────

    def _final_report(self):
        total_p = sum(r.get("passed", 0) for r in self.all_results.values())
        total_f = sum(r.get("failed", 0) for r in self.all_results.values())
        total_t = sum(r.get("total",  0) for r in self.all_results.values())
        all_bugs = [b for r in self.all_results.values() for b in r.get("bugs", [])]

        print("\n" + "═"*62)
        print("  FINAL SUMMARY")
        print("═"*62)
        print(f"  {'Page':<26} {'Pass':>6} {'Fail':>6} {'Total':>6} {'Bugs':>6}")
        print(f"  {'─'*52}")
        for name, r in self.all_results.items():
            icon = "✅" if r.get("failed", 1) == 0 else "❌"
            print(f"  {icon} {name:<24} {r.get('passed',0):>6} "
                  f"{r.get('failed',0):>6} {r.get('total',0):>6} "
                  f"{len(r.get('bugs',[])):>6}")
        print(f"  {'─'*52}")
        print(f"  {'TOTAL':<26} {total_p:>6} {total_f:>6} {total_t:>6} {len(all_bugs):>6}")
        print("═"*62)

        report_path = generate_report(
            all_results=self.all_results,
            base_url=BASE_URL,
            model=AI_MODEL,
        )
        print(f"\n  HTML Report → {report_path}")
        print(f"  Bug Tickets  → {len(all_bugs)} found\n")

        # Write CI summary JSON
        summary = {
            "timestamp": datetime.now().isoformat(),
            "model": AI_MODEL, "base_url": BASE_URL,
            "total_passed": total_p, "total_failed": total_f,
            "total_tests": total_t, "total_bugs": len(all_bugs),
        }
        (REPORTS_DIR / "summary.json").write_text(json.dumps(summary, indent=2))

        if total_f > 0:
            sys.exit(1)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _show(self, r: dict):
        icon = "✅" if r["status"] == "passed" else "❌"
        print(f"  {icon}  Passed: {r['passed']}  Failed: {r['failed']}  Total: {r['total']}")

    def _banner(self):
        print("\n" + "═"*62)
        print("  Markopolo Autonomous AI Test Agent")
        print(f"  Model   : {AI_MODEL}  (local Ollama — no API key)")
        print(f"  Target  : {BASE_URL}")
        print(f"  Specs   : {len(list(SPECS_DIR.glob('*.md')))} files")
        print(f"  Started : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("═"*62)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    agent = AutonomousTestAgent()
    agent.run()
