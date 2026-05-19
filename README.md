# Autonomous AI Testing

> **Intent-based autonomous QA system** — describe your app in Markdown, AI handles everything else.

**Zero API keys. Zero hardcoded scripts. Zero manual maintenance. 100% free and open source.**

---

## What Is This?

A self-writing, self-healing QA automation system that:

1. **Reads** your Markdown spec files (written by a human QA)
2. **Compiles** them into deterministic JSON (no AI guessing structure)
3. **Generates** Playwright tests across **24 test types** — ≥330 runtime tests per spec
4. **Validates** the generated code before execution (AST gate)
5. **Runs** tests against your staging environment
6. **Heals** failures with a **surgical selector self-fix** — extracts the broken locator, asks AI for one replacement, persists via `memory.update_selector` so the fix survives across runs (full-file regen as fallback)
7. **Caches** generated test code by `sha256(spec_md + base_url)` — unchanged specs reuse last run's tests, persisted to gh-pages so stateless CI runners benefit
8. **Detects multiple languages** from each spec md (`/en`, `/ar`, …) and runs the suite per locale (page loads, `<html lang>`, `dir="rtl"` enforcement)
9. **Walks every spec URL** autonomously via QA-19 (deterministic walk + optional [browser-use](https://github.com/browser-use/browser-use) + Ollama)
10. **Reports** a professional HTML report with POC screenshots, annotated failure videos (.webm), live history and trend charts on GitHub Pages

```
specs/*.md ─► Spec Compiler ─► JSON ─► AI ─► 24 Test Types ─► AST Validate ─► Execute
                                       │                                        │
                                       │   ◄── cache lookup (sha256)            ▼
                                       │                                  Surgical Self-Heal
                                       └── Anti-Hallucination Guard       (selector fix → memory)
                                              "use ONLY spec fields"             │
                                                                                 ▼
       browser-use (optional, QA-19)  ────────►  Autonomous Walk ─►  Bug Tickets (POC + video)
       walks every spec URL +                                              │
       4 hand-picked URLs                                                  ▼
                                                                  HTML Report + Trend Charts
                                                                          │
                                                                          ▼
                                                              GitHub Pages (live, public)
```

Push a change → GitHub Actions runs **18 parallel QA agent jobs** + AI Test Agent + consolidate-and-publish to GitHub Pages.

---

## Architecture (v5)

```
your-page.md
   ↓
spec_parser.py    ← extracts URL, languages, flows, edge cases, validation rules,
                    test data — all deterministic, no AI
   ↓
spec_compiler.py  ← MD → structured JSON (UI element selector map)
   ↓
your-page.spec.json
   ↓
test_memory.py    ← cache lookup: sha256(spec_md + base_url)
                    cache HIT  → reuse last run's tests, skip AI
                    cache MISS → continue to generation ↓
   ↓
test_generator.py ← 24 test types — real test data injected
                    anti-hallucination guard: "use ONLY spec fields"
                    parametrize-heavy: ≥330 runtime tests / spec
   ↓
test_validator.py ← AST gate (blocks syntax errors, missing assertions)
   ↓
pytest execution  ← conftest.py captures network + console + performance + video
                    HEADED=1 opens a real browser window so you watch it run
   ↓
self-heal loop    ← (a) Surgical: extract failing selector → AI suggests one
                        replacement → memory.update_selector (persists)
                    (b) Full-file regen — fallback if surgical fails
                    Max 3 rounds.
   ↓
memory.py         ← records failures, persists selector fixes across runs
   ↓
bug_builder.py    ← per-failure AI bug tickets with POC screenshots + .webm video
   ↓
gap_checker.py    ← coverage gap analysis against spec requirements
   ↓
reporter.py       ← master HTML report (dark theme, click-to-expand, filters)
   ↓
build_pages_site.py ← consolidates 18 agents → publishes to gh-pages
                       index + history table + trend chart + per-agent reports
```

### Old vs New

| Old Approach (v1)               | This Approach (v5)                              |
|---------------------------------|-------------------------------------------------|
| AI interprets raw Markdown      | Compiler extracts structure first               |
| AI guesses selectors            | Selector map built from UI element table        |
| AI invents fields not in spec   | Anti-hallucination guard on every prompt        |
| Same spec → different tests     | Same spec → same JSON → deterministic tests     |
| One giant AI prompt             | 24 focused prompts, real test data injected     |
| No validation before execution  | AST validator blocks broken code                |
| Starts fresh every run          | Persistent memory + sha256 test cache (gh-pages backed) |
| 5-model fallback chain          | 14-model fallback chain (all free/open-source)  |
| Full-file regen on every fail   | Surgical selector self-heal first, full regen as fallback |
| `assert page.url` only          | Real fill + click + assert using compiled selectors |
| CI shows pass/fail only         | CI shows per-type test data, failure messages   |
| One language only               | Multi-language detection per spec (en, ar, …)   |
| Single-runner CI                | 18 parallel QA agent jobs + AI agent + consolidate + Pages |

---

## Quick Start (One Command)

```bash
git clone https://github.com/mejbaur-markopolo/Markopolo-Automation-Testing.git
cd Markopolo-Automation-Testing

# Setup Configuration
cp .env.example .env
# Edit .env to set your PROJECT_NAME, BASE_URL, and credentials (TEST_USERNAME/PASSWORD)

python run.py
```

That's it. On first invocation `run.py` calls `install.py`, which on macOS / Linux / Windows:

- verifies Python ≥ 3.10
- `pip install -r requirements.txt`
- installs Playwright Chromium (with Linux system libs)
- installs Ollama (Homebrew on macOS, official `install.sh` on Linux,
  prints the Windows installer URL)
- starts `ollama serve` in the background
- pulls the small first-run model (`qwen2.5-coder:1.5b` — ~1 GB)

Then it opens a real Chromium window so you can **watch** the QA suite run live
(`HEADED=1`, slow-motion 800 ms between actions).

### Run modes

```bash
python run.py            # demo: TestQA01Functional with visible browser (~3 min)
python run.py --ai       # AI Test Agent v5 — auto-generates from md specs
python run.py --all      # every QA agent suite — full ~30 min run
python run.py --headless # same as default but no visible window
python run.py --url https://your-staging.example.com   # any URL
```

### Just check the environment

```bash
python install.py --check   # report what's installed / missing, install nothing
python install.py --big     # install + pull the 7b model (~5 GB) for stronger AI
```

---

## AI Stack (all free, all local, no API keys)

### 14-Model Fallback Chain

If the primary model fails, the next is tried automatically. No intervention needed.

| # | Model | Size | Notes |
|---|-------|------|-------|
| 1 | `qwen2.5-coder:7b` | 4.7 GB | Best code quality — use locally |
| 2 | `deepseek-coder:6.7b` | 3.8 GB | Excellent code model |
| 3 | `codellama:7b` | 3.8 GB | Meta code model |
| 4 | `mistral:7b` | 4.1 GB | Strong general model |
| 5 | `phi4:3.8b` | 2.3 GB | Microsoft Phi-4 |
| 6 | `llama3.2:3b` | 2.0 GB | Meta 3B |
| 7 | `phi3.5` | 2.2 GB | Microsoft Phi-3.5 |
| 8 | `gemma2:2b` | 1.6 GB | Google Gemma2 |
| 9 | `llama3.2:1b` | 1.3 GB | Meta 1B |
| 10 | `qwen2.5-coder:1.5b` | 986 MB | **Default CI model** |
| 11 | `tinyllama:1.1b` | 637 MB | Ultra-tiny fallback |
| 12 | `qwen2.5:0.5b` | 395 MB | Smallest possible fallback |

> Set a different primary with `AI_MODEL=qwen2.5-coder:7b python ai_engine/agent.py`

**Template fallback**: if every AI model fails, a deterministic template engine generates valid tests using the compiled spec's CSS selectors — tests always run, even with zero AI.

---

## browser-use Integration (Autonomous Browser AI)

This system integrates [browser-use](https://github.com/browser-use/browser-use) — an open-source library that lets an AI agent control a real browser autonomously. Used here with **local Ollama models only** — zero API keys, zero cost.

### What browser-use adds

| Feature | Without browser-use | With browser-use |
|---------|---------------------|------------------|
| Selector discovery | Compiled from spec file | AI visits page, finds real selectors automatically |
| Exploratory testing | Spec-driven only | AI browses page, finds unexpected issues |
| Flow validation | Generated test script | AI actually performs the flow like a real user |

### Enable browser-use

```bash
# Install dependencies
pip install browser-use langchain-ollama

# Pull a model that supports tool calling (needed by browser-use)
ollama pull qwen2.5:7b     # recommended — best local quality
# or
ollama pull llama3.2:3b    # lighter option

# Run with browser-use enabled
BROWSER_USE_ENABLED=true BROWSER_USE_MODEL=qwen2.5:7b python ai_engine/agent.py
```

### Which models work with browser-use

browser-use requires a model that supports **tool/function calling**. Small models (1.5b, 1b) usually don't work well.

| Model | Size | Works? | Notes |
|-------|------|--------|-------|
| `qwen2.5:7b` | 4.7 GB | ✅ Best | Recommended |
| `qwen2.5-coder:7b` | 4.7 GB | ✅ Good | Strong for forms/buttons |
| `llama3.2:3b` | 2.0 GB | ⚠️ Basic | Limited tool calling |
| `mistral:7b` | 4.1 GB | ✅ Good | Strong reasoning |
| `qwen2.5-coder:1.5b` | 986 MB | ❌ Poor | Too small for reliable tool calling |

### What it does in the pipeline

When `BROWSER_USE_ENABLED=true`, after compiling the spec to JSON, the browser agent:

1. **Visits the real page** — navigates to the actual URL
2. **Discovers selectors** — finds real CSS selectors for each UI element and enriches the spec
3. **Reports issues** — any visible errors, broken images, or JS console issues

All discovered selectors are passed into the test generator so tests use real, working selectors instead of guesses.

### In CI (GitHub Actions)

browser-use is **disabled by default** in CI to keep runs fast. Enable it via `workflow_dispatch`:

```
Actions → Autonomous AI Testing → Run workflow → browser_use: true
```

Note: browser-use needs a larger model (7b+) which isn't pulled by default in CI. If enabled without the right model, it falls back gracefully.

---

## Test Types — ≥330 runtime tests per spec

The AI emits one test function (or one parametrized test) per type. `pytest.mark.parametrize` then explodes each into many runtime tests, so a single spec file produces **≥330 tests** without bloating AI generation cost.

| # | Type | Runtime tests / spec | What It Tests |
|---|------|----------------------|---------------|
| 1 | **Smoke** | ~4 | Page reachable, no 5xx, title set, body non-empty |
| 2 | **Functional** | up to **16** | One test per `## User Flows` entry — exact spec order |
| 3 | **Validation** | **8–16** | For every rule: one invalid + one valid input |
| 4 | **Negative** | **16** | Wrong credentials, rejected inputs + 4 universal scenarios (back btn, double-click, paste, rapid-fire) |
| 5 | **Edge Cases** | up to **14** | One test per `## Edge Cases` entry parsed from spec md |
| 6 | **Boundary** | **34** | Length extremes, unicode/RTL/emoji, format strings, path traversal, CRLF, null bytes |
| 7 | **Combinatorial** | **32** | 8 input shapes × 4 viewports — input-shape × viewport matrix |
| 8 | **Data Driven** | ~10 | Parametrized over spec test data table |
| 9 | **Deep Form** | ~5 | Tab order, paste, password masking, autocomplete |
| 10 | **API/Network** | ~6 | Request method, response status, structure |
| 11 | **Accessibility** | ~6 | axe-core violations, ARIA labels, keyboard nav |
| 12 | **Responsive** | ~5 | 5 viewports: 375px → 1920px |
| 13 | **Navigation** | ~5 | Internal links (forgot pw, sign up, back) |
| 14 | **Session/Auth** | ~5 | Token persistence, redirect when authenticated |
| 15 | **Performance** | ~3 | Page load, DOMContentLoaded, Web Vitals |
| 16 | **Console Errors** | ~3 | No JS errors on load or form interaction |
| 17 | **Error States** | ~3 | No stack traces, graceful network errors |
| 18 | **Visual/Layout** | ~3 | Elements within viewport, title, favicon |
| 19 | **Cross-browser** | ~3 | Tagged for Chromium / Firefox / WebKit |
| 20 | **i18n** | **28** | RTL (Arabic, Hebrew, Persian, Urdu) + CJK + emoji + accents + zero-width |
| 21 | **Multi-Language** | 4 × N locales | One per locale parsed from spec — page loads, `<html lang>`, `dir="rtl"`, no JS errors |
| 22 | **Rate Limiting** | ~3 | Rapid submission, brute force, double-click |
| 23 | **Cookie/Storage** | ~3 | localStorage no passwords, session cookies, isolation |
| 24 | **Security** | **100** | 50 XSS + 50 SQLi OWASP vectors via parametrize (×fields tested) |

Each test includes:

- Real test data from your spec injected into prompts (no AI guessing)
- `# TEST_DATA: <value>` comments for CI traceability
- Assertion messages that show expected vs actual
- An anti-hallucination guard in every prompt: AI must use ONLY fields, buttons, URLs, and labels from the spec — no inventing UI elements

---

## Adapt to ANY Project

This system works with any web application. To test a different project:

### Option A — Use the template (fastest)

```bash
cp specs/TEMPLATE.md specs/your-page.md
# Edit specs/your-page.md — fill in URL, selectors, flows, validations
python ai_engine/agent.py
```

`specs/TEMPLATE.md` is a fully documented template with examples for every section.

### Option B — Write from scratch

Create `specs/your-page.md` with these sections:

```markdown
# Page Name: Checkout

## URL
/checkout

## UI Elements
| Element          | Selector / Hint              | Notes     |
|------------------|------------------------------|-----------|
| Email field      | input[type='email']          | Required  |
| Card number      | input[name='cardNumber']     | Required  |
| Pay button       | button[type='submit']        | Text: Pay |

## Requirements
- REQ-001: User can complete checkout with valid card
- REQ-002: Invalid card shows error message

## User Flows
### Flow 1: Successful Checkout
1. Navigate to /checkout
2. Fill in email
3. Fill in card details
4. Click Pay
5. Expect redirect to /order-confirmation

## Validation Rules
| Field  | Rule              | Error Message              |
|--------|-------------------|----------------------------|
| Email  | Valid email format | Please enter a valid email |
| Card   | 16 digits          | Invalid card number        |

## Edge Cases
| ID    | Scenario                      | Expected                  |
|-------|-------------------------------|---------------------------|
| EC-001 | Submit with empty card       | Show validation error     |
| EC-002 | SQL injection in email field | Error, no SQL execution   |

## Test Data
| Category      | Value                    |
|---------------|--------------------------|
| Valid email   | test@mailinator.com      |
| Valid card    | 4111111111111111         |
| Invalid card  | 1234                     |
```

### Step 3: Run

```bash
BASE_URL=https://your-staging.com python ai_engine/agent.py
```

### Step 4: Push to CI

```bash
git add specs/your-page.md
git commit -m "Add checkout spec"
git push
```

GitHub Actions runs all 24 test types + 18 hand-crafted QA agents automatically.

---

## Manual Setup (only if `python install.py` doesn't fit your environment)

`python install.py` already does all of this cross-platform — only follow these steps if you need to install pieces by hand.

### Prerequisites

- macOS, Linux, or Windows
- Python 3.10+

### 1. Clone

```bash
git clone https://github.com/mejbaur-markopolo/Markopolo-Automation-Testing.git
cd Markopolo-Automation-Testing
```

### 2. Install Ollama

```bash
# macOS
brew install ollama && brew services start ollama

# Linux
curl -fsSL https://ollama.com/install.sh | sh && ollama serve &

# Windows
# Download and run the official installer from:
# https://ollama.com/download/windows
```

### 3. Pull models

```bash
# First-run default (~1 GB):
ollama pull qwen2.5-coder:1.5b

# Stronger model for higher-quality generation (~5 GB):
ollama pull qwen2.5-coder:7b
```

### 4. Install Python deps + Playwright

```bash
pip install -r requirements.txt
playwright install chromium               # Linux: add --with-deps
```

### 5. Run

```bash
# Default staging URL with visible browser
python run.py

# AI Test Agent (auto-generate + auto-run)
python run.py --ai

# Custom URL
python run.py --url https://your-app.com

# Or call the agent directly with extra env vars
BASE_URL=https://your-app.com AI_MODEL=qwen2.5-coder:7b TEST_PASSWORD=YourPass python -m ai_engine.agent
```

### 6. View report

```bash
open reports/bug-report.html
```

The CI run also publishes the same report (and the full history + trend charts) to GitHub Pages at `https://<your-org>.github.io/<your-repo>/`.

---

## Project Structure

```
Markopolo-Automation-Testing/
│
├── install.py                    ← Cross-OS one-shot installer
├── run.py                        ← Single-command runner (visible browser by default)
│
├── specs/                        ← YOUR INPUT (edit these)
│   ├── login.md                  ← Login page (with EN + AR locales)
│   ├── student_*.md              ← Student-side flows (favorites, payments, etc.)
│   ├── tutor_*.md                ← Tutor-side flows (signup, calendar, etc.)
│   ├── TEMPLATE.md               ← Copy this to add new pages
│   └── *.spec.json               ← Auto-compiled (do not edit)
│
├── ai_engine/                    ← Core system
│   ├── agent.py                  ← AI Test Agent v5 + surgical self-heal + cache
│   ├── spec_parser.py            ← Parses MD into ParsedSpec (incl. languages, edge cases)
│   ├── spec_compiler.py          ← MD → structured JSON (deterministic)
│   ├── spec_directives.py        ← Honors "skip X" directives in spec md
│   ├── test_generator.py         ← 24 test types with real test data + anti-hallucination
│   ├── test_validator.py         ← AST gate (syntax + assertions)
│   ├── test_memory.py            ← Cross-run cache (sha256 of spec + base url)
│   ├── memory.py                 ← Persistent selector fixes + flake markers
│   ├── browser_agent.py          ← browser-use integration (autonomous QA-19)
│   ├── vision_validator.py       ← Vision-LLM (qwen2-vl) for QA-22
│   ├── langgraph_agent.py        ← LangGraph orchestrator (QA-5)
│   ├── evidence.py               ← Network/console/performance capture
│   ├── bug_builder.py            ← AI bug ticket writer
│   ├── gap_checker.py            ← Coverage gap analysis
│   └── reporter.py               ← HTML report generator (dark theme)
│
├── tests/
│   ├── test_qa_comprehensive.py  ← 22 hand-crafted QA test classes (QA-01..22)
│   ├── _visual_diff.py           ← Pixel-diff for QA-11 visual regression
│   └── visual_baselines/         ← Saved baseline screenshots
│
├── scripts/
│   ├── consolidate_reports.py    ← Merges all 19 CI artifacts into master report
│   ├── build_pages_site.py       ← GitHub Pages site (index, history, agent reports)
│   ├── test_data_viewer.py       ← Expandable "Test Data Used" report section
│   └── generate_ci_summary.py    ← GitHub Step Summary
│
├── payloads/                     ← OWASP security vectors
│   ├── xss.txt                   ← 50 XSS vectors
│   ├── sqli.txt                  ← 50 SQL injection vectors
│   ├── boundary.txt              ← 60+ boundary strings
│   └── __init__.py
│
├── cache/                        ← AI test-code cache (sha256-keyed, gh-pages backed)
│   └── tests/<slug>.json
│
├── reports/                      ← Test results (runtime)
│   ├── bug-report.html           ← Master HTML report
│   ├── screenshots/              ← Failure screenshots (POC, annotated)
│   ├── videos/                   ← .webm video PoC for failed tests
│   ├── evidence/                 ← Per-test network/console/perf JSON
│   ├── test_data_log.json        ← Every test data input the run exercised
│   ├── trends.json               ← Cumulative pass-rate trend across runs
│   └── summary.json              ← Machine-readable totals
│
├── conftest.py                   ← pytest config + evidence capture + HEADED support
├── pytest.ini
├── requirements.txt
└── .github/workflows/
    └── ai-tests.yml              ← 18 parallel QA agents + AI Test Agent + consolidate
```

---

## CI/CD

Every push to `main` triggers the full pipeline. **20 jobs run in parallel**:

| Job | Covers |
|-----|--------|
| AI Test Agent v5 | Auto-generates 24 test types per spec; runs them; bug-tickets failures |
| QA Agent 1 | QA-01 Functional, QA-02 Edge Cases |
| QA Agent 2 | QA-03 Security (172 tests), QA-04 Performance, QA-05 Hallucination/Data |
| QA Agent 3 | QA-06 API & Network, QA-07 Accessibility |
| QA Agent 4 | QA-08 Mobile / Cross-viewport |
| QA Agent 5 | LangGraph AI Orchestration |
| QA Agent 6–18 | QA-09 SEO, QA-10 i18n, QA-11 Visual Regression, QA-12 JS Errors, QA-13 Security Headers, QA-14 Cookies, QA-15 OWASP Surface, QA-16 Core Web Vitals, QA-17 Memory Leak, QA-18 Network Resilience, QA-19 Autonomous Explorer, QA-20 Property Fuzz, QA-22 Vision-LLM |
| Consolidate | Merges every artifact into the master HTML report |
| pages-deploy | Publishes report + history + trend chart to GitHub Pages |

### Artifacts per run

| Artifact | Contents |
|----------|----------|
| `qa-agent-N-reports-RUN` | Per-agent HTML + JSON + screenshots + videos |
| `ai-test-agent-RUN` | AI-generated test files + per-spec results |
| `master-report-RUN` | Consolidated HTML report + bug tickets + trend |
| `cache-RUN` | AI test-code cache (gh-pages-backed across runs) |

### GitHub Step Summary (per run)

The Actions summary tab shows:

- AI model used + full model chain
- Per-type breakdown with collapsible test tables
- Test data used for each test case (`# TEST_DATA:` annotations)
- Pass/fail status per test function
- Failure messages inline
- Coverage gaps detected
- Links to all artifacts and the live GitHub Pages report

### Manual trigger with custom settings

Go to: **Actions → Autonomous AI Testing → Run workflow**

Inputs:
- **AI model** — e.g. `qwen2.5-coder:7b` for higher quality
- **Target URL** — test against a different environment
- **browser_use** — enable autonomous browser exploration (QA-19)
- **enable_vision** — enable QA-22 vision-LLM (pulls a 5 GB model)

### CI model + test caching

- **Ollama models** are cached between runs via `actions/cache@v4`. First run pulls ~1 GB; subsequent runs skip the download.
- **Generated test code** is cached by `sha256(spec_md + base_url)` and persisted to gh-pages. Unchanged specs reuse last run's tests so the AI Test Agent only calls Ollama for new or modified specs.

### Live report site

After each successful run, GitHub Pages is updated at `https://<owner>.github.io/<repo>/` with:

- The current master report + every per-agent report
- A **history table** showing every prior run (sourced from `trends.json` so all runs are listed even if older `run-N.html` files were cleaned up)
- A **trend sparkline** with pass-rate per run + alerts on regressions

---

## How It Works: Fallback Chain

```
AI call attempt
   ↓
qwen2.5-coder:1.5b (primary)    ← try
   ↓ fails
llama3.2:1b                     ← try
   ↓ fails
phi3.5                          ← try
   ↓ fails
qwen2.5:0.5b                    ← try
   ↓ all fail
Template engine (zero-AI)       ← always works
   Uses compiled spec selectors:
   - fills input[type='email']
   - fills input[type='password']
   - clicks button[type='submit']
   - asserts no 500/404, console errors, load time < 5s
```

The template engine is not a "dummy" — it uses the CSS selectors compiled from your spec to generate tests that actually interact with your page's form fields.

---

## Spec Format Reference

```markdown
## UI Elements       ← table: Element | Selector/Hint | Notes
## Requirements      ← bullet list or table: REQ-X-NN description
## User Flows        ← ### Flow N — Name, then numbered steps
## Validation Rules  ← table: Field | Rule | Error Message
## Edge Cases        ← table: EC-X-NN | Scenario | Expected
## API Contract      ← METHOD /api/endpoint table
## Test Data         ← table: Category | Value
```

The Spec Compiler reads these headings and builds the JSON deterministically. AI never guesses the structure — it only generates test code once the structure is already known.

---

## Security Payloads

OWASP / PortSwigger-standard vectors for authorized security testing:

- `payloads/xss.txt` — **50** XSS vectors (script tags, event handlers, data URIs, SVG, encoded variants)
- `payloads/sqli.txt` — **50** SQL injection vectors (UNION, OR 1=1, blind, time-based, MS-SQL specific)
- `payloads/boundary.txt` — **60+** boundary strings (length extremes, unicode/RTL/emoji, format strings, path traversal, CRLF, null bytes)

Tests verify your app handles malicious input safely — they assert the payload is **not executed** or that the response is graceful (no 500, no leaked stack trace, no DB error). Use only on applications you own or have permission to test.

In addition to the parametrized XSS/SQLi tests, QA-03 ships dedicated **auth-bypass probes**:

- Unauthenticated request to `/api/me`, `/api/admin`, `/api/users/me` — fails only if real PII comes back
- Forged `alg=none` JWT with admin claims — must be rejected with 401/403
- IDOR probe across `/api/users/{1,2,999,uuid}`
- Session cookies must have `HttpOnly` + `Secure` flags

QA-06 adds **JSON schema validation** — every `application/json` response on page load must parse and be object-or-array shape (catches truncated JSON, HTML-error-pages-with-wrong-content-type, etc.).

---

## CI Behaviour Notes

### TEMPLATE.md / README.md / EXAMPLE.md are automatically skipped

`specs/TEMPLATE.md` is never processed as a test spec — the agent skips it (and any spec starting with `_`). Only your real spec files are tested.

### Spec directives are honoured

Add a line like `<!-- skip: security, performance -->` in a spec md file and the agent will not generate those test types for that spec. Useful for static pages where security / perf testing isn't meaningful.

### CI job timeouts

- **AI Test Agent v5**: 90 min (it generates and runs tests for every spec; cache hits make subsequent runs much faster)
- **QA Agent 1, 2**: 45 min (heaviest hand-crafted suites — QA-03 alone is 172 tests after payload expansion)
- **QA Agent 3 .. 18**: 30 min each
- **Consolidate**: 15 min

### Partial results on cancellation

If the CI job is cancelled mid-run, `reports/summary.json` and `reports/test_data_log.json` are still written with whatever completed (marked `"partial": true`). The Consolidate job runs with `if: always()` so the master report is built even when some agents fail or time out.

### Per-call AI timeout (90 s)

Each `ollama.chat()` call has a 90-second hard limit. If a model hangs, it is skipped and the next model in the chain is tried. After two consecutive timeouts a model is blacklisted for the rest of the session.

### Each Playwright operation has a 15-second timeout

`conftest.py` sets `page.set_default_timeout(15000)` on every test page. Navigation uses `wait_until="domcontentloaded"` instead of `"networkidle"` to avoid hanging on pages with long-polling or websockets. SPA hydration is handled with explicit `page.wait_for_function(...)` checks in `conftest.py` to avoid white-screen captures.

### Concurrency

Pushes cancel older runs (`cancel-in-progress: true`). If you push twice in quick succession, only the newer commit's run keeps going.

---

## Troubleshooting

### `python install.py` says Ollama still not on PATH

Open a fresh terminal (so PATH picks up the new install) and re-run `python install.py`. On Windows the official installer requires a logout/login or a new terminal.

### `python run.py` opens the browser but tests are blank / nothing happens

Staging may be unreachable. Override the URL:

```bash
python run.py --url https://your-actual-staging.example.com
```

### "Ollama not running"

```bash
# macOS
brew services start ollama

# Linux
ollama serve &
```

### "0 tests collected"

Check the generated file directly:

```bash
cat tests/test_login.py
python ai_engine/test_validator.py tests/
```

If the file is empty, all AI models failed and the template engine also failed (rare). Check Ollama is running: `ollama list`.

### "No module named 'ollama'"

```bash
pip install ollama
# or
pip3 install ollama --break-system-packages
```

### AI model not downloaded (404 errors in logs)

```bash
ollama pull qwen2.5-coder:1.5b
ollama list   # verify it shows
```

After 2 consecutive 404s the agent fast-fails to the template engine to avoid log spam.

### Tests pass but all use `assert page.url`

This means the template engine ran (AI unavailable). Pull a model:

```bash
ollama pull qwen2.5-coder:1.5b
```

Or use a larger model for better quality:

```bash
AI_MODEL=qwen2.5-coder:7b python ai_engine/agent.py
```

### "pip not found" on macOS

```bash
pip3 install -r requirements.txt
```

### Reports directory missing

```bash
mkdir -p reports reports/screenshots reports/evidence
```

---

*Built with Ollama + Playwright + pytest + GitHub Actions — zero cloud cost, zero API keys, fully open source.*
