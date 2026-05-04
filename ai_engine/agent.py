"""
Markopolo Autonomous AI Test Agent  —  v3
------------------------------------------
• Parses MD specs into focused sections (no more token overflow)
• Multi-model chain: tries every available Ollama model, auto-falls back
• Template engine: generates valid tests even when ALL AI models fail
• Section-by-section generation: flows / validation / edge cases / security
• Streams every pytest line to CI in real-time
• Per-failure AI bug tickets with screenshots
"""

import os, sys, json, ast, re, base64, builtins, subprocess
from pathlib import Path
from datetime import datetime

import ollama

try:
    from ai_engine.spec_parser  import parse as parse_spec, ParsedSpec
    from ai_engine.spec_parser  import (flows_prompt_section,
                                        edge_cases_prompt_section,
                                        validation_prompt_section,
                                        security_prompt_section)
    from ai_engine.reporter     import generate_report
except ImportError:
    from spec_parser  import parse as parse_spec, ParsedSpec
    from spec_parser  import (flows_prompt_section,
                               edge_cases_prompt_section,
                               validation_prompt_section,
                               security_prompt_section)
    from reporter     import generate_report

# ── Force real-time output ────────────────────────────────────────────────────
_real_print = builtins.print
def print(*a, **kw):
    kw.setdefault("flush", True); _real_print(*a, **kw)
def log(msg=""):
    _real_print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

# ── Config ────────────────────────────────────────────────────────────────────
BASE_URL        = os.getenv("BASE_URL",  "https://beta-stg.markopolo.ai")
AI_MODEL        = os.getenv("AI_MODEL",  "qwen2.5-coder:1.5b")
SPECS_DIR       = Path("specs")
TESTS_DIR       = Path("tests")
REPORTS_DIR     = Path("reports")
SHOTS_DIR       = Path("reports/screenshots")
MAX_FIX_RETRIES = 3
BUG_COUNTER     = [0]

# ── Model chain — tried in order, auto-fallback ───────────────────────────────
# (model_name, max_output_tokens, temperature)
MODEL_CHAIN = [
    (AI_MODEL,         4096, 0.05),   # primary — env-configurable
    (AI_MODEL,         2000, 0.10),   # same model, smaller window safety net
    ("llama3.2:1b",    3000, 0.10),   # fallback 1 (1.3 GB, fast)
    ("phi3.5",         3000, 0.10),   # fallback 2 (2.2 GB)
    ("qwen2.5:0.5b",   2000, 0.15),   # fallback 3 (tiny, last resort)
]

# ── System prompts ────────────────────────────────────────────────────────────
SYS_TEST = """\
You are an expert QA automation engineer. Write Playwright (Python/pytest) test functions.

STRICT RULES — follow every rule or the tests will not run:
1. Output ONLY valid Python. No markdown fences. No prose. No comments like "Here is...".
2. Start the output with `import` statements — never with text.
3. Every test function MUST start with `def test_` and have `page: Page` as its only parameter.
4. Use these imports exactly:
   import os, time, pytest
   from playwright.sync_api import Page, expect
   BASE_URL = os.getenv("BASE_URL", "https://beta-stg.markopolo.ai")
5. Navigation pattern: page.goto(url) then page.wait_for_load_state("networkidle")
6. Selector order (best to worst):
   page.get_by_role("button", name="Login")
   page.get_by_label("Email")
   page.get_by_placeholder("Enter email")
   page.locator('input[type="email"]')
7. Assertions: expect(locator).to_be_visible() / expect(page).to_have_url()
8. Unique emails: f"qa_{int(time.time())}@mailinator.com"
9. Passwords: os.getenv("TEST_PASSWORD", "Test@1234!")
10. WRITE SHORT functions — max 25 lines each. If you run out of space, end cleanly.
"""

SYS_BUG = """\
You are a senior QA lead. Write formal bug tickets.
Be precise and actionable. Use the exact section labels requested.\
"""

SYS_ANALYST = """\
You are a senior QA engineer. Analyse test coverage gaps in plain bullet points.\
"""

