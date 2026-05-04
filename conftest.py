"""
pytest configuration — evidence capture for every test.
Captures: screenshots (on failure), network log, console errors, performance.
All evidence saved to reports/evidence/ and indexed for the HTML bug report.
"""

import re, json, pytest
from pathlib import Path
from datetime import datetime

# ── Directories ───────────────────────────────────────────────────────────────
SCREENSHOTS_DIR = Path("reports/screenshots")
EVIDENCE_DIR    = Path("reports/evidence")

# ── Global index written at session end ───────────────────────────────────────
_SCREENSHOT_INDEX: dict[str, dict] = {}
_EVIDENCE_INDEX:   dict[str, str]  = {}   # nodeid → evidence json path


# ── Browser / context defaults ────────────────────────────────────────────────

@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 720},
        "ignore_https_errors": True,
        "locale": "en-US",
    }


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    return {
        **browser_type_launch_args,
        "headless": True,
        "slow_mo": 0,
    }


@pytest.fixture(autouse=True)
def _set_page_timeouts(request):
    """
    Set a 15-second default timeout on every page operation.
    Prevents tests from hanging indefinitely on slow/broken staging pages.
    Without this, page.wait_for_load_state("networkidle") can block forever.
    """
    if "page" not in request.fixturenames:
        yield
        return
    page = request.getfixturevalue("page")
    page.set_default_timeout(15000)           # 15s for all page operations
    page.set_default_navigation_timeout(15000) # 15s for goto/navigation
    yield


# ── Per-test evidence capture ─────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _capture_evidence(request):
    """Capture network + console + performance for every test that uses `page`."""
    if "page" not in request.fixturenames:
        yield
        return

    page = request.getfixturevalue("page")
    evidence = {"network": [], "console": [], "errors": [], "performance": {}}

    def _on_request(req):
        try:
            evidence["network"].append({
                "type": "request",
                "method": req.method,
                "url": req.url,
                "post_data": req.post_data or "",
            })
        except Exception:
            pass

    def _on_response(resp):
        try:
            evidence["network"].append({
                "type": "response",
                "status": resp.status,
                "url": resp.url,
            })
        except Exception:
            pass

    def _on_console(msg):
        try:
            entry = {"type": msg.type, "text": msg.text}
            evidence["console"].append(entry)
            if msg.type in ("error", "warning"):
                evidence["errors"].append(entry)
        except Exception:
            pass

    page.on("request",  _on_request)
    page.on("response", _on_response)
    page.on("console",  _on_console)

    yield evidence

    # ── Collect performance timing ────────────────────────────────────────────
    try:
        timing = page.evaluate("""() => {
            const t = performance.timing;
            return {
                dom_load_ms:  t.domContentLoadedEventEnd - t.navigationStart,
                page_load_ms: t.loadEventEnd - t.navigationStart,
                ttfb_ms:      t.responseStart - t.navigationStart,
            };
        }""")
        evidence["performance"] = timing
    except Exception:
        pass

    # ── Log console errors ────────────────────────────────────────────────────
    if evidence["errors"]:
        print(f"\n  [CONSOLE] {len(evidence['errors'])} error(s) in {request.node.name}:",
              flush=True)
        for e in evidence["errors"][:3]:
            print(f"    {e['type'].upper()}: {e['text'][:120]}", flush=True)

    # ── Save evidence file ────────────────────────────────────────────────────
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^\w\-]", "_", request.node.nodeid)[:120]
    ev_path = EVIDENCE_DIR / f"{safe}.json"
    ev_path.write_text(json.dumps(evidence, indent=2, default=str))
    _EVIDENCE_INDEX[request.node.nodeid] = str(ev_path)


# ── Screenshot on failure ─────────────────────────────────────────────────────

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report  = outcome.get_result()

    if report.when == "call" and report.failed:
        page = item.funcargs.get("page")
        if page is None:
            return
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        safe = re.sub(r"[^\w\-]", "_", item.nodeid)[:120]
        shot_path = SCREENSHOTS_DIR / f"{safe}.png"
        try:
            page.screenshot(path=str(shot_path), full_page=True)
            _SCREENSHOT_INDEX[item.nodeid] = {
                "path":      str(shot_path),
                "url":       page.url,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as exc:
            print(f"  [SCREENSHOT] Failed for {item.nodeid}: {exc}", flush=True)


# ── Diagnostics ───────────────────────────────────────────────────────────────

def pytest_collection_finish(session):
    n = len(session.items)
    print(f"[COLLECT] {n} test(s) found", flush=True)
    for item in session.items:
        print(f"  → {item.nodeid}", flush=True)


def pytest_internalerror(excrepr, excinfo):
    print(f"[PYTEST INTERNAL ERROR] {excinfo.value}", flush=True)


# ── Write indexes at session end ──────────────────────────────────────────────

def pytest_sessionfinish(session, exitstatus):
    if _SCREENSHOT_INDEX:
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        (SCREENSHOTS_DIR / "_index.json").write_text(
            json.dumps(_SCREENSHOT_INDEX, indent=2))
    if _EVIDENCE_INDEX:
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        (EVIDENCE_DIR / "_index.json").write_text(
            json.dumps(_EVIDENCE_INDEX, indent=2))
