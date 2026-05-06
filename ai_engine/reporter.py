"""
Generates a fully self-contained HTML bug report.
All screenshots are embedded as base64 — one file, ready to email to the dev team.
"""

import ast, json, re
from pathlib import Path
from datetime import datetime

REPORTS_DIR = Path("reports")

# ─────────────────────────────────────────────────────────────────────────────
# HTML skeleton
# ─────────────────────────────────────────────────────────────────────────────

_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Fagun QA Bug Report — {run_date}</title>
<style>
/* ── Reset & base ── */
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --bg:#0d1117;--surface:#161b22;--border:#30363d;--text:#e6edf3;
  --muted:#8b949e;--c-critical:#f85149;--c-high:#f0883e;
  --c-medium:#e3b341;--c-low:#58a6ff;--c-pass:#3fb950;
  --c-critical-bg:#3d0e0e;--c-high-bg:#3d1e0e;
  --c-medium-bg:#3d2e0e;--c-low-bg:#0e1e3d;
  --c-pass-bg:#0e2d1a;--radius:10px;--font:'Inter',system-ui,sans-serif
}}
html{{scroll-behavior:smooth}}
body{{background:var(--bg);color:var(--text);font-family:var(--font);
     font-size:14px;line-height:1.6;padding:0}}
a{{color:var(--c-low);text-decoration:none}}
a:hover{{text-decoration:underline}}
code,pre{{font-family:'JetBrains Mono','Fira Code',monospace;font-size:12px}}
pre{{background:#0d1117;border:1px solid var(--border);border-radius:6px;
    padding:12px;overflow-x:auto;white-space:pre-wrap;word-break:break-word}}

/* ── Layout ── */
.wrap{{max-width:1100px;margin:0 auto;padding:24px 20px}}

/* ── Header ── */
.hdr{{background:linear-gradient(135deg,#1c2333 0%,#161b22 100%);
     border-bottom:1px solid var(--border);padding:28px 0;margin-bottom:32px}}
.hdr-inner{{max-width:1100px;margin:0 auto;padding:0 20px;
           display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:16px}}
.hdr-left h1{{font-size:22px;font-weight:700;letter-spacing:-0.3px}}
.hdr-left h1 span{{color:var(--c-critical);}}
.hdr-meta{{display:flex;flex-direction:column;gap:4px;font-size:12px;color:var(--muted);text-align:right}}
.hdr-meta b{{color:var(--text)}}
.print-btn{{background:#21262d;border:1px solid var(--border);color:var(--text);
           padding:8px 16px;border-radius:6px;cursor:pointer;font-size:13px;
           transition:background .15s}}
.print-btn:hover{{background:#30363d}}

/* ── Stats bar ── */
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;
       margin-bottom:36px}}
.stat{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);
      padding:18px 16px}}
