"""
pytest configuration — evidence capture for every test.

On failure we capture:
  • Screenshot (annotated with a red banner showing the error message)
  • Screen recording (Playwright video — only kept for failed tests)
  • Network log, console log, performance timing
  • DOM snapshot of the page at failure time

All paths in _index.json are RELATIVE so consolidate-reports.py running
on a different runner can resolve them after artifact download.
"""

import os, re, json, shutil, sys, pytest
from pathlib import Path
from datetime import datetime

# Spec directive parser — honor "Don't test X" / "Skip Y" instructions
# the spec author writes inside the .md spec files.
sys.path.insert(0, str(Path(__file__).parent))
try:
    from ai_engine.spec_directives import (
        aggregate_directives, should_skip_test_name,
    )
    _DIRECTIVES_AVAILABLE = True
except ImportError:
    _DIRECTIVES_AVAILABLE = False

# ─── Optional: PIL is used to draw an error banner on the screenshot.
# If unavailable, we skip annotation but still save the raw screenshot.
try:
    from PIL import Image, ImageDraw, ImageFont
    _PIL_OK = True
except ImportError:
    _PIL_OK = False

# Set HEADED=1 (or --headed flag) to watch tests in a real browser window.
# Set SLOW_MO=800 to add millisecond delay between actions (default 800 in headed mode).
_HEADED  = os.getenv("HEADED",   "0").strip() in ("1", "true", "yes")
_SLOW_MO = int(os.getenv("SLOW_MO", "800" if _HEADED else "0"))

# Set CAPTURE_VIDEO=1 to record video for every test (CI does this by default).
_VIDEO_ON = os.getenv("CAPTURE_VIDEO", "1").strip() in ("1", "true", "yes")

# ── Directories (absolute so they exist regardless of CWD; paths in
#    `_index.json` are stored as REPO-RELATIVE strings so consolidate-runner
#    can resolve them post-artifact-download) ──────────────────────────────
_ROOT = Path(__file__).parent
SCREENSHOTS_DIR = _ROOT / "reports" / "screenshots"
EVIDENCE_DIR    = _ROOT / "reports" / "evidence"
VIDEOS_DIR      = _ROOT / "reports" / "videos"

# ── Global indexes written at session end ────────────────────────────────
_SCREENSHOT_INDEX: dict[str, dict] = {}
_EVIDENCE_INDEX:   dict[str, str]  = {}
_VIDEO_INDEX:      dict[str, str]  = {}     # nodeid → relative video path

# Per-test runtime state
_PRE_FAILURE_SNAP: dict[str, dict] = {}     # nodeid → {error, traceback}


# ─── Helpers ────────────────────────────────────────────────────────────────

def _rel_to_repo(path: Path) -> str:
    """Convert an absolute path to one relative to the repo root, with
    forward slashes — works on every CI runner regardless of cwd."""
    try:
        return str(Path(path).resolve().relative_to(_ROOT)).replace("\\", "/")
    except (ValueError, OSError):
        return str(path).replace("\\", "/")


def _annotate_screenshot(png_path: Path, banner_text: str) -> None:
    """Draw a red banner across the top of the screenshot showing the
    failure message, so anyone viewing the image sees the bug context.

    Skips silently if PIL is unavailable (the raw screenshot still works)."""
    if not _PIL_OK:
        return
    if not png_path.exists():
        return
    try:
        img = Image.open(png_path).convert("RGB")
        w, h = img.size
        banner_h = 90
        # Stretch the canvas downward by banner_h so the original image
        # is fully preserved underneath the banner.
        out = Image.new("RGB", (w, h + banner_h), (24, 14, 14))
        out.paste(img, (0, banner_h))

        draw = ImageDraw.Draw(out)
        # Red banner background
        draw.rectangle((0, 0, w, banner_h), fill=(190, 30, 30))
        # White stripe accent
        draw.rectangle((0, banner_h - 4, w, banner_h), fill=(255, 255, 255))

        # Try to load a system font; fall back to default
        font = None
        for font_path in (
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",  # macOS
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux
            "/Library/Fonts/Arial Bold.ttf",
        ):
            try:
                font = ImageFont.truetype(font_path, 22)
                break
            except (OSError, IOError):
                continue
        if font is None:
            font = ImageFont.load_default()

        # Word-wrap the banner text to two lines max
        text = banner_text.strip().replace("\n", " ")
        if len(text) > 200:
            text = text[:197] + "..."
        # Crude wrap at ~95 chars per line
        line_cap = 95
        if len(text) <= line_cap:
            lines = ["🐞 BUG CAPTURED — " + text]
        else:
            lines = [
                "🐞 BUG CAPTURED",
                text[: line_cap * 2],
            ]
        y = 12
        for line in lines[:2]:
            draw.text((16, y), line, fill=(255, 255, 255), font=font)
            y += 30

        out.save(png_path, "PNG", optimize=True)
    except Exception as e:
        # Annotation must never break the test run
        print(f"  [SCREENSHOT] Annotation skipped: {e}", flush=True)