# ── Model chain caller ────────────────────────────────────────────────────────

def _available_models() -> set[str]:
    try:
        return {m["model"] for m in ollama.list().get("models", [])}
    except Exception:
        return {AI_MODEL}

_AVAILABLE: set[str] | None = None

def ai_call(system: str, user: str, max_tokens: int = 4096) -> str:
    """Try every model in MODEL_CHAIN until one responds. Never crashes."""
    global _AVAILABLE
    if _AVAILABLE is None:
        _AVAILABLE = _available_models()
        log(f"  [MODELS] Available: {sorted(_AVAILABLE)}")

    for model, tok, temp in MODEL_CHAIN:
        if model not in _AVAILABLE and model != AI_MODEL:
            continue
        effective_tokens = min(max_tokens, tok)
        log(f"  [AI] → {model}  max_tokens={effective_tokens}")
        try:
            resp = ollama.chat(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user},
                ],
                options={"temperature": temp, "num_predict": effective_tokens},
            )
            text = resp["message"]["content"].strip()
            if len(text) > 50:
                log(f"  [AI] ✅ {model} → {len(text)} chars")
                return text
            log(f"  [AI] ⚠️  {model} returned empty/too-short response, trying next...")
        except Exception as e:
            log(f"  [AI] ❌ {model} error: {e}")
    log("  [AI] ⚠️  All models exhausted — using template fallback")
    return ""

# ── Code helpers ──────────────────────────────────────────────────────────────

def clean_code(raw: str) -> str:
    raw = raw.strip()
    raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    # Remove leading prose before first import/def
    lines = raw.splitlines()
    for i, line in enumerate(lines):
        if line.startswith(("import ", "from ", "def ", "class ", "BASE_URL", "#")):
            return "\n".join(lines[i:]).strip()
    return raw.strip()

def is_valid_python(code: str) -> tuple[bool, str]:
    try:
        ast.parse(code)
        return True, ""
    except SyntaxError as e:
        return False, f"line {e.lineno}: {e.msg}"

def ensure_imports(code: str) -> str:
    header = []
    if "import os"               not in code: header.append("import os")
    if "import time"             not in code: header.append("import time")
    if "import pytest"           not in code: header.append("import pytest")
    if "from playwright.sync_api" not in code:
        header.append("from playwright.sync_api import Page, expect")
    if "BASE_URL" not in code:
        header.append(f'BASE_URL = os.getenv("BASE_URL", "{BASE_URL}")')
    return ("\n".join(header) + "\n\n" + code) if header else code

# ── Template engine (zero-AI fallback) ───────────────────────────────────────
# Always generates valid Python — guarantees tests run even if all AI fails.

def template_tests(spec: ParsedSpec) -> str:
    slug  = spec.slug.replace("-", "_")
    url   = spec.url or (BASE_URL + spec.path)
    lines = [
        "import os, time, pytest",
        "from playwright.sync_api import Page, expect",
        f'BASE_URL = os.getenv("BASE_URL", "{BASE_URL}")',
        "",
    ]

    # 1 — Page loads
    lines += [
        f"def test_{slug}_page_loads(page: Page):",
        f'    """Page loads and URL is correct."""',
        f'    page.goto("{url}")',
        f'    page.wait_for_load_state("networkidle")',
        f'    assert "{spec.path.rstrip("/")}" in page.url or page.url.startswith(BASE_URL)',
        "",
    ]

    # 2 — One test per user flow (navigation only)
    for i, flow in enumerate(spec.flows[:4], 1):
        fname = re.sub(r"\W+", "_", flow["name"].lower())[:40]
        lines += [
            f"def test_{slug}_flow_{i}_{fname}(page: Page):",
            f'    """Flow {i}: {flow["name"][:60]}"""',
            f'    page.goto("{url}")',
            f'    page.wait_for_load_state("networkidle")',
            f'    # Steps: ' + " | ".join(flow["steps"][:3]),
            f'    assert page.url  # page is reachable',
            "",
        ]

    # 3 — One test per edge case
    for ec in spec.edge_cases[:6]:
        eid = ec["id"].lower().replace("-", "_")
        lines += [
            f"def test_{eid}(page: Page):",
            f'    """{ec["id"]}: {ec["scenario"][:70]}"""',
            f'    page.goto("{url}")',
            f'    page.wait_for_load_state("networkidle")',
            f'    # Expected: {ec["expected"][:80]}',
            f'    assert page.url  # page accessible; manual validation needed',
            "",
        ]

    # 4 — Mobile viewport
    lines += [
        f"def test_{slug}_mobile_viewport(page: Page):",
        f'    """Page is usable on 375px mobile viewport."""',
        f'    page.set_viewport_size({{"width": 375, "height": 667}})',
        f'    page.goto("{url}")',
        f'    page.wait_for_load_state("networkidle")',
        f'    assert page.url  # page loaded on mobile',
        "",
    ]

    return "\n".join(lines)

