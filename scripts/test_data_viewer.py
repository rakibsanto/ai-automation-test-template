"""
Test-Data Viewer — renders an expandable section in the master report
showing every distinct test-data input the run exercised.

Two data sources are merged:
  1. reports/test_data_log.json — AI Test Agent emits per-spec/per-type
     test counts + test_data samples (from `# TEST_DATA: ...` comments).
  2. consolidate_reports._testdata() — AST extracts literal arguments
     to fill()/type()/select_option() and constants like TEST_PHONE.

The viewer groups by spec, then by test type, and lists all distinct
data values used. Click-to-expand keeps the report tidy when there's
a lot of data.
"""
from __future__ import annotations
import json
from collections import defaultdict
from pathlib import Path

REPORTS_DIR = Path(__file__).parent.parent / "reports"


def _esc(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _load_test_data_log() -> dict:
    p = REPORTS_DIR / "test_data_log.json"
    if not p.exists():
        # Try inside any sub-artifact directory
        for nested in REPORTS_DIR.rglob("test_data_log.json"):
            try:
                return json.loads(nested.read_text(encoding="utf-8"))
            except Exception:
                continue
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def render_test_data_section(extra_test_data: dict[str, str] | None = None) -> str:
    """Render the test-data viewer HTML.

    extra_test_data: optional {function_name: 'TEST_PHONE · fill("..")'}
    map from consolidate's _testdata() — augments the AI agent's log
    with source-extracted data so non-parametrised tests also show up.
    Returns "" when there's nothing to show."""
    extra_test_data = extra_test_data or {}
    log = _load_test_data_log()
    specs = log.get("specs", {})

    if not specs and not extra_test_data:
        return ""

    # Build per-spec rows. For each spec we have types → test_data.
    spec_rows = []
    total_unique_inputs = 0
    for spec_name, spec_info in sorted(specs.items()):
        types = spec_info.get("types", {})
        if not types:
            continue
        type_blocks = []
        spec_input_count = 0
        for type_name, type_info in sorted(types.items()):
            test_data = type_info.get("test_data", [])
            test_count = type_info.get("test_count", 0)
            tests = type_info.get("tests", [])
            # De-dup test_data entries
            seen, unique_data = set(), []
            for td in test_data:
                td_s = str(td)
                if td_s and td_s not in seen:
                    seen.add(td_s)
                    unique_data.append(td_s)
            spec_input_count += len(unique_data)
            data_html = ""
            if unique_data:
                items = "".join(f'<li><code>{_esc(d)}</code></li>'
                                 for d in unique_data[:30])
                data_html = f'<ul class="td-data-list">{items}</ul>'
                if len(unique_data) > 30:
                    data_html += (f'<div class="td-truncated">'
                                  f'+ {len(unique_data) - 30} more</div>')
            else:
                # No test_data comments — show test names + extra source-data
                src_lines = []
                for t in tests[:8]:
                    src = extra_test_data.get(t, "")
                    if src:
                        src_lines.append(f'<li><code>{_esc(t)}</code>: '
                                          f'<span class="td-src">{_esc(src)}</span></li>')
                if src_lines:
                    data_html = f'<ul class="td-data-list">{"".join(src_lines)}</ul>'
                else:
                    data_html = ('<div class="td-empty">No explicit test data — '
                                 'tests use only the URL or assertion-only checks</div>')

            type_blocks.append(f"""
<details class="td-type-row">
  <summary>
    <span class="td-type-name">{_esc(type_name)}</span>
    <span class="td-count">{test_count} test(s)</span>
    <span class="td-data-count">{len(unique_data)} input(s)</span>
  </summary>
  <div class="td-type-body">{data_html}</div>
</details>""")

        total_unique_inputs += spec_input_count
        spec_rows.append(f"""
<details class="td-spec-row">
  <summary>
    <span class="td-spec-name">📄 {_esc(spec_name)}</span>
    <span class="td-count">{spec_info.get('total_tests', 0)} test(s)</span>
    <span class="td-data-count">{spec_input_count} input(s)</span>
  </summary>
  <div class="td-spec-body">
    <div class="td-help">Click any test type below to see the actual data values fed in.</div>
    {''.join(type_blocks)}
  </div>
</details>""")

    if not spec_rows:
        return ""

    # Topline stats
    total_specs = len(spec_rows)
    return f"""
<div class="td-summary" id="test-data">
  <div class="sec-title" style="margin:24px 0 12px">
    🧪 Test Data Used <span class="count">{total_specs} spec(s) · {total_unique_inputs} unique input(s)</span>
  </div>
  <div class="td-headline">
    Every distinct value the suite fed into the app — phone numbers,
    OTPs, XSS payloads, search strings, viewport sizes, etc. Click any
    spec to expand and see the inputs per test type.
  </div>
  <div class="td-list">{"".join(spec_rows)}</div>
</div>"""
