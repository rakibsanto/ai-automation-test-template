"""
Browser Agent — autonomous browser control via browser-use + local Ollama.

Uses https://github.com/browser-use/browser-use with local Ollama models.
Zero API keys required — completely free and open-source.

Features:
  • Autonomous selector discovery (visits page, finds real CSS selectors)
  • Exploratory testing (AI browses page, finds issues automatically)
  • Flow validation (validates user flows by actually performing them)

Requirements (optional — graceful fallback if not installed):
    pip install browser-use langchain-ollama

Best local models for browser-use (need tool/function calling support):
    qwen2.5:7b          — best balance of quality + speed
    qwen2.5-coder:7b    — good for form/button interaction
    llama3.2:3b         — lightweight option
    mistral:7b          — strong reasoning

Enable in agent.py:
    BROWSER_USE_ENABLED=true BROWSER_USE_MODEL=qwen2.5:7b python ai_engine/agent.py

Note: Small models (1.5b, 1b) may not support tool calling reliably.
      browser-use is skipped automatically if the model doesn't respond correctly.
"""

from __future__ import annotations
import asyncio, os, json, re
from pathlib import Path

# ── Optional imports — graceful fallback if not installed ─────────────────────
try:
    from browser_use import Agent as BUAgent
    _BU_INSTALLED = True
except ImportError:
    _BU_INSTALLED = False

try:
    from langchain_ollama import ChatOllama
    _LANGCHAIN_OLLAMA_INSTALLED = True
except ImportError:
    _LANGCHAIN_OLLAMA_INSTALLED = False

BASE_URL          = os.getenv("BASE_URL",           "https://beta-stg.markopolo.ai")
BROWSER_USE_MODEL = os.getenv("BROWSER_USE_MODEL",  "qwen2.5:7b")
_BU_TIMEOUT       = int(os.getenv("BROWSER_USE_TIMEOUT", "120"))  # seconds per task


def _available() -> bool:
    """Check if browser-use and langchain-ollama are both installed."""
    if not _BU_INSTALLED:
        return False
    if not _LANGCHAIN_OLLAMA_INSTALLED:
        return False
    return True


def _get_llm(model: str | None = None):
    """Return a ChatOllama instance configured for local inference."""
    if not _LANGCHAIN_OLLAMA_INSTALLED:
        raise ImportError("pip install langchain-ollama")
    m = model or BROWSER_USE_MODEL
    return ChatOllama(
        model=m,
        num_ctx=16000,        # larger context for browser tasks
        temperature=0.1,      # low temp for deterministic actions
    )


async def _run_task(task: str, model: str, timeout: int = _BU_TIMEOUT) -> str:
    """Run a browser-use task with a hard timeout. Returns result as string."""
    if not _available():
        return ""
    llm = _get_llm(model)
    agent = BUAgent(task=task, llm=llm)
    try:
        result = await asyncio.wait_for(agent.run(), timeout=timeout)
        return str(result) if result else ""
    except asyncio.TimeoutError:
        return f"[TIMEOUT after {timeout}s]"
    except Exception as e:
        return f"[ERROR: {e}]"