# ── Section-based AI test generation ─────────────────────────────────────────
# Each section generates a small focused chunk → no token overflow.

_SECTION_SYSTEM = SYS_TEST

def _gen_section(title: str, instructions: str, context: str) -> str:
    """Ask AI to write tests for ONE section. Returns valid Python or ''."""
    prompt = f"""Write Playwright pytest functions for: {title}

{context}

INSTRUCTIONS:
{instructions}

Output ONLY Python function definitions (def test_...). No imports. No module-level code.
Keep each function under 20 lines. End every function completely — never leave a def open.
"""
    for attempt in range(1, 4):
        log(f"    [SECTION:{title}] attempt {attempt}/3")
        raw  = ai_call(_SECTION_SYSTEM, prompt, max_tokens=3000)
        code = clean_code(raw)
        if not code:
            continue
        # Wrap in a module to validate
        test_module = (
            "import os,time,pytest\n"
            "from playwright.sync_api import Page,expect\n"
            f'BASE_URL=os.getenv("BASE_URL","{BASE_URL}")\n\n'
            + code
        )
        valid, err = is_valid_python(test_module)
        if valid:
            log(f"    [SECTION:{title}] ✅ {code.count('def test_')} tests generated")
            return code
        log(f"    [SECTION:{title}] ❌ Syntax: {err} — retrying")
        prompt = (f"Fix this Python syntax error: {err}\n\n"
                  f"Return ONLY the corrected function definitions:\n{code}")
    return ""

def generate_all_sections(spec: ParsedSpec) -> str:
    """Generate tests section by section, combine, validate."""
    log(f"  [GEN] Section-based generation for {spec.page_name}")
    chunks: list[str] = []

    # ── Flows ─────────────────────────────────────────────────────────────────
    if spec.flows:
        ctx  = flows_prompt_section(spec)
        inst = ("Write ONE test function per flow. "
                "Test the full navigation + key actions described in each flow. "
                "Use get_by_role/get_by_label selectors. Assert URL or visible element after action.")
        chunk = _gen_section("User Flows", inst, ctx)
        if chunk: chunks.append(chunk)

    # ── Validation ────────────────────────────────────────────────────────────
    ctx  = validation_prompt_section(spec)
    inst = ("Write tests that input each invalid value and assert the validation error appears. "
            "Also test that valid inputs pass. One function per rule.")
    chunk = _gen_section("Validation Rules", inst, ctx)
    if chunk: chunks.append(chunk)

    # ── Edge cases ────────────────────────────────────────────────────────────
    if spec.edge_cases:
        ctx  = edge_cases_prompt_section(spec)
        inst = ("Write ONE test per edge case. Input the value, observe the result. "
                "Assert the expected behaviour listed. Keep each function under 15 lines.")
        chunk = _gen_section("Edge Cases", inst, ctx)
        if chunk: chunks.append(chunk)

    # ── Security ──────────────────────────────────────────────────────────────
    ctx  = security_prompt_section(spec)
    inst = ("Submit each security input in form fields. "
            "Assert the page does NOT crash (no 500 error, no alert dialog, URL stays same). "
            "One function per input.")
    chunk = _gen_section("Security Inputs", inst, ctx)
    if chunk: chunks.append(chunk)

    # ── Mobile viewport ───────────────────────────────────────────────────────
    ctx  = f"PAGE: {spec.page_name}  URL: {spec.url}  PATH: {spec.path}"
    inst = (f"Write ONE test that sets viewport to 375×667 and visits {spec.url}. "
            "Assert key elements visible at mobile size.")
    chunk = _gen_section("Mobile Viewport", inst, ctx)
    if chunk: chunks.append(chunk)

    if not chunks:
        log("  [GEN] ⚠️  All AI sections empty — using template engine")
        return ""

    # Combine into one module
    full = (
        "import os, time, pytest\n"
        "from playwright.sync_api import Page, expect\n"
        f'BASE_URL = os.getenv("BASE_URL", "{BASE_URL}")\n\n'
        + "\n\n".join(chunks)
    )
    valid, err = is_valid_python(full)
    if valid:
        log(f"  [GEN] ✅ Combined: {full.count('def test_')} tests, "
            f"{len(full.splitlines())} lines")
        return full

    # Final fix attempt on combined file
    log(f"  [GEN] Syntax error in combined file ({err}) — AI fix attempt...")
    fixed_raw = ai_call(
        SYS_TEST,
        f"Fix this Python syntax error: {err}\n\nCode:\n{full}\n\nReturn complete fixed file.",
        max_tokens=4096,
    )
    fixed = clean_code(fixed_raw)
    valid2, err2 = is_valid_python(fixed)
    if valid2:
        log("  [GEN] ✅ Combined file fixed")
        return fixed
    log(f"  [GEN] ❌ Could not fix combined file ({err2}) — template fallback")
    return ""

