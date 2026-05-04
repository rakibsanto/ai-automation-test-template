# Markopolo Autonomous AI Testing

> **Intent-based autonomous QA system** — describe your app in Markdown, AI handles everything else.

**Zero API keys. Zero hardcoded scripts. Zero manual maintenance. 100% free and open source.**

---

## What Is This?

A self-writing, self-healing QA automation system that:

1. **Reads** your Markdown spec files (written by a human QA)
2. **Compiles** them into deterministic JSON (no AI guessing structure)
3. **Generates** Playwright tests across all **22 testing types**
4. **Validates** the generated code before execution (AST gate)
5. **Runs** tests against your staging environment
6. **Heals** failures automatically (3 rounds of AI self-fix)
7. **Reports** a professional HTML bug report with POC screenshots
8. **Learns** from failures via persistent memory between runs
9. **Browses** autonomously via [browser-use](https://github.com/browser-use/browser-use) + local Ollama (no API key)

```
specs/*.md → Spec Compiler → JSON → AI → 22 Test Types → Validate → Execute
           → Self-Heal → Bug Tickets (with POC) → Gap Analysis → HTML Report
           ↑
       browser-use (optional) — autonomously discovers selectors + explores pages
```

Push a change → GitHub Actions runs the full pipeline automatically.

---

## Architecture (v5)

```
your-page.md
   ↓
spec_compiler.py  ← converts MD to structured JSON (deterministic, no AI)
   ↓
your-page.spec.json  ← selector map + flows + edge cases + test data
   ↓
test_generator.py  ← 22 test types, real test data injected from spec
   ↓
test_validator.py  ← AST gate (blocks syntax errors, missing assertions)
   ↓
pytest execution   ← conftest.py captures network + console + performance
   ↓
memory.py          ← records failures, persists selector fixes between runs
   ↓
self-heal loop     ← AI rewrites failing tests (max 3 rounds)
   ↓
bug_builder.py     ← per-failure AI bug tickets with POC screenshots
   ↓
gap_checker.py     ← coverage gap analysis against spec requirements
   ↓
reporter.py        ← full HTML report (screenshots, network logs, evidence)
   ↓
generate_ci_summary.py  ← GitHub Step Summary: test data per type, pass/fail per test
```

### Old vs New

| Old Approach (v1)               | This Approach (v5)                              |
|---------------------------------|-------------------------------------------------|
| AI interprets raw Markdown      | Compiler extracts structure first               |
| AI guesses selectors            | Selector map built from UI element table        |
| Same spec → different tests     | Same spec → same JSON → deterministic tests     |
| One giant AI prompt             | 22 focused prompts, real test data injected     |
| No validation before execution  | AST validator blocks broken code                |
| Starts fresh every run          | Memory persists fixes between runs              |
| 5-model fallback chain          | 14-model fallback chain (all free/open-source)  |
| `assert page.url` only          | Real fill + click + assert using compiled selectors |
| CI shows pass/fail only         | CI shows per-type test data, failure messages   |

---

## Quick Start (One Command)

```bash
git clone https://github.com/mejbaur-markopolo/Markopolo-Automation-Testing.git
cd Markopolo-Automation-Testing
bash setup.sh
```

`setup.sh` installs Ollama, pulls models interactively, installs Python deps, verifies all modules, and creates a `.env` file.

Then run:

```bash
source .env
python ai_engine/agent.py
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
Actions → Markopolo Autonomous AI Testing → Run workflow → browser_use: true
```

Note: browser-use needs a larger model (7b+) which isn't pulled by default in CI. If enabled without the right model, it falls back gracefully.

---

## 22 Test Types

| # | Type | What It Tests |
|---|------|---------------|
| 1 | **Smoke** | 4 critical-path checks in under 60s each |
| 2 | **Functional** | Every user flow defined in the spec |
| 3 | **Validation** | Form field rules (valid/invalid inputs + error messages) |
| 4 | **Negative** | Wrong credentials, rejected inputs, unexpected states |
| 5 | **Boundary** | Min/max length, 255 chars, overflow, empty strings |
| 6 | **Data Driven** | `@pytest.mark.parametrize` with spec test data table |
| 7 | **Deep Form** | Tab order, paste, password masking, autocomplete, required marks |
| 8 | **API/Network** | Request method, response status, response body structure |
| 9 | **Accessibility** | axe-core violations, ARIA labels, keyboard navigation |
| 10 | **Responsive** | 6 viewports: 375px → 1920px (parametrized) |
| 11 | **Navigation** | Internal links (forgot password, sign up, back, etc.) |
| 12 | **Session/Auth** | Token persistence, redirect when authenticated |
| 13 | **Performance** | Page load < 3s, DOMContentLoaded, Web Vitals |
| 14 | **Console Errors** | No JS errors on load or form interaction |
| 15 | **Error States** | No stack traces exposed, network error handling |
| 16 | **Visual/Layout** | Elements within viewport, title set, favicon loads |
| 17 | **Cross-browser** | Smoke tests tagged for Chromium / Firefox / WebKit |
| 18 | **i18n** | Arabic RTL, Chinese, emoji, accented chars, zero-width |
| 19 | **Rate Limiting** | Rapid submission, brute force, double-click |
| 20 | **Cookie/Storage** | localStorage no passwords, session cookies, storage isolation |
| 21 | **Security** | 16 XSS + 13 SQLi OWASP vectors via `@pytest.mark.parametrize` |

Each type generates **4–8 test functions** with:
- Real test data from your spec injected into prompts
- `# TEST_DATA: <value>` comments for CI traceability
- Assertion messages that show actual vs expected values

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

GitHub Actions runs all 22 test types automatically.

---

## Manual Setup (step by step)

### Prerequisites

- macOS or Linux, Python 3.10+

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
curl -fsSL https://ollama.ai/install.sh | sh && ollama serve &
```

### 3. Pull models

```bash
# Minimum — CI grade (986 MB):
ollama pull qwen2.5-coder:1.5b

# Recommended for local — best quality (4.7 GB):
ollama pull qwen2.5-coder:7b

# Optional extra backups:
ollama pull llama3.2:1b
ollama pull phi3.5
```

### 4. Install Python deps

```bash
pip install -r requirements.txt
playwright install chromium
```

### 5. Run

```bash
# Default staging URL
python ai_engine/agent.py

# Custom URL + better model
BASE_URL=https://your-app.com AI_MODEL=qwen2.5-coder:7b python ai_engine/agent.py

# With test password
TEST_PASSWORD=YourPass python ai_engine/agent.py
```

### 6. View report

```bash
open reports/bug-report.html
```

---

## Project Structure

```
Markopolo-Automation-Testing/
│
├── specs/                        ← YOUR INPUT (edit these)
│   ├── login.md                  ← Login page spec
│   ├── reset-password.md         ← Password reset spec
│   ├── signup.md                 ← Registration spec
│   ├── TEMPLATE.md               ← Copy this to add new pages
│   └── *.spec.json               ← Auto-compiled (do not edit)
│
├── ai_engine/                    ← Core system
│   ├── agent.py                  ← Main orchestrator + 14-model chain
│   ├── spec_parser.py            ← Parses MD into ParsedSpec dataclass
│   ├── spec_compiler.py          ← MD → structured JSON (deterministic)
│   ├── test_generator.py         ← 22 test types with real test data
│   ├── test_validator.py         ← AST gate (syntax + assertions)
│   ├── evidence.py               ← Network/console/performance capture
│   ├── bug_builder.py            ← AI bug ticket writer
│   ├── gap_checker.py            ← Coverage gap analysis
│   ├── memory.py                 ← Persistent learning between runs
│   └── reporter.py               ← HTML report generator
│
├── scripts/
│   └── generate_ci_summary.py   ← Writes detailed GitHub Step Summary
│                                    (test data per type, pass/fail per test)
│
├── payloads/                     ← OWASP security vectors
│   ├── xss.txt                   ← 16 XSS vectors
│   ├── sqli.txt                  ← 13 SQL injection vectors
│   ├── boundary.txt              ← 9 boundary strings
│   └── __init__.py
│
├── tests/                        ← AI-generated tests (runtime)
├── reports/                      ← Test results (runtime)
│   ├── bug-report.html           ← Main HTML report (dark theme)
│   ├── screenshots/              ← Failure screenshots (POC)
│   ├── evidence/                 ← Per-test network/console/perf data
│   ├── test_data_log.json        ← What test data AI used per type
│   ├── ci_summary.md             ← GitHub Step Summary source
│   ├── gaps_*.txt                ← Coverage gap reports
│   └── summary.json              ← Machine-readable totals
│
├── setup.sh                      ← One-command setup (macOS/Linux)
├── conftest.py                   ← pytest config + evidence capture
├── pytest.ini                    ← pytest settings
├── requirements.txt
└── .github/workflows/
    └── ai-tests.yml              ← Full CI/CD pipeline (19 steps)
```

---

## CI/CD

Every push to `main` triggers the full pipeline automatically.

```
checkout → python 3.12 → deps → playwright → ollama → cache models
→ pull 4 models → verify 11 modules → compile specs → run AI agent
→ generate CI summary → upload 5 artifacts
```

### Artifacts per run

| Artifact | Contents |
|----------|----------|
| `bug-report-N` | Self-contained HTML report with screenshots |
| `screenshots-N` | PNG failure screenshots (POC evidence) |
| `full-reports-N` | All reports + evidence + JSON data |
| `ai-generated-tests-N` | The 22-type generated Playwright test files |
| `compiled-specs-N` | Compiled JSON spec files |

### GitHub Step Summary (per run)

The Actions summary tab shows:
- AI model used + full model chain
- Per-type breakdown with collapsible test tables
- Test data used for each test case (`# TEST_DATA:` annotations)
- Pass/fail status per test function
- Failure messages inline (no digging into logs needed)
- Coverage gaps detected
- Links to all artifacts

### Manual trigger with custom settings

Go to: **Actions → Markopolo Autonomous AI Testing → Run workflow**

You can override:
- **AI model** — e.g. `qwen2.5-coder:7b` for better quality
- **Target URL** — test against a different environment

### CI model caching

Models are cached between runs using `actions/cache@v4`. After the first run (~15 min), subsequent runs skip the download and start in ~2 min.

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

OWASP-standard vectors for authorized security testing:

- `payloads/xss.txt` — 16 XSS vectors (script tags, event handlers, data URIs, etc.)
- `payloads/sqli.txt` — 13 SQL injection vectors (UNION, OR 1=1, blind, etc.)
- `payloads/boundary.txt` — 9 boundary strings (empty, max-length, null, whitespace)

Tests verify your app handles malicious input safely — they assert the payload is **not executed**, not that it causes an error. Use only on applications you own or have permission to test.

---

## CI Behaviour Notes

### TEMPLATE.md is automatically skipped

`specs/TEMPLATE.md` is never processed as a test spec — the agent skips it automatically. Only your real spec files (login.md, signup.md, etc.) are tested.

### CI job timeout (60 minutes)

The CI job is capped at 60 minutes. Model pulls are limited to three small models (`qwen2.5-coder:1.5b`, `tinyllama:1.1b`, `qwen2.5:0.5b`) to keep CI fast. Larger models (7b+) are for local use.

### Partial results on cancellation

If the CI job is cancelled mid-run, `reports/summary.json` and `reports/test_data_log.json` are still written with whatever completed (marked `"partial": true`). The GitHub Step Summary will show partial results.

### ollama.chat() has a 90-second timeout

Each AI call has a `AI_TIMEOUT=90s` hard limit. If a model hangs (slow cold start, partial download), it is skipped after 90 seconds and the next model in the chain is tried.

### Each Playwright operation has a 15-second timeout

`conftest.py` sets `page.set_default_timeout(15000)` on every test page. Navigation uses `wait_until="domcontentloaded"` instead of `"networkidle"` to avoid hanging on pages with long-polling or websockets.

---

## Troubleshooting

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