def discover_page(url: str, compiled_spec: dict, model: str | None = None) -> dict:
    """
    Use browser-use to autonomously discover page details.
    Enriches the compiled spec with real selectors and any visible issues.

    Returns dict with keys:
        selectors: {name: css_selector} — discovered CSS selectors
        issues:    [str]                — any visible errors/warnings found
        page_info: {title, h1, forms}  — basic page metadata
    """
    if not _available():
        return {"selectors": {}, "issues": [], "page_info": {}}

    m = model or BROWSER_USE_MODEL

    # Build a targeted prompt from the spec
    element_hints = []
    for key, val in compiled_spec.get("selectors", {}).items():
        label = val.get("label", key) if isinstance(val, dict) else key
        element_hints.append(label)
    hints_text = ", ".join(element_hints[:10]) if element_hints else "form fields, buttons"

    task = f"""Navigate to {url} and do the following:

1. Find the CSS selectors for these elements: {hints_text}
   - For each element, provide the most specific CSS selector that uniquely identifies it
   - Prefer: id > data-testid > input[type=...] > .class > tag

2. Look for any visible errors, broken images, or JavaScript errors

3. Report the page title and main heading (h1)

Return your findings as a JSON object like:
{{
  "selectors": {{
    "email": "input[type='email']",
    "password": "input[type='password']",
    "submit": "button[type='submit']"
  }},
  "issues": ["console error: ...", "broken image: ..."],
  "page_info": {{
    "title": "Page Title",
    "h1": "Main Heading"
  }}
}}

Only return the JSON, no other text."""

    raw = asyncio.run(_run_task(task, m))

    # Parse JSON from response
    result = {"selectors": {}, "issues": [], "page_info": {}}
    try:
        # Try to extract JSON from the response
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            data = json.loads(match.group())
            result["selectors"] = data.get("selectors", {})
            result["issues"]    = data.get("issues", [])
            result["page_info"] = data.get("page_info", {})
    except (json.JSONDecodeError, AttributeError):
        # If no JSON, treat the whole response as an issue note
        if raw and not raw.startswith("[ERROR") and not raw.startswith("[TIMEOUT"):
            result["issues"].append(f"browser-use response (non-JSON): {raw[:200]}")

    return result


def run_exploratory_check(url: str, page_name: str, model: str | None = None) -> list[str]:
    """
    Let browser-use autonomously browse the page and report any issues it finds.
    Returns a list of issue descriptions.
    """
    if not _available():
        return []

    m = model or BROWSER_USE_MODEL

    task = f"""You are a QA tester. Go to {url} (the {page_name} page) and:

1. Look at the page carefully — is it loading correctly?
2. Try to interact with the main form/button if present
3. Check for: broken layouts, missing text, error messages, JavaScript alerts
4. Check that the page title makes sense
5. Try scrolling to see if content is cut off

List every issue you find, one per line, as:
ISSUE: <description>

If no issues, say:
NO_ISSUES: Page looks correct

Be specific and brief. Max 10 issues."""

    raw = asyncio.run(_run_task(task, m))
    issues = []
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("ISSUE:"):
            issues.append(line[6:].strip())
    return issues


def validate_flow(url: str, flow_steps: list[str], model: str | None = None) -> dict:
    """
    Validate a user flow by having browser-use actually perform it.
    Returns {success: bool, actual_result: str, issues: [str]}.
    """
    if not _available():
        return {"success": False, "actual_result": "browser-use not available", "issues": []}

    m = model or BROWSER_USE_MODEL
    steps_text = "\n".join(f"{i+1}. {s}" for i, s in enumerate(flow_steps))

    task = f"""Perform this user flow on {url}:

{steps_text}

After completing (or failing) each step:
- If a step fails, stop and report FAILED: <reason>
- If all steps succeed, report SUCCESS: <what happened>
- Note any unexpected behavior as ISSUE: <description>

Be brief and factual."""

    raw = asyncio.run(_run_task(task, m))

    success = "SUCCESS:" in raw
    issues  = [line.split("ISSUE:", 1)[1].strip()
               for line in raw.splitlines() if "ISSUE:" in line]

    return {
        "success":       success,
        "actual_result": raw[:500],
        "issues":        issues,
    }


# ── CLI usage ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    if not _available():
        print("browser-use not available. Install with:")
        print("  pip install browser-use langchain-ollama")
        sys.exit(1)

    url   = sys.argv[1] if len(sys.argv) > 1 else BASE_URL
    model = sys.argv[2] if len(sys.argv) > 2 else BROWSER_USE_MODEL
    print(f"Running exploratory check on {url} with {model}...")
    issues = run_exploratory_check(url, "page", model=model)
    if issues:
        print(f"Found {len(issues)} issue(s):")
        for i in issues:
            print(f"  • {i}")
    else:
        print("No issues found.")