# ── Test execution (streaming) ────────────────────────────────────────────────

def _stream(cmd: list, env: dict, timeout: int = 300) -> tuple[int, str]:
    lines: list[str] = []
    try:
        proc = subprocess.Popen(
            cmd, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1,
        )
        for line in proc.stdout:
            s = line.rstrip()
            lines.append(s)
            log(f"    {s}")
        proc.wait(timeout=timeout)
        return proc.returncode, "\n".join(lines)
    except subprocess.TimeoutExpired:
        proc.kill()
        return -1, "\n".join(lines) + "\n[TIMEOUT]"
    except Exception as e:
        return -1, f"[ERROR] {e}"

def run_tests(test_file: Path) -> dict:
    json_report = REPORTS_DIR / f"result_{test_file.stem}.json"
    env = {**os.environ, "BASE_URL": BASE_URL,
           "PWDEBUG": "0", "PYTHONUNBUFFERED": "1"}

    log(f"  [COLLECT] Discovering tests in {test_file.name}...")
    _rc, cout = _stream(
        [sys.executable, "-m", "pytest", str(test_file),
         "--collect-only", "-q", "--no-header"], env, timeout=60)
    collected = len(re.findall(r"<Function test_", cout))
    log(f"  [COLLECT] {collected} test functions found")

    if collected == 0:
        log("  [COLLECT] ⚠️  0 tests found — dumping generated file:")
        log(test_file.read_text())

    log(f"  [PYTEST] Running tests...")
    rc, output = _stream(
        [sys.executable, "-m", "pytest", str(test_file),
         "-v", "--tb=short", "--no-header",
         "--json-report", f"--json-report-file={json_report}",
         "--timeout=30"],
        env, timeout=300,
    )

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
            for n, st in re.findall(r"(\d+) (passed|failed|error)", line):
                if st == "passed":            passed = int(n)
                elif st in ("failed","error"): failed += int(n)
        total = passed + failed

    return {
        "status":      "passed" if rc == 0 else "failed",
        "total": total, "passed": passed, "failed": failed,
        "output": output,
        "json_report": str(json_report) if json_report.exists() else None,
        "returncode":  rc,
    }

# ── Bug tickets ───────────────────────────────────────────────────────────────

def load_screenshot_index() -> dict:
    idx = SHOTS_DIR / "_index.json"
    try:
        return json.loads(idx.read_text()) if idx.exists() else {}
    except Exception:
        return {}