.stat .label{{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.6px;margin-bottom:8px}}
.stat .val{{font-size:34px;font-weight:700;line-height:1}}
.stat.critical .val{{color:var(--c-critical)}}
.stat.high     .val{{color:var(--c-high)}}
.stat.medium   .val{{color:var(--c-medium)}}
.stat.low      .val{{color:var(--c-low)}}
.stat.pass     .val{{color:var(--c-pass)}}
.stat.fail     .val{{color:var(--c-critical)}}
.stat.total    .val{{color:#a371f7}}

/* ── Section titles ── */
.sec-title{{font-size:16px;font-weight:600;border-bottom:1px solid var(--border);
           padding-bottom:10px;margin:40px 0 20px}}
.sec-title .count{{background:var(--border);color:var(--muted);
                  font-size:11px;padding:2px 8px;border-radius:99px;margin-left:8px;font-weight:400}}

/* ── Severity badge ── */
.badge{{display:inline-block;padding:3px 10px;border-radius:99px;font-size:11px;
       font-weight:600;letter-spacing:.4px;text-transform:uppercase}}
.badge.CRITICAL{{background:var(--c-critical-bg);color:var(--c-critical);border:1px solid var(--c-critical)}}
.badge.HIGH    {{background:var(--c-high-bg);    color:var(--c-high);    border:1px solid var(--c-high)}}
.badge.MEDIUM  {{background:var(--c-medium-bg);  color:var(--c-medium);  border:1px solid var(--c-medium)}}
.badge.LOW     {{background:var(--c-low-bg);     color:var(--c-low);     border:1px solid var(--c-low)}}
.badge.PASS    {{background:var(--c-pass-bg);    color:var(--c-pass);    border:1px solid var(--c-pass)}}
.badge.FAIL    {{background:var(--c-critical-bg);color:var(--c-critical);border:1px solid var(--c-critical)}}
.badge.gen-fail{{background:#3d2000;color:#fb923c;border:1px solid #fb923c}}
.badge.P0{{background:#450a0a;color:#fca5a5}}
.badge.P1{{background:#3d1a0a;color:#fdba74}}
.badge.P2{{background:#1a2e0a;color:#86efac}}
.badge.P3{{background:#0a1a2e;color:#93c5fd}}

/* ── Bug ticket card ── */
.bug-card{{background:var(--surface);border:1px solid var(--border);
          border-radius:var(--radius);margin-bottom:28px;overflow:hidden}}
.bug-card-hdr{{padding:16px 20px;display:flex;align-items:flex-start;
              justify-content:space-between;flex-wrap:wrap;gap:8px;
              border-bottom:1px solid var(--border)}}
.bug-card-hdr .left{{display:flex;align-items:center;gap:10px;flex-wrap:wrap}}
.bug-id{{font-size:12px;font-weight:700;color:var(--muted);
        font-family:monospace;background:#0d1117;border:1px solid var(--border);
        padding:2px 8px;border-radius:4px}}
.bug-title{{font-size:15px;font-weight:600;color:var(--text);margin-top:2px}}
.bug-meta{{font-size:12px;color:var(--muted);display:flex;gap:16px;flex-wrap:wrap;margin-top:6px}}
.bug-meta span{{display:flex;align-items:center;gap:4px}}
.bug-body{{padding:20px}}

/* ── Two-col grid ── */
.two-col{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px}}
@media(max-width:640px){{.two-col{{grid-template-columns:1fr}}}}

/* ── Info blocks ── */
.info-block{{border-radius:8px;padding:14px 16px}}
.info-block .ib-label{{font-size:11px;font-weight:600;text-transform:uppercase;
                      letter-spacing:.6px;margin-bottom:8px}}
.info-block.expected{{background:#0d2818;border-left:3px solid var(--c-pass)}}
.info-block.expected .ib-label{{color:var(--c-pass)}}
.info-block.actual  {{background:var(--c-critical-bg);border-left:3px solid var(--c-critical)}}
.info-block.actual .ib-label{{color:var(--c-critical)}}
.info-block.analysis{{background:#1c1a2e;border-left:3px solid #a371f7}}
.info-block.analysis .ib-label{{color:#a371f7}}
.info-block.fix     {{background:#0a2218;border-left:3px solid var(--c-pass)}}
.info-block.fix .ib-label{{color:var(--c-pass)}}
.info-block.rootcause{{background:#1c1200;border-left:3px solid var(--c-medium)}}
.info-block.rootcause .ib-label{{color:var(--c-medium)}}

/* ── Steps list ── */
ol.steps{{padding-left:20px;color:var(--text)}}
ol.steps li{{margin-bottom:5px}}

/* ── Screenshot ── */
.shot-wrap{{margin-top:16px}}
.shot-label{{font-size:11px;font-weight:600;text-transform:uppercase;
            letter-spacing:.6px;color:var(--muted);margin-bottom:8px;
            display:flex;align-items:center;gap:6px}}
.shot-label::before{{content:"📸"}}
.screenshot{{width:100%;border:1px solid var(--border);border-radius:8px;
            cursor:zoom-in;transition:opacity .2s}}
.screenshot:hover{{opacity:.9}}
.no-shot{{background:#0d1117;border:1px dashed var(--border);border-radius:8px;
         padding:20px;text-align:center;color:var(--muted);font-size:12px}}

/* ── Error/traceback collapsible ── */
.err-toggle{{width:100%;background:#0d1117;border:1px solid var(--border);
            border-radius:6px;padding:10px 14px;color:var(--c-critical);
            font-family:monospace;font-size:12px;cursor:pointer;text-align:left;
            display:flex;justify-content:space-between;align-items:center;
            margin-top:14px}}
.err-toggle:hover{{background:#161b22}}
.err-body{{display:none;margin-top:1px}}
.err-body.open{{display:block}}

/* ── Env strip ── */
.env-strip{{font-size:11px;color:var(--muted);display:flex;gap:16px;flex-wrap:wrap;
           margin-top:14px;padding-top:14px;border-top:1px solid var(--border)}}
.env-strip span{{display:flex;gap:4px}}
.env-strip b{{color:var(--text)}}

/* ── Results table ── */
table{{width:100%;border-collapse:collapse;background:var(--surface);
      border:1px solid var(--border);border-radius:var(--radius);overflow:hidden}}
th{{background:#0d1117;color:var(--muted);font-size:11px;text-transform:uppercase;
   letter-spacing:.5px;padding:10px 16px;text-align:left}}
td{{padding:10px 16px;border-top:1px solid var(--border);font-size:13px}}
tr:hover td{{background:#1c2333}}

/* ── Gaps block ── */
.gap-block{{background:var(--surface);border:1px solid var(--border);
           border-radius:var(--radius);padding:20px;margin-bottom:20px}}
.gap-block h3{{color:#a371f7;font-size:14px;margin-bottom:12px}}
.gap-block p,.gap-block li{{color:var(--muted);font-size:13px;margin-bottom:4px}}

/* ── Evidence panels ── */
.ev-toggle{{width:100%;background:#0a1628;border:1px solid var(--border);border-radius:6px;
           padding:9px 14px;color:var(--c-low);font-family:monospace;font-size:12px;
           cursor:pointer;text-align:left;display:flex;justify-content:space-between;
           align-items:center;margin-top:10px}}
.ev-toggle:hover{{background:#0e1e38}}
.ev-body{{display:none;margin-top:1px}}
.ev-body.open{{display:block}}
.ev-table{{width:100%;border-collapse:collapse;font-size:11px;margin-top:4px}}
.ev-table th{{background:#0d1117;color:var(--muted);padding:5px 10px;text-align:left;font-weight:600}}
.ev-table td{{padding:4px 10px;border-top:1px solid #21262d;color:var(--text);
             word-break:break-all;max-width:400px}}
.ev-table tr:nth-child(even) td{{background:#0d1117}}
.perf-grid{{display:flex;gap:16px;flex-wrap:wrap;margin-top:4px}}
.perf-stat{{background:#0d1117;border:1px solid var(--border);border-radius:6px;
           padding:10px 16px;min-width:120px;text-align:center}}
.perf-stat .pval{{font-size:22px;font-weight:700;color:var(--c-low)}}
.perf-stat .plbl{{font-size:10px;color:var(--muted);text-transform:uppercase;
                 letter-spacing:.5px;margin-top:4px}}
.pval.warn{{color:var(--c-medium)}}
.pval.bad{{color:var(--c-critical)}}

/* ── Per-spec test detail blocks ── */
.spec-blk{{background:var(--surface);border:1px solid var(--border);
          border-radius:var(--radius);margin-bottom:16px;overflow:hidden}}
.spec-blk-hdr{{padding:14px 20px;display:flex;align-items:center;
              justify-content:space-between;cursor:pointer;user-select:none}}
.spec-blk-hdr:hover{{background:#1c2333}}
.spec-blk-title{{font-size:14px;font-weight:600;display:flex;align-items:center;gap:10px}}
.spec-blk-toggle{{font-size:12px;color:var(--muted)}}
.spec-blk-body{{display:none}}
.spec-blk-body.open{{display:block}}
.test-table{{width:100%;border-collapse:collapse;font-size:12px}}
.test-table th{{background:#0d1117;color:var(--muted);font-size:10px;
               text-transform:uppercase;letter-spacing:.5px;padding:8px 14px;text-align:left}}
.test-table td{{padding:9px 14px;border-top:1px solid var(--border);vertical-align:top}}
.test-table tr:hover td{{background:#1c2333}}
.test-row-pass td:first-child{{border-left:3px solid var(--c-pass)}}
.test-row-fail td:first-child{{border-left:3px solid var(--c-critical)}}
.test-row-skip td:first-child{{border-left:3px solid var(--muted)}}
.tname{{font-family:monospace;color:var(--c-low);font-size:12px}}
.tname-title{{color:var(--text);font-weight:500;margin-bottom:2px}}
.twhat{{color:var(--muted);font-size:12px}}
.tdata{{font-family:monospace;color:#a371f7;font-size:11px}}
.tdata-empty{{color:var(--muted);font-size:11px;font-style:italic}}

.console-err{{background:var(--c-critical-bg);border-left:3px solid var(--c-critical);
             padding:6px 10px;border-radius:4px;margin-bottom:4px;font-size:11px;
             font-family:monospace;color:var(--c-critical)}}
.console-warn{{background:var(--c-medium-bg);border-left:3px solid var(--c-medium);
              padding:6px 10px;border-radius:4px;margin-bottom:4px;font-size:11px;
              font-family:monospace;color:var(--c-medium)}}

/* ── Lightbox ── */
#lb{{display:none;position:fixed;inset:0;background:rgba(0,0,0,.9);
    z-index:1000;cursor:zoom-out;justify-content:center;align-items:center}}
#lb.show{{display:flex}}
#lb img{{max-width:95vw;max-height:92vh;border-radius:8px;border:2px solid var(--border)}}

/* ── Print ── */
@media print{{
  .hdr-meta .print-btn,.err-toggle{{display:none}}
  .err-body{{display:block!important}}
  body{{background:#fff;color:#000}}
  .bug-card{{border:1px solid #ccc;break-inside:avoid}}
}}
</style>
</head>
<body>

<!-- Lightbox -->
<div id="lb" onclick="this.classList.remove('show')">
  <img id="lb-img" src="" alt="Screenshot"/>
</div>

<!-- Header -->
<div class="hdr">
  <div class="hdr-inner">
    <div class="hdr-left">
      <h1>Fagun <span>QA</span> Bug Report</h1>
      <div style="font-size:13px;color:var(--muted);margin-top:4px">
        AI-generated · autonomous · intent-based testing
      </div>
    </div>
    <div class="hdr-meta">
      <div><b>Date:</b> {run_date}</div>
      <div><b>Target:</b> {base_url}</div>
      <div><b>AI Model:</b> {model} (local · no API key)</div>
      <div><b>Browser:</b> Chromium (headless)</div>
      <button class="print-btn" onclick="window.print()">Print / Save PDF</button>
    </div>
  </div>
</div>

<div class="wrap">

<!-- Stats -->
<div class="stats">
  <div class="stat critical"><div class="label">Critical</div><div class="val">{cnt_critical}</div></div>
  <div class="stat high">    <div class="label">High</div>    <div class="val">{cnt_high}</div></div>
  <div class="stat medium">  <div class="label">Medium</div>  <div class="val">{cnt_medium}</div></div>
  <div class="stat low">     <div class="label">Low</div>     <div class="val">{cnt_low}</div></div>
  <div class="stat pass">    <div class="label">Passed</div>  <div class="val">{total_passed}</div></div>
  <div class="stat fail">    <div class="label">Failed</div>  <div class="val">{total_failed}</div></div>
  <div class="stat total">   <div class="label">Total Tests</div><div class="val">{total_tests}</div></div>
</div>

<!-- Bug Tickets -->
<div class="sec-title">
  Bug Tickets <span class="count">{total_bugs}</span>
</div>

{bug_tickets_html}

<!-- Summary Table -->
<div class="sec-title">All Test Results</div>
<table>
  <thead>
    <tr>
      <th>Page</th><th>Status</th><th>Passed</th><th>Failed</th><th>Total</th><th>Bugs</th>
    </tr>
  </thead>
  <tbody>
    {results_rows}
  </tbody>
</table>

<!-- Per-Spec Test Details -->
<div class="sec-title" style="margin-top:40px">
  Per-Test Breakdown
  <span class="count">title · what was tested · test data used</span>
</div>
{spec_details_html}

<!-- Coverage Gaps -->
<div class="sec-title" style="margin-top:40px">Coverage Gaps <span class="count">AI Analysis</span></div>
{gaps_html}

<!-- Footer -->
<div style="text-align:center;color:var(--muted);font-size:12px;margin-top:60px;padding-top:20px;border-top:1px solid var(--border)">
  Fagun Autonomous Testing &nbsp;·&nbsp; Powered by Ollama + Playwright + pytest &nbsp;·&nbsp; Zero API keys
</div>

</div><!-- /wrap -->

<script>
function toggleSpec(id){{
  var body=document.getElementById(id);
  var btn=body.previousElementSibling;
  var arrow=btn.querySelector('.spec-blk-toggle');
  if(body.classList.contains('open')){{
    body.classList.remove('open');arrow.textContent='▶ Show tests';
  }}else{{
    body.classList.add('open');arrow.textContent='▼ Hide tests';
  }}
}}
function toggleErr(id){{
  var el=document.getElementById(id);
  var btn=el.previousElementSibling;
  if(el.classList.contains('open')){{el.classList.remove('open');btn.querySelector('span').textContent='▶ Show error details';}}
  else{{el.classList.add('open');btn.querySelector('span').textContent='▼ Hide error details';}}
}}
function toggleEv(id){{
  var el=document.getElementById(id);
  var btn=el.previousElementSibling;
  var arrow=btn.querySelectorAll('span')[1];
  if(el.classList.contains('open')){{el.classList.remove('open');arrow.textContent='▶ Show';}}
  else{{el.classList.add('open');arrow.textContent='▼ Hide';}}
}}
function openShot(src){{document.getElementById('lb-img').src=src;document.getElementById('lb').classList.add('show');}}
document.addEventListener('keydown',function(e){{if(e.key==='Escape')document.getElementById('lb').classList.remove('show');}});
</script>
</body>
</html>"""


# ─────────────────────────────────────────────────────────────────────────────
# Bug ticket HTML template
# ─────────────────────────────────────────────────────────────────────────────

def _bug_ticket(bug: dict, idx: int) -> str:
    sev   = bug.get("severity", "MEDIUM")
    pri   = bug.get("priority", "P2")
    title = bug.get("title", "Untitled Bug")
    test  = bug.get("test_name", "")
    url   = bug.get("page_url", "")
    ts    = bug.get("timestamp", "")[:19].replace("T", " ")
    dur   = bug.get("duration", "")
    desc  = bug.get("description", "")
    steps = bug.get("steps", [])
    exp   = bug.get("expected", "")
    act   = bug.get("actual", "")
    root  = bug.get("root_cause", "")
    fix   = bug.get("suggested_fix", "")
    err   = _esc(bug.get("error_message", ""))
    tb    = _esc(bug.get("traceback", ""))
    shot  = bug.get("screenshot_b64", "")
    bug_id= bug.get("id", f"BUG-{idx:03d}")
    env_b = bug.get("browser", "Chromium")
    env_v = bug.get("viewport", "1280×720")
    env_e = bug.get("env", "Staging")

    # Steps list
    steps_html = ""
    if steps:
        items = "".join(f"<li>{_esc(s)}</li>" for s in steps)
        steps_html = f"""
<div style="margin-bottom:16px">
  <div style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.6px;
              color:var(--muted);margin-bottom:8px">Steps to Reproduce</div>
  <ol class="steps">{items}</ol>
</div>"""

    # Expected / Actual
    exp_act = f"""
<div class="two-col">
  <div class="info-block expected">
    <div class="ib-label">Expected Behavior</div>
    <div>{_esc(exp) or "<em style='color:var(--muted)'>Not specified</em>"}</div>
  </div>
  <div class="info-block actual">
    <div class="ib-label">Actual Behavior (Bug)</div>
    <div>{_esc(act) or "<em style='color:var(--muted)'>See error below</em>"}</div>
  </div>
</div>"""

    # Screenshot / POC
    if shot:
        shot_html = f"""
<div class="shot-wrap">
  <div class="shot-label">Proof of Concept — Screenshot</div>
  <img class="screenshot" src="{shot}" alt="Test failure screenshot"
       onclick="openShot(this.src)" title="Click to enlarge"/>
</div>"""
    else:
        shot_html = """
<div class="shot-wrap">
  <div class="shot-label">Proof of Concept — Screenshot</div>
  <div class="no-shot">No screenshot captured (test may have failed before page loaded)</div>
</div>"""

    # Error collapsible
    err_id = f"err-{idx}"
    if err or tb:
        err_section = f"""
<button class="err-toggle" onclick="toggleErr('{err_id}')">
  <span>▶ Show error details</span>
  <span style="font-size:11px;color:var(--muted)">AssertionError / Traceback</span>
</button>
<div class="err-body" id="{err_id}">
  <pre style="margin-top:8px"><strong style="color:var(--c-critical)">{err}</strong>

{tb}</pre>
</div>"""
    else:
        err_section = ""

    # ── Evidence panels ──────────────────────────────────────────────────────
    ev_html = ""
    ev_idx = idx  # reuse the ticket index as panel id

    # Performance panel
    perf = bug.get("performance", {})
    if perf:
        def _perf_class(ms, warn=1500, bad=3000):
            if ms >= bad:  return "pval bad"
            if ms >= warn: return "pval warn"
            return "pval"
        dom_ms  = perf.get("dom_load_ms",  0)
        load_ms = perf.get("page_load_ms", 0)
        ttfb_ms = perf.get("ttfb_ms",      0)
        ev_html += f"""
<button class="ev-toggle" onclick="toggleEv('perf-{ev_idx}')">
  <span>⚡ Performance Timing</span>
  <span style="font-size:11px;color:var(--muted)">▶ Show</span>
</button>
<div class="ev-body" id="perf-{ev_idx}">
  <div class="perf-grid" style="margin:8px 0">
    <div class="perf-stat"><div class="{_perf_class(ttfb_ms,300,1000)}">{ttfb_ms}ms</div>
      <div class="plbl">TTFB</div></div>
    <div class="perf-stat"><div class="{_perf_class(dom_ms)}">{dom_ms}ms</div>
      <div class="plbl">DOM Ready</div></div>
    <div class="perf-stat"><div class="{_perf_class(load_ms,2000,4000)}">{load_ms}ms</div>
      <div class="plbl">Page Load</div></div>
  </div>
</div>"""

    # Console errors panel
    errs = bug.get("error_log", [])
    if errs:
        items = "".join(
            f'<div class="console-{e.get("type","error")}">'
            f'<b>{_esc(e.get("type","").upper())}:</b> {_esc(e.get("text","")[:200])}</div>'
            for e in errs[:10]
        )
        ev_html += f"""
<button class="ev-toggle" onclick="toggleEv('console-{ev_idx}')" style="border-color:var(--c-critical);color:var(--c-critical)">
  <span>🔴 Console Errors ({len(errs)})</span>
  <span style="font-size:11px;color:var(--muted)">▶ Show</span>
</button>
<div class="ev-body" id="console-{ev_idx}">
  <div style="margin:8px 0">{items}</div>
</div>"""

    # Network log panel (show only API calls)
    net_log = [n for n in bug.get("network_log", []) if "/api/" in n.get("url","")]
    if net_log:
        rows = "".join(
            f'<tr><td>{_esc(n.get("method",""))}</td>'
            f'<td style="color:{"var(--c-pass)" if 200<=n.get("status",0)<300 else "var(--c-critical)"}"">'
            f'{n.get("status","")}</td>'
            f'<td>{_esc(n.get("url","")[-80:])}</td></tr>'
            for n in net_log[:15] if n.get("type") == "response"
        )
        if rows:
            ev_html += f"""
<button class="ev-toggle" onclick="toggleEv('net-{ev_idx}')">
  <span>🌐 Network Log ({len(net_log)} API calls)</span>
  <span style="font-size:11px;color:var(--muted)">▶ Show</span>
</button>
<div class="ev-body" id="net-{ev_idx}">
  <table class="ev-table" style="margin:8px 0">
    <thead><tr><th>Method</th><th>Status</th><th>URL</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</div>"""

    # Root cause + fix
    analysis_fix = ""
    if root:
        analysis_fix += f"""
<div class="info-block rootcause" style="margin-bottom:12px">
  <div class="ib-label">Root Cause Analysis (AI)</div>
  <div>{_esc(root)}</div>
</div>"""
    if fix:
        analysis_fix += f"""
<div class="info-block fix">
  <div class="ib-label">Suggested Fix for Developer</div>
  <div>{_esc(fix)}</div>
</div>"""

    # Description
    desc_html = f"""
<div class="info-block analysis" style="margin-bottom:16px">
  <div class="ib-label">Description</div>
  <div>{_esc(desc) or "<em style='color:var(--muted)'>See error details below</em>"}</div>
</div>""" if desc else ""

    return f"""
<div class="bug-card" id="{bug_id}">
  <div class="bug-card-hdr">
    <div>
      <div class="left">
        <span class="bug-id">{bug_id}</span>
        <span class="badge {sev}">{sev}</span>
        <span class="badge {pri}">{pri}</span>
      </div>
      <div class="bug-title">{_esc(title)}</div>
      <div class="bug-meta">
        <span>🔗 <a href="{_esc(url)}" target="_blank">{_esc(url)}</a></span>
        <span>🧪 <code>{_esc(test)}</code></span>
        <span>🕐 {ts}</span>
        {'<span>⏱ ' + dur + '</span>' if dur else ''}
      </div>
    </div>
  </div>
  <div class="bug-body">
    {desc_html}
    {steps_html}
    {exp_act}
    {shot_html}
    {err_section}
    {ev_html}
    <div style="margin-top:16px">{analysis_fix}</div>
    <div class="env-strip">
      <span><b>Browser:</b> {env_b}</span>
      <span><b>Viewport:</b> {env_v}</span>
      <span><b>Env:</b> {env_e}</span>
      <span><b>Spec:</b> <a href="{_esc(url)}" target="_blank">View page</a></span>
    </div>
  </div>
</div>"""


# ─────────────────────────────────────────────────────────────────────────────
# Results row
# ─────────────────────────────────────────────────────────────────────────────

def _result_row(name: str, r: dict) -> str:
    status = r.get("status", "unknown")
    bugs   = r.get("bugs", [])
    if status == "generation_failed":
        badge = '<span class="badge gen-fail">GEN FAILED</span>'
    elif r.get("failed", 1) == 0:
        badge = '<span class="badge PASS">PASSED</span>'
    else:
        badge = '<span class="badge FAIL">FAILED</span>'

    bug_links = " ".join(
        f'<a href="#{b["id"]}" class="badge {b["severity"]}">{b["id"]}</a>'
        for b in bugs
    )

    return f"""<tr>
      <td><strong>{_esc(name)}</strong></td>
      <td>{badge}</td>
      <td style="color:var(--c-pass)">{r.get('passed', 0)}</td>
      <td style="color:var(--c-critical)">{r.get('failed', 0)}</td>
      <td>{r.get('total', 0)}</td>
      <td>{bug_links or '<span style="color:var(--muted)">—</span>'}</td>
    </tr>"""


# ─────────────────────────────────────────────────────────────────────────────
# Gaps HTML
# ─────────────────────────────────────────────────────────────────────────────

def _gaps_block(name: str, gaps: str) -> str:
    if not gaps:
        return ""
    lines = [f"<p>{_esc(l.strip())}</p>" if l.strip() else "" for l in gaps.splitlines()]
    return f"""<div class="gap-block">
  <h3>{_esc(name.replace('-', ' ').title())}</h3>
  {''.join(lines)}
</div>"""


# ─────────────────────────────────────────────────────────────────────────────
# HTML escape
# ─────────────────────────────────────────────────────────────────────────────

def _esc(s: str) -> str:
    if not s:
        return ""
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;"))


# ─────────────────────────────────────────────────────────────────────────────
# Per-spec test detail helpers
# ─────────────────────────────────────────────────────────────────────────────

def _parse_test_file(path: Path) -> dict:
    """Return {fn_name: {title, docstring, test_data}} by AST-parsing the generated test file."""
    info = {}
    if not path.exists():
        return info
    try:
        source = path.read_text(encoding="utf-8")
        tree   = ast.parse(source)
        lines  = source.splitlines()
        for node in ast.walk(tree):
            if not (isinstance(node, ast.FunctionDef) and node.name.startswith("test_")):
                continue
            doc   = ast.get_docstring(node) or ""
            # Scan first 8 lines of function body for a TEST_DATA comment
            data  = ""
            for ln in range(node.lineno, min(node.lineno + 8, len(lines))):
                if "# TEST_DATA:" in lines[ln]:
                    data = lines[ln].split("# TEST_DATA:", 1)[-1].strip()
                    break
            # Human title: strip "test_" prefix + spec slug prefix, title-case
            raw_title = node.name[5:]  # remove leading "test_"
            title = raw_title.replace("_", " ").title()
            info[node.name] = {"title": title, "docstring": doc, "test_data": data}
    except Exception:
        pass
    return info


def _load_pytest_outcomes(json_report_path: str | None) -> dict:
    """Return {fn_name: outcome} from a pytest JSON report file."""
    outcomes = {}
    if not json_report_path:
        return outcomes
    p = Path(json_report_path)
    if not p.exists():
        return outcomes
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        for t in data.get("tests", []):
            nodeid  = t.get("nodeid", "")
            fn_name = nodeid.split("::")[-1].split("[")[0]
            outcomes[fn_name] = t.get("outcome", "unknown")
    except Exception:
        pass
    return outcomes


def _outcome_badge(outcome: str) -> str:
    mapping = {
        "passed":  ('<span class="badge PASS">PASS</span>',  "test-row-pass"),
        "failed":  ('<span class="badge FAIL">FAIL</span>',  "test-row-fail"),
        "error":   ('<span class="badge FAIL">ERROR</span>', "test-row-fail"),
        "skipped": ('<span style="color:var(--muted)">⏭ SKIP</span>', "test-row-skip"),
    }
    return mapping.get(outcome, (f'<span style="color:var(--muted)">— {_esc(outcome)}</span>', ""))


def _spec_detail_block(spec_name: str, result: dict, block_idx: int) -> str:
    """Build a collapsible per-spec table showing every test with title, description, data."""
    json_report = result.get("json_report")
    outcomes    = _load_pytest_outcomes(json_report)

    tests_dir  = Path("tests")
    test_file  = tests_dir / f"test_{spec_name.replace('-', '_')}.py"
    test_info  = _parse_test_file(test_file)

    # Merge: all known test names from either source
    all_names = list(dict.fromkeys(list(test_info.keys()) + list(outcomes.keys())))

    if not all_names:
        return ""

    total   = len(all_names)
    passed  = sum(1 for n in all_names if outcomes.get(n) == "passed")
    failed  = total - passed
    icon    = "✅" if failed == 0 else "❌"
    body_id = f"spec-detail-{block_idx}"

    rows = []
    for fn in all_names:
        outcome  = outcomes.get(fn, "unknown")
        badge, row_cls = _outcome_badge(outcome)
        info     = test_info.get(fn, {})
        title    = _esc(info.get("title", fn.replace("_", " ").title()))
        raw_fn   = _esc(fn)
        docstring= _esc(info.get("docstring", ""))
        tdata    = info.get("test_data", "")

        what_cell = (
            f'<div class="tname-title">{title}</div>'
            f'<div class="twhat">{docstring}</div>'
            if docstring else
            f'<div class="tname-title">{title}</div>'
        )
        data_cell = (
            f'<span class="tdata">{_esc(tdata)}</span>'
            if tdata else
            '<span class="tdata-empty">—</span>'
        )

        rows.append(f"""<tr class="{row_cls}">
          <td>{badge}</td>
          <td><span class="tname">{raw_fn}</span></td>
          <td>{what_cell}</td>
          <td>{data_cell}</td>
        </tr>""")

    rows_html = "\n".join(rows)
    label = f"{icon} <code>{_esc(spec_name)}</code> — {passed} passed / {failed} failed / {total} total"

    return f"""
<div class="spec-blk">
  <div class="spec-blk-hdr" onclick="toggleSpec('{body_id}')">
    <span class="spec-blk-title">{label}</span>
    <span class="spec-blk-toggle">▶ Show tests</span>
  </div>
  <div class="spec-blk-body" id="{body_id}">
    <table class="test-table">
      <thead>
        <tr>
          <th style="width:80px">Status</th>
          <th style="width:260px">Test Function</th>
          <th>What It Tested</th>
          <th style="width:280px">Test Data Used</th>
        </tr>
      </thead>
      <tbody>
        {rows_html}
      </tbody>
    </table>
  </div>
</div>"""


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def generate_report(all_results: dict, base_url: str, model: str) -> Path:
    all_bugs = [b for r in all_results.values() for b in r.get("bugs", [])]

    total_passed = sum(r.get("passed", 0) for r in all_results.values())
    total_failed = sum(r.get("failed", 0) for r in all_results.values())
    total_tests  = sum(r.get("total",  0) for r in all_results.values())

    cnt = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for b in all_bugs:
        sev = b.get("severity", "MEDIUM").upper()
        cnt[sev] = cnt.get(sev, 0) + 1

    bug_tickets_html = "".join(
        _bug_ticket(b, i + 1) for i, b in enumerate(all_bugs)
    ) or '<p style="color:var(--muted);text-align:center;padding:24px">No bugs detected — all tests passed.</p>'

    results_rows = "".join(_result_row(name, r) for name, r in all_results.items())

    spec_details_html = "".join(
        _spec_detail_block(name, r, i)
        for i, (name, r) in enumerate(all_results.items())
    ) or '<p style="color:var(--muted)">No test detail data available.</p>'

    gaps_html = "".join(
        _gaps_block(name, r.get("gaps", ""))
        for name, r in all_results.items()
    ) or '<p style="color:var(--muted)">No gap analysis available.</p>'

    html = _PAGE.format(
        run_date     = datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        base_url     = _esc(base_url),
        model        = _esc(model),
        cnt_critical = cnt["CRITICAL"],
        cnt_high     = cnt["HIGH"],
        cnt_medium   = cnt["MEDIUM"],
        cnt_low      = cnt["LOW"],
        total_passed = total_passed,
        total_failed = total_failed,
        total_tests  = total_tests,
        total_bugs       = len(all_bugs),
        bug_tickets_html = bug_tickets_html,
        results_rows     = results_rows,
        spec_details_html= spec_details_html,
        gaps_html        = gaps_html,
    )

    REPORTS_DIR.mkdir(exist_ok=True)
    out = REPORTS_DIR / "bug-report.html"
    out.write_text(html, encoding="utf-8")
    return out