# ─── Browser / context defaults ────────────────────────────────────────────

@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Per-session context args — enables video recording in 1280x720 size."""
    args = {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 720},
        "ignore_https_errors": True,
        "locale": "en-US",
    }
    if _VIDEO_ON:
        VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
        args["record_video_dir"] = str(VIDEOS_DIR)
        # MP4 container so reports can <video> tag-embed without conversion
        args["record_video_size"] = {"width": 1280, "height": 720}
    return args


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    return {
        **browser_type_launch_args,
        "headless": not _HEADED,    # HEADED=1 → open real browser window
        "slow_mo":  _SLOW_MO,       # SLOW_MO=800 → 800ms delay per action
    }


@pytest.fixture(autouse=True)
def _set_page_timeouts(request):
    """15-s default timeout on every page operation. Stops tests hanging on
    slow staging."""
    if "page" not in request.fixturenames:
        yield
        return
    page = request.getfixturevalue("page")
    page.set_default_timeout(15000)
    page.set_default_navigation_timeout(15000)
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
    _EVIDENCE_INDEX[request.node.nodeid] = _rel_to_repo(ev_path)


# ── Failure capture: screenshot + annotated banner + video preserve ──────────

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report  = outcome.get_result()

    if report.when != "call":
        return

    page = item.funcargs.get("page")
    if page is None:
        return

    nodeid = item.nodeid
    safe   = re.sub(r"[^\w\-]", "_", nodeid)[:120]

    # ─── On FAILURE: take screenshot, annotate, preserve video ─────────────
    if report.failed:
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        shot_path = SCREENSHOTS_DIR / f"{safe}.png"

        # Build a one-line failure summary for the screenshot banner.
        # Prefer lines starting with 'E ' (pytest's failure-detail prefix)
        # since they carry the actual assertion message rather than the
        # surrounding fixture/source-code lines pytest also prints.
        err_text = ""
        try:
            longrepr = str(report.longrepr or "")
            # Pass 1: look for E-prefixed lines (the real failure detail)
            for line in longrepr.splitlines():
                if not re.match(r"^E\s{1,3}", line):
                    continue
                s = re.sub(r"^E\s{1,3}", "", line).strip()
                if not s:
                    continue
                # Skip continuation lines like "+ where ..." / "assert ..."
                if s.startswith(("assert ", "+ ", "where ")):
                    continue
                # Skip pytest's "<class 'X'>" / "<Locator ...>" debug repr
                if s.startswith("<") and s.endswith(">"):
                    continue
                err_text = s
                break
            # Pass 2: fall back to the first non-source-snippet line
            if not err_text:
                for line in longrepr.splitlines():
                    s = line.strip()
                    if not s or s.startswith((">", ":", "/", "_")):
                        continue
                    if "=" in s and ("page" in s.lower() or "fixture" in s.lower()):
                        continue
                    err_text = s[:200]
                    break
            if not err_text:
                err_text = "test failed"
        except Exception:
            err_text = "test failed"

        # Take screenshot — try several strategies for resilience
        saved = False
        for kwargs in ({"full_page": True}, {"full_page": False}, {}):
            try:
                page.screenshot(path=str(shot_path), **kwargs)
                saved = True
                break
            except Exception:
                continue

        if saved:
            _annotate_screenshot(shot_path, err_text)
            _SCREENSHOT_INDEX[nodeid] = {
                "path":      _rel_to_repo(shot_path),
                "url":       getattr(page, "url", ""),
                "error":     err_text[:300],
                "timestamp": datetime.now().isoformat(),
            }
        else:
            print(f"  [SCREENSHOT] All attempts failed for {nodeid}", flush=True)

        # ─── Preserve video ─────────────────────────────────────────────
        # Playwright finalises the video file when the page closes. We
        # rename/copy the auto-generated file to a predictable name and
        # store a relative path in the video index.
        if _VIDEO_ON:
            try:
                video = page.video  # type: ignore[attr-defined]
                if video is not None:
                    raw_video_path = Path(video.path())
                    # The video file is finalised when the context closes;
                    # we record where it WILL be once playwright finishes.
                    target = VIDEOS_DIR / f"{safe}.webm"
                    _VIDEO_INDEX[nodeid] = _rel_to_repo(target)
                    # Stash the raw path so session-end can rename it
                    _VIDEO_INDEX[f"__pending__{nodeid}"] = str(raw_video_path)
            except Exception as e:
                print(f"  [VIDEO] Could not get video for {nodeid}: {e}", flush=True)


# ── Diagnostics ───────────────────────────────────────────────────────────────

def pytest_collection_modifyitems(config, items):
    """Honor 'Don't test X' / 'Skip Y' directives in any specs/*.md file.
    Applies a pytest.mark.skip to matching test items so they show up as
    SKIPPED in the report (with a clear reason) instead of PASSED."""
    if not _DIRECTIVES_AVAILABLE:
        return
    try:
        agg = aggregate_directives(Path(__file__).parent / "specs")
    except Exception as e:
        print(f"[DIRECTIVES] Could not load: {e}", flush=True)
        return
    if agg.empty():
        return
    print(f"[DIRECTIVES] Honoring {len(agg.raw_directives)} skip directive(s) "
          f"from spec files: types={sorted(agg.skip_test_types)}", flush=True)
    skipped = 0
    for item in items:
        # Match against the full nodeid + class name + method name combined
        # so 'TestQA10I18nAndRTL' triggers an 'i18n' skip directive even
        # when the test method itself is named test_qa10_arabic_*.
        haystack = item.nodeid
        cls = getattr(item, "cls", None)
        if cls is not None:
            haystack += " " + cls.__name__
        skip, reason = should_skip_test_name(agg, haystack)
        if skip:
            item.add_marker(pytest.mark.skip(reason=reason))
            skipped += 1
    if skipped:
        print(f"[DIRECTIVES] Auto-skipped {skipped} test(s) per spec directives", flush=True)


def pytest_collection_finish(session):
    n = len(session.items)
    print(f"[COLLECT] {n} test(s) found", flush=True)
    for item in session.items:
        print(f"  → {item.nodeid}", flush=True)


def pytest_internalerror(excrepr, excinfo):
    print(f"[PYTEST INTERNAL ERROR] {excinfo.value}", flush=True)


# ── Write indexes at session end ──────────────────────────────────────────────

def _finalise_videos() -> None:
    """Move/rename auto-generated playwright videos to predictable filenames.
    Delete videos for passed tests to save artifact size (CI quota matters)."""
    if not _VIDEO_ON or not VIDEOS_DIR.exists():
        return
    # 1. Move pending failure videos to their target name
    for key in list(_VIDEO_INDEX.keys()):
        if not key.startswith("__pending__"):
            continue
        nodeid = key.replace("__pending__", "", 1)
        raw_path = Path(_VIDEO_INDEX.pop(key))
        target_rel = _VIDEO_INDEX.get(nodeid)
        if not target_rel:
            continue
        target_abs = _ROOT / target_rel
        try:
            if raw_path.exists():
                target_abs.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(raw_path), str(target_abs))
            else:
                # Sometimes Playwright writes the video AFTER context close;
                # if it's not there yet, drop the index entry so the report
                # gracefully falls back to "no video".
                _VIDEO_INDEX.pop(nodeid, None)
        except Exception as e:
            print(f"  [VIDEO] move failed for {nodeid}: {e}", flush=True)
            _VIDEO_INDEX.pop(nodeid, None)

    # 2. Delete leftover videos that don't belong to any failure
    keep = set()
    for v_rel in _VIDEO_INDEX.values():
        keep.add((_ROOT / v_rel).resolve())
    for video in VIDEOS_DIR.rglob("*.webm"):
        if video.resolve() not in keep:
            try:
                video.unlink()
            except Exception:
                pass
    # Tidy empty per-test subdirs Playwright may have left behind
    for sub in VIDEOS_DIR.iterdir():
        if sub.is_dir():
            try:
                if not any(sub.iterdir()):
                    sub.rmdir()
            except Exception:
                pass


def pytest_sessionfinish(session, exitstatus):
    _finalise_videos()
    if _SCREENSHOT_INDEX:
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        (SCREENSHOTS_DIR / "_index.json").write_text(
            json.dumps(_SCREENSHOT_INDEX, indent=2))
    if _EVIDENCE_INDEX:
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        (EVIDENCE_DIR / "_index.json").write_text(
            json.dumps(_EVIDENCE_INDEX, indent=2))
    if _VIDEO_INDEX:
        VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
        (VIDEOS_DIR / "_index.json").write_text(
            json.dumps(_VIDEO_INDEX, indent=2))