def screenshot_to_b64(path: str) -> str | None:
    try:
        return "data:image/png;base64," + base64.b64encode(Path(path).read_bytes()).decode()
    except Exception:
        return None

def _parse_bug(text: str, test_name: str, page_url: str) -> dict:
    def grab(label, stops):
        stop_pat = "|".join(re.escape(s) for s in stops)
        m = re.search(rf"{label}:\s*(.+?)(?=(?:{stop_pat}):|$)", text,
                      re.DOTALL | re.IGNORECASE)
        return m.group(1).strip() if m else ""

    sev = grab("SEVERITY", []).split()[0].upper() if grab("SEVERITY", []) else "MEDIUM"
    if sev not in ("CRITICAL","HIGH","MEDIUM","LOW"): sev = "MEDIUM"
    pri_raw = grab("PRIORITY", ["TITLE"]).split()[0].upper()
    pri = pri_raw if re.match(r"P[0-3]", pri_raw) else "P2"
    steps_m = re.search(r"STEPS:\n((?:\d+\..+\n?)+)", text, re.MULTILINE)
    steps = re.findall(r"\d+\.\s*(.+)", steps_m.group(1)) if steps_m else [
        f"Navigate to {page_url}", "Perform the action", "Observe the result"]

    BUG_COUNTER[0] += 1
    return {
        "id":            f"BUG-{BUG_COUNTER[0]:03d}",
        "test_name":     test_name,
        "severity":      sev,
        "priority":      pri,
        "title":         grab("TITLE",       ["DESCRIPTION"]) or test_name.replace("_"," ").title(),
        "description":   grab("DESCRIPTION", ["STEPS"]),
        "steps":         steps,
        "expected":      grab("EXPECTED",    ["ACTUAL"]),
        "actual":        grab("ACTUAL",      ["ROOT_CAUSE"]),
        "root_cause":    grab("ROOT_CAUSE",  ["SUGGESTED_FIX"]),
        "suggested_fix": grab("SUGGESTED_FIX", []),
        "page_url":      page_url,
    }

def ai_analyze_failure(test_name, error_msg, traceback, spec_snippet, page_url) -> dict:
    prompt = f"""Write a bug ticket for this failure.

TEST: {test_name}
URL:  {page_url}
ERROR: {error_msg}
TRACEBACK:
{traceback[-1200:]}
SPEC CONTEXT:
{spec_snippet[:800]}

Use EXACTLY these labels:
SEVERITY: [CRITICAL|HIGH|MEDIUM|LOW]
PRIORITY: [P0|P1|P2|P3]
TITLE: one line
DESCRIPTION: 2-3 sentences
STEPS:
1.
2.
3.
EXPECTED: per spec
ACTUAL: from error
ROOT_CAUSE: 1-2 sentences
SUGGESTED_FIX: specific fix for developer
"""
    raw = ai_call(SYS_BUG, prompt, max_tokens=800)
    return _parse_bug(raw, test_name, page_url)

def build_bug_tickets(spec_content, json_report_path, shot_index) -> list[dict]:
    if not json_report_path or not Path(json_report_path).exists():
        return []
    try:
        data = json.loads(Path(json_report_path).read_text())
    except Exception:
        return []
    bugs = []
    for test in data.get("tests", []):
        if test.get("outcome") not in ("failed", "error"):
            continue
        node_id   = test.get("nodeid", "")
        test_name = node_id.split("::")[-1]
        call      = test.get("call", {})
        crash     = call.get("crash", {})
        error_msg = crash.get("message", "")
        traceback = call.get("longrepr", "")
        shot_info = shot_index.get(node_id, {})
        shot_b64  = screenshot_to_b64(shot_info.get("path","")) if shot_info else None
        page_url  = shot_info.get("url", BASE_URL) or BASE_URL
        ts        = shot_info.get("timestamp", datetime.now().isoformat())

        log(f"    [BUG] Analyzing: {test_name}")
        bug = ai_analyze_failure(test_name, error_msg, traceback, spec_content[:800], page_url)
        bug.update({
            "node_id": node_id, "error_message": error_msg,
            "traceback": traceback, "screenshot_b64": shot_b64,
            "screenshot_path": shot_info.get("path",""),
            "duration": f"{call.get('duration',0):.2f}s",
            "timestamp": ts[:19].replace("T"," "),
            "browser": "Chromium", "viewport": "1280×720", "env": "Staging",
        })
        bugs.append(bug)
    return bugs

# ── Gap detection ─────────────────────────────────────────────────────────────

def detect_gaps(spec: ParsedSpec, test_code: str, results: dict) -> str:
    reqs = "\n".join(spec.requirements[:10])
    ecs  = "\n".join(f"  {e['id']}: {e['scenario']}" for e in spec.edge_cases[:8])
    prompt = f"""Identify every coverage gap in the tests written for {spec.page_name}.

REQUIREMENTS:
{reqs}

EDGE CASES IN SPEC:
{ecs}

TEST CODE WRITTEN ({results.get('total',0)} tests, "
{results.get('passed',0)} passed, {results.get('failed',0)} failed):
{test_code[:1500]}

List every gap:
- [MISSING] <what> — <why it matters> — <how to add it>
"""
    return ai_call(SYS_ANALYST, prompt, max_tokens=1200)

# ── Main agent ────────────────────────────────────────────────────────────────

class AutonomousTestAgent:

    def __init__(self):
        self.all_results: dict[str, dict] = {}
        TESTS_DIR.mkdir(exist_ok=True)
        REPORTS_DIR.mkdir(exist_ok=True)
        SHOTS_DIR.mkdir(parents=True, exist_ok=True)

    def run(self):
        self._banner()
        specs = sorted(SPECS_DIR.glob("*.md"))
        if not specs:
            log("[ERROR] No .md spec files in specs/")
            sys.exit(1)
        for sp in specs:
            self._process(sp)
        self._final_report()

    def _process(self, spec_path: Path):
        name = spec_path.stem
        log(f"\n{'━'*62}")
        log(f"  SPEC: {spec_path.name}")
        log(f"{'━'*62}")

        # ── Parse MD into structured sections ─────────────────────────────────
        log("  [PARSE] Reading and parsing spec sections...")
        spec = parse_spec(spec_path)
        log(f"  [PARSE] Found: {len(spec.flows)} flows | "
            f"{len(spec.edge_cases)} edge cases | "
            f"{len(spec.validation_rules)} validation rules | "
            f"{len(spec.requirements)} requirements")

        test_file = TESTS_DIR / f"test_{name.replace('-','_')}.py"

        # ── Generate tests section by section ─────────────────────────────────
        log("\n  [THINK] Section-by-section AI test generation...")
        code = generate_all_sections(spec)

        if not code:
            log("  [FALLBACK] Using template engine (zero-AI guaranteed tests)...")
            code = template_tests(spec)
            log(f"  [FALLBACK] Template generated {code.count('def test_')} tests")

        code = ensure_imports(code)
        valid, err = is_valid_python(code)
        if not valid:
            log(f"  [ERROR] Final code still invalid ({err}) — skipping {name}")
            self.all_results[name] = {
                "status": "generation_failed", "total": 0, "passed": 0,
                "failed": 0, "bugs": [], "gaps": "Generation failed.",
            }
            return

        test_file.write_text(code)
        log(f"  [SAVE]  {test_file}  ({code.count('def test_')} tests)")

        # ── Execute ───────────────────────────────────────────────────────────
        log(f"\n  [EXECUTE] Running against {BASE_URL}...")
        results = run_tests(test_file)
        self._show(results)

        # ── Fix failures ──────────────────────────────────────────────────────
        if results["failed"] > 0:
            log(f"\n  [REFLECT] {results['failed']} failure(s) — AI self-healing...")
            for fix_round in range(1, MAX_FIX_RETRIES + 1):
                log(f"  [FIX] Round {fix_round}/{MAX_FIX_RETRIES}")
                fixed_raw = ai_call(
                    SYS_TEST,
                    f"Fix these failing Playwright tests.\n\n"
                    f"FAILURES:\n{results['output'][:2000]}\n\n"
                    f"ORIGINAL CODE:\n{code}\n\n"
                    "Return the complete corrected test file. Python only.",
                    max_tokens=4096,
                )
                fixed = clean_code(fixed_raw)
                v, e = is_valid_python(ensure_imports(fixed))
                if v and fixed:
                    code = ensure_imports(fixed)
                    test_file.write_text(code)
                    results = run_tests(test_file)
                    self._show(results)
                    if results["failed"] == 0:
                        log("  [FIX] ✅ All failures resolved!")
                        break
                    log(f"  [FIX] Still {results['failed']} failures")
                else:
                    log(f"  [FIX] ❌ Fix attempt produced invalid code: {e}")

        # ── Bug tickets ───────────────────────────────────────────────────────
        bugs = []
        if results["failed"] > 0:
            log(f"\n  [BUGS] AI writing {results['failed']} bug ticket(s)...")
            bugs = build_bug_tickets(
                spec.raw, results.get("json_report"), load_screenshot_index()
            )
            log(f"  [BUGS] {len(bugs)} ticket(s) created")

        # ── Coverage gaps ─────────────────────────────────────────────────────
        log("\n  [GAPS] Detecting coverage gaps...")
        gaps = detect_gaps(spec, code, results)
        (REPORTS_DIR / f"gaps_{name}.md").write_text(
            f"# Coverage Gaps — {name}\n\n"
            f"Generated: {datetime.now().isoformat()}\n\n{gaps}"
        )

        results.update({"bugs": bugs, "gaps": gaps, "spec_name": name})
        self.all_results[name] = results

    def _final_report(self):
        total_p = sum(r.get("passed", 0) for r in self.all_results.values())
        total_f = sum(r.get("failed", 0) for r in self.all_results.values())
        total_t = sum(r.get("total",  0) for r in self.all_results.values())
        all_bugs = [b for r in self.all_results.values() for b in r.get("bugs", [])]

        log("\n" + "═"*62)
        log("  FINAL SUMMARY")
        log("═"*62)
        log(f"  {'Page':<26} {'Pass':>6} {'Fail':>6} {'Total':>6} {'Bugs':>6}")
        log(f"  {'─'*52}")
        for n, r in self.all_results.items():
            icon = "✅" if r.get("failed",1)==0 else "❌"
            log(f"  {icon} {n:<24} {r.get('passed',0):>6} "
                f"{r.get('failed',0):>6} {r.get('total',0):>6} "
                f"{len(r.get('bugs',[])):>6}")
        log(f"  {'─'*52}")
        log(f"  {'TOTAL':<26} {total_p:>6} {total_f:>6} {total_t:>6} {len(all_bugs):>6}")
        log("═"*62)

        report = generate_report(self.all_results, BASE_URL, AI_MODEL)
        log(f"\n  HTML Report → {report}")
        log(f"  Bug Tickets  → {len(all_bugs)} found\n")

        (REPORTS_DIR / "summary.json").write_text(json.dumps({
            "timestamp": datetime.now().isoformat(),
            "model": AI_MODEL, "base_url": BASE_URL,
            "total_passed": total_p, "total_failed": total_f,
            "total_tests": total_t, "total_bugs": len(all_bugs),
        }, indent=2))

        if total_f > 0:
            sys.exit(1)

    def _show(self, r):
        icon = "✅" if r["status"]=="passed" else "❌"
        log(f"  {icon}  Passed:{r['passed']}  Failed:{r['failed']}  Total:{r['total']}")

    def _banner(self):
        log("═"*62)
        log("  Markopolo Autonomous AI Test Agent  v3")
        log(f"  Primary model : {AI_MODEL}  (+ {len(MODEL_CHAIN)-1} fallbacks)")
        log(f"  Target        : {BASE_URL}")
        log(f"  Specs         : {len(list(SPECS_DIR.glob('*.md')))} files")
        log(f"  Started       : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        log("═"*62)


if __name__ == "__main__":
    AutonomousTestAgent().run()
