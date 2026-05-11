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
<title>Mehad QA Bug Report — {run_date}</title>
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
      padding:18px 16px;
      /* clickable stat cards */
      text-decoration:none;color:inherit;display:block;cursor:pointer;
      transition:transform .12s,border-color .12s,background .12s,box-shadow .12s}}
.stat:hover{{border-color:#58a6ff;background:#1c2333;
            transform:translateY(-2px);box-shadow:0 4px 16px rgba(88,166,255,.12)}}
.stat::after{{content:"→";position:absolute;opacity:0;transition:opacity .15s,transform .15s;
             right:14px;top:14px;color:#58a6ff;font-size:14px;font-weight:700}}
.stat{{position:relative}}
.stat:hover::after{{opacity:1;transform:translateX(2px)}}
.stat .label{{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.6px;margin-bottom:8px}}
.stat .val{{font-size:34px;font-weight:700;line-height:1}}
.stat.critical .val{{color:var(--c-critical)}}
.stat.high     .val{{color:var(--c-high)}}
.stat.medium   .val{{color:var(--c-medium)}}
.stat.low      .val{{color:var(--c-low)}}
.stat.pass     .val{{color:var(--c-pass)}}
.stat.fail     .val{{color:var(--c-critical)}}
.stat.total    .val{{color:#a371f7}}

/* ── Filter bar (used above bug list and test list) ── */
.filter-bar{{display:flex;gap:8px;align-items:center;flex-wrap:wrap;
            background:var(--surface);border:1px solid var(--border);
            border-radius:var(--radius);padding:10px 14px;margin-bottom:14px}}
.filter-lbl{{font-size:11px;text-transform:uppercase;letter-spacing:.6px;
            color:var(--muted);font-weight:600;margin-right:6px}}
.fbtn{{background:#0d1117;color:var(--muted);border:1px solid var(--border);
      border-radius:6px;padding:6px 12px;font-size:12px;font-weight:600;
      cursor:pointer;transition:background .12s,border-color .12s,color .12s}}
.fbtn:hover{{background:#1c2333;color:var(--text);border-color:#58a6ff}}
.fbtn.active{{background:#1f6feb;color:#fff;border-color:#1f6feb}}
.fbtn-pass.active{{background:var(--c-pass);border-color:var(--c-pass)}}
.fbtn-fail.active{{background:var(--c-critical);border-color:var(--c-critical)}}
.fbtn-critical.active{{background:var(--c-critical);border-color:var(--c-critical)}}
.fbtn-high.active{{background:var(--c-high);border-color:var(--c-high)}}
.fbtn-medium.active{{background:var(--c-medium);border-color:var(--c-medium);color:#000}}
.fbtn-low.active{{background:var(--c-low);border-color:var(--c-low);color:#000}}
.fbtn-search{{flex:1;min-width:180px;background:#0d1117;color:var(--text);
             border:1px solid var(--border);border-radius:6px;padding:6px 12px;
             font-size:12px;font-family:inherit;outline:none}}
.fbtn-search:focus{{border-color:#58a6ff}}
.fbtn-action{{background:#0d1117;color:var(--c-low);border:1px solid var(--border);
             border-radius:6px;padding:6px 10px;font-size:11px;font-weight:600;
             cursor:pointer;transition:background .12s,color .12s}}
.fbtn-action:hover{{background:#1c2333;color:var(--text)}}

/* When filter is active, hide non-matching items via attribute selectors */
.bug-card[data-hidden="1"]{{display:none}}
.spec-blk[data-hidden="1"]{{display:none}}
.trow[data-hidden="1"]{{display:none}}

/* ── Root-cause cluster summary banner ──────────────────────────────────── */
.cluster-summary{{margin:24px 0 16px}}
.cluster-headline{{font-size:14px;color:var(--muted);margin-bottom:14px}}
.cluster-headline strong{{color:#a371f7}}
.cluster-list{{display:flex;flex-direction:column;gap:8px}}
.cluster-row{{background:var(--surface);border:1px solid var(--border);
             border-radius:8px;padding:14px 18px;
             display:grid;grid-template-columns:auto 1fr auto;
             gap:14px;align-items:center}}
.cluster-row:hover{{border-color:#58a6ff}}
.cluster-meta{{display:flex;gap:6px;align-items:center;flex-wrap:wrap}}
.cluster-count{{font-size:11px;color:var(--muted);background:#0d1117;
               border:1px solid var(--border);border-radius:4px;
               padding:3px 8px;font-weight:600}}
.cluster-title{{font-size:13px;color:var(--text);font-weight:600}}
.cluster-tickets{{display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end;
                 max-width:300px}}
.cluster-bug-link{{font-size:10px;font-family:'SF Mono',monospace;color:#58a6ff;
                  text-decoration:none;background:#0d1117;border:1px solid var(--border);
                  padding:2px 6px;border-radius:4px}}
.cluster-bug-link:hover{{border-color:#58a6ff;background:#1c2333}}
.recurrence-badge{{background:#2d1b1b;color:#f85149;border:1px solid #f85149;
                  border-radius:4px;padding:2px 8px;font-size:10px;
                  font-weight:700;text-transform:uppercase;letter-spacing:.4px}}
.cluster-help{{font-size:11px;color:var(--muted);margin-top:12px;
              padding:8px 12px;background:#0d1117;border-radius:6px;
              border-left:3px solid #a371f7}}

/* ── Cross-spec inconsistency section ──────────────────────────────────── */
.ci-summary{{margin:24px 0 16px}}
.ci-headline{{font-size:13px;color:var(--muted);margin-bottom:14px}}
.ci-headline strong{{color:var(--c-medium)}}
.ci-list{{display:flex;flex-direction:column;gap:10px}}
.ci-row{{background:var(--surface);border:1px solid var(--border);
        border-radius:8px;padding:12px 16px}}
.ci-cat{{font-weight:600;color:var(--text);font-size:13px;margin-bottom:8px}}
.ci-table{{width:100%;border-collapse:collapse;font-size:12px}}
.ci-table th{{background:#0d1117;color:var(--muted);font-size:10px;
             text-transform:uppercase;letter-spacing:.5px;
             padding:6px 12px;text-align:left;border:1px solid var(--border)}}
.ci-table td{{padding:6px 12px;border:1px solid var(--border)}}
.ci-value code{{color:var(--c-medium);font-weight:600}}
.ci-spec-chip{{display:inline-block;font-size:10px;font-family:'SF Mono',monospace;
              background:#0d1117;color:#a371f7;border:1px solid var(--border);
              border-radius:4px;padding:2px 6px;margin:2px 3px}}

/* ── Test quality audit section ─────────────────────────────────────────── */
.tq-summary{{margin:24px 0 16px}}
.tq-headline{{font-size:13px;color:var(--muted);margin-bottom:14px}}
.tq-headline strong{{color:var(--c-medium)}}
.tq-table{{width:100%;border-collapse:collapse;font-size:12px;
          background:var(--surface);border:1px solid var(--border);
          border-radius:8px;overflow:hidden}}
.tq-table th{{background:#0d1117;color:var(--muted);font-size:10px;
             text-transform:uppercase;letter-spacing:.5px;
             padding:10px 14px;text-align:left}}
.tq-table td{{padding:9px 14px;border-top:1px solid var(--border)}}
.tq-table tr:hover td{{background:#1c2333}}
.tq-help{{font-size:11px;color:var(--muted);margin-top:12px;
         padding:8px 12px;background:#0d1117;border-radius:6px;
         border-left:3px solid var(--c-medium)}}

/* ── Test data viewer (expandable) ──────────────────────────────────────── */
.td-summary{{margin:24px 0 16px}}
.td-headline{{font-size:13px;color:var(--muted);margin-bottom:14px}}
.td-list{{display:flex;flex-direction:column;gap:8px}}
.td-spec-row, .td-type-row{{
  background:var(--surface);border:1px solid var(--border);border-radius:8px;
  overflow:hidden
}}
.td-type-row{{margin-top:6px;background:#0d1117}}
.td-spec-row > summary, .td-type-row > summary{{
  list-style:none;cursor:pointer;padding:11px 16px;
  display:flex;align-items:center;gap:14px;font-size:13px;
  user-select:none;transition:background .12s
}}
.td-spec-row > summary::-webkit-details-marker,
.td-type-row > summary::-webkit-details-marker{{display:none}}
.td-spec-row > summary::before, .td-type-row > summary::before{{
  content:"▶";color:var(--muted);font-size:9px;width:12px;flex-shrink:0
}}
.td-spec-row[open] > summary::before, .td-type-row[open] > summary::before{{
  content:"▼"
}}
.td-spec-row > summary:hover, .td-type-row > summary:hover{{background:#1c2333}}
.td-spec-name{{font-weight:600;color:var(--text);flex:1}}
.td-type-name{{font-family:'SF Mono',monospace;color:var(--c-low);
              font-size:12px;flex:1}}
.td-count{{font-size:11px;color:var(--muted);background:#0d1117;
          border:1px solid var(--border);border-radius:4px;padding:2px 8px}}
.td-data-count{{font-size:11px;color:#a371f7;background:rgba(163,113,247,.10);
               border-radius:4px;padding:2px 8px;font-weight:600}}
.td-spec-body, .td-type-body{{
  padding:12px 18px;border-top:1px solid var(--border)
}}
.td-help{{font-size:11px;color:var(--muted);margin-bottom:10px;
         padding:6px 10px;background:#0d1117;border-radius:5px;
         border-left:3px solid #a371f7}}
.td-data-list{{margin:8px 0;padding-left:20px;color:var(--text);font-size:12px}}
.td-data-list li{{padding:3px 0;line-height:1.5}}
.td-data-list code{{background:#0d1117;border:1px solid var(--border);
                    border-radius:3px;padding:1px 6px;font-size:11px;
                    color:#a371f7}}
.td-src{{color:#58a6ff;font-family:'SF Mono',monospace;font-size:11px}}
.td-empty{{color:var(--muted);font-style:italic;font-size:12px;padding:8px 0}}
.td-truncated{{font-size:11px;color:var(--muted);margin-top:6px;
              padding:6px 10px;background:#0d1117;border-radius:4px}}

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

/* ── Video PoC ── */
.video-wrap{{margin-top:16px}}
.video-label{{font-size:11px;font-weight:600;text-transform:uppercase;
             letter-spacing:.6px;color:var(--muted);margin-bottom:8px;
             display:flex;align-items:center;gap:6px}}
.video-label::before{{content:"🎬"}}
.poc-video{{width:100%;max-height:540px;border:1px solid var(--border);
           border-radius:8px;background:#000}}
.video-cta{{display:inline-block;margin-top:6px;font-size:11px;color:#58a6ff;
           text-decoration:none}}
.video-cta:hover{{text-decoration:underline}}

/* ── Sticky back button (top of report) ── */
.back-bar{{position:sticky;top:0;z-index:50;background:#0d1117ee;
          border-bottom:1px solid var(--border);padding:8px 0;
          backdrop-filter:blur(8px)}}
.back-bar-inner{{max-width:1100px;margin:0 auto;padding:0 20px;
                 display:flex;align-items:center;gap:14px;font-size:12px}}
.back-link{{color:#58a6ff;text-decoration:none;display:inline-flex;
            align-items:center;gap:6px;font-weight:600;
            padding:6px 12px;border:1px solid var(--border);border-radius:6px;
            background:#161b22;transition:background .15s,border-color .15s}}
.back-link:hover{{background:#1c2333;border-color:#58a6ff}}
.back-bar-spacer{{flex:1}}
.back-bar-quick{{color:var(--muted);font-size:11px}}
.back-bar-quick a{{color:#58a6ff;text-decoration:none;margin-left:8px}}
.back-bar-quick a:hover{{text-decoration:underline}}

/* ── Footer + contact card ── */
.footer-wrap{{margin-top:60px;padding:24px 20px;border-top:1px solid var(--border);
             text-align:center}}
.contact-card{{display:inline-flex;flex-direction:column;align-items:center;
              gap:6px;padding:18px 28px;background:var(--surface);
              border:1px solid var(--border);border-radius:10px;
              margin:14px auto 18px}}
.contact-card .name{{font-weight:700;font-size:15px;color:var(--text)}}
.contact-card .title{{font-size:12px;color:var(--muted)}}
.contact-card .links{{display:flex;gap:14px;margin-top:8px;flex-wrap:wrap;
                     justify-content:center}}
.contact-card .links a{{color:#58a6ff;text-decoration:none;font-size:12px;
                       padding:5px 10px;border:1px solid var(--border);
                       border-radius:6px;background:#0d1117;
                       transition:background .15s,border-color .15s}}
.contact-card .links a:hover{{background:#1c2333;border-color:#58a6ff}}

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

/* ── Expandable per-test rows (uses native <details>) ───────────────────── */
.trow-help{{padding:10px 16px;font-size:11px;color:var(--muted);
           border-bottom:1px solid var(--border);background:#0d1117}}
.trow{{border-bottom:1px solid var(--border)}}
.trow:last-child{{border-bottom:none}}
.trow > summary{{
  list-style:none;cursor:pointer;padding:11px 16px;display:flex;
  align-items:center;gap:14px;font-size:13px;user-select:none;
  transition:background .12s
}}
.trow > summary::-webkit-details-marker{{display:none}}
.trow > summary::before{{
  content:"▶";color:var(--muted);font-size:9px;width:12px;flex-shrink:0
}}
.trow[open] > summary::before{{content:"▼"}}
.trow > summary:hover{{background:#1c2333}}
.trow.pass{{border-left:3px solid var(--c-pass)}}
.trow.fail{{border-left:3px solid var(--c-critical);background:#1f1414}}
.trow.skip{{border-left:3px solid var(--muted)}}
.trow.fail > summary{{background:#1f1414}}
.trow.fail > summary:hover{{background:#2a1a1a}}

.t-chip{{font-size:10px;font-weight:700;letter-spacing:.5px;padding:3px 8px;
        border-radius:4px;font-family:'SF Mono',monospace;flex-shrink:0;
        min-width:88px;text-align:center}}
.t-chip.pass{{background:rgba(63,185,80,.16);color:var(--c-pass);border:1px solid var(--c-pass)}}
.t-chip.fail{{background:rgba(248,81,73,.16);color:var(--c-critical);border:1px solid var(--c-critical)}}
.t-chip.skip{{background:rgba(139,148,158,.16);color:var(--muted);border:1px solid var(--muted)}}
.t-chip.unknown{{background:#1c2333;color:var(--muted);border:1px solid var(--border)}}
.trow-name{{font-family:'SF Mono',monospace;color:var(--text);font-size:12px;
           overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1}}
.trow-params{{font-family:'SF Mono',monospace;color:#a371f7;font-size:11px;
             padding:2px 8px;background:rgba(163,113,247,.10);
             border-radius:4px;flex-shrink:0;max-width:240px;
             overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.trow-dur{{color:var(--muted);font-size:11px;flex-shrink:0;min-width:48px;text-align:right}}

.trow-details{{padding:14px 18px 18px 42px;background:#0d1117;
              border-top:1px solid var(--border)}}
.td-row{{display:flex;gap:12px;align-items:flex-start;padding:5px 0;
        font-size:13px;line-height:1.6}}
.td-lbl{{font-weight:600;color:var(--muted);min-width:160px;flex-shrink:0;
       font-size:11px;text-transform:uppercase;letter-spacing:.5px}}
.td-lbl.exp{{color:var(--c-pass)}}
.td-lbl.act{{color:var(--c-critical)}}
.td-val{{color:var(--text);flex:1}}
.td-val.td-data{{font-family:'SF Mono',monospace;color:#a371f7;font-size:12px}}
.td-val.td-empty{{color:var(--muted);font-style:italic}}
.td-val a{{color:#58a6ff;text-decoration:none}}
.td-val a:hover{{text-decoration:underline}}

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

/* ── Responsive — tablet + mobile breakpoints ─────────────────────────── */
@media (max-width:1024px) {{
  .wrap{{padding:16px 14px}}
  .hdr-inner{{flex-direction:column;align-items:flex-start;gap:12px}}
  .hdr-meta{{flex-direction:row;flex-wrap:wrap;gap:10px}}
  .stats{{grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:8px}}
  .stat .val{{font-size:26px}}
  .two-col{{grid-template-columns:1fr}}
}}
@media (max-width:768px) {{
  .wrap{{padding:12px 10px}}
  .hdr h1{{font-size:22px}}
  .hdr-meta{{font-size:12px}}
  .stats{{grid-template-columns:repeat(2,1fr);gap:8px}}
  .stat{{padding:14px 12px}}
  .stat .val{{font-size:22px}}
  .stat .label{{font-size:10px}}
  .filter-bar{{flex-direction:column;align-items:stretch}}
  .filter-bar .fbtn,.filter-bar .fbtn-action,.filter-bar .fbtn-search{{width:100%}}
  .trow > summary{{flex-wrap:wrap;gap:8px}}
  .trow-name{{font-size:11px}}
  .trow-params{{max-width:100%;font-size:10px}}
  .trow-details{{padding:12px 12px 14px 28px}}
  .td-row{{flex-direction:column;gap:2px}}
  .td-lbl{{min-width:auto}}
  table,.test-table{{font-size:11px;display:block;overflow-x:auto}}
  .bug-card-hdr{{padding:14px}}
  .bug-title{{font-size:14px}}
  .bug-body{{padding:14px}}
  .cluster-row{{grid-template-columns:1fr;gap:8px}}
  .cluster-tickets{{justify-content:flex-start;max-width:100%}}
  .ci-table{{font-size:10px}}
  .tq-table{{font-size:10px}}
  .ev-table{{display:block;overflow-x:auto}}
  .perf-grid{{flex-wrap:wrap}}
  .perf-stat{{min-width:90px;flex:1}}
  .back-bar-inner{{flex-direction:column;align-items:flex-start;gap:6px;padding:0 12px}}
  .back-bar-quick{{font-size:10px}}
}}
@media (max-width:480px) {{
  .stats{{grid-template-columns:1fr 1fr;gap:6px}}
  .hdr h1{{font-size:18px}}
  .sec-title{{font-size:14px}}
  .footer-wrap{{padding:18px 12px}}
  .contact-card{{padding:14px 18px}}
  .contact-card .links{{flex-direction:column;gap:6px}}
}}

/* ── Print ── */
@media print{{
  .hdr-meta .print-btn,.err-toggle{{display:none}}
  .err-body{{display:block!important}}
  body{{background:#fff;color:#000}}
  .bug-card{{border:1px solid #ccc;break-inside:avoid}}
  .back-bar{{display:none}}
}}
</style>
</head>
<body>

<!-- Sticky back-button bar — visible on all reports so users can return
     to the dashboard regardless of which #anchor they opened. -->
<div class="back-bar">
  <div class="back-bar-inner">
    <a href="{back_link_path}" class="back-link">← Back to Dashboard</a>
    <span class="back-bar-spacer"></span>
    <span class="back-bar-quick">
      Jump:
      <a href="#bugs">🐛 Bugs</a>
      <a href="#tests">🧪 Tests</a>
      <a href="#summary-table">📊 Summary</a>
    </span>
  </div>
</div>

<!-- Lightbox -->
<div id="lb" onclick="this.classList.remove('show')">
  <img id="lb-img" src="" alt="Screenshot"/>
</div>

<!-- Header -->
<div class="hdr">
  <div class="hdr-inner">
    <div class="hdr-left">
      <h1>Mehad <span>QA</span> Bug Report</h1>
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

<!-- Stats — every card is clickable; jumps to a filtered section -->
<div class="stats">
  <a href="#bugs"        class="stat critical" data-filter="bugs"     title="Show CRITICAL bug tickets"><div class="label">Critical</div><div class="val">{cnt_critical}</div></a>
  <a href="#bugs"        class="stat high"     data-filter="bugs"     title="Show HIGH bug tickets"><div class="label">High</div>    <div class="val">{cnt_high}</div></a>
  <a href="#bugs"        class="stat medium"   data-filter="bugs"     title="Show MEDIUM bug tickets"><div class="label">Medium</div>  <div class="val">{cnt_medium}</div></a>
  <a href="#bugs"        class="stat low"      data-filter="bugs"     title="Show LOW bug tickets"><div class="label">Low</div>     <div class="val">{cnt_low}</div></a>
  <a href="#tests"       class="stat pass"     data-filter="passed"   title="Show only PASSED tests"><div class="label">Passed</div>  <div class="val">{total_passed}</div></a>
  <a href="#tests"       class="stat fail"     data-filter="failed"   title="Show only FAILED tests"><div class="label">Failed</div>  <div class="val">{total_failed}</div></a>
  <a href="#tests"       class="stat total"    data-filter="all"      title="Show all tests"><div class="label">Total Tests</div><div class="val">{total_tests}</div></a>
</div>

<!-- Cluster summary — groups bugs by root cause (e.g. 6 missing-headers
     finding share '1 root cause: security headers') -->
{cluster_summary}

<!-- Extra section: cross-spec inconsistencies, etc. -->
{extra_section_html}

<!-- Bug Tickets -->
<div class="sec-title" id="bugs">
  Bug Tickets <span class="count">{total_bugs}</span>
</div>

<!-- Bug-tickets severity filter (visible only when at least one bug exists) -->
<div class="filter-bar bug-filter-bar" id="bug-filter-bar">
  <span class="filter-lbl">Filter:</span>
  <button class="fbtn active" data-bug-filter="all">All ({total_bugs})</button>
  <button class="fbtn fbtn-critical" data-bug-filter="CRITICAL">Critical ({cnt_critical})</button>
  <button class="fbtn fbtn-high"     data-bug-filter="HIGH">High ({cnt_high})</button>
  <button class="fbtn fbtn-medium"   data-bug-filter="MEDIUM">Medium ({cnt_medium})</button>
  <button class="fbtn fbtn-low"      data-bug-filter="LOW">Low ({cnt_low})</button>
</div>

<div id="bug-list">
{bug_tickets_html}
</div>

<!-- Summary Table -->
<div class="sec-title" id="summary-table">All Test Results</div>
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

<!-- Per-Spec Test Details — pass/fail filter -->
<div class="sec-title" id="tests" style="margin-top:40px">
  Per-Test Breakdown
  <span class="count">click any row to expand · test data + duration shown</span>
</div>
<div class="filter-bar test-filter-bar">
  <span class="filter-lbl">Show:</span>
  <button class="fbtn active" data-test-filter="all">All ({total_tests})</button>
  <button class="fbtn fbtn-pass" data-test-filter="passed">✅ Passed ({total_passed})</button>
  <button class="fbtn fbtn-fail" data-test-filter="failed">❌ Failed ({total_failed})</button>
  <input type="text" class="fbtn-search" placeholder="🔍 Search by test name..." data-search="">
  <button class="fbtn-action" data-action="expand-all">⬇ Expand all</button>
  <button class="fbtn-action" data-action="collapse-all">⬆ Collapse all</button>
</div>
<div id="spec-details">
{spec_details_html}
</div>

<!-- Coverage Gaps -->
<div class="sec-title" style="margin-top:40px">Coverage Gaps <span class="count">AI Analysis</span></div>
{gaps_html}

<!-- Footer with author/contact card -->
<div class="footer-wrap">
  <div style="color:var(--muted);font-size:12px;margin-bottom:6px">
    Built by Mejbaur Bahar Fagun
  </div>
  <div class="contact-card">
    <div class="name">Mejbaur Bahar Fagun</div>
    <div class="title">Senior Software Engineer QA (IV) · Markopolo.ai</div>
    <div class="links">
      <a href="https://www.linkedin.com/in/mejbaur/" target="_blank" rel="noopener">💼 LinkedIn</a>
    </div>
  </div>
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

// ── Filter state & DOM wiring ─────────────────────────────────────────────
function applyTestFilter(mode){{
  // mode = "all" | "passed" | "failed"
  var rows = document.querySelectorAll('#spec-details .trow');
  rows.forEach(function(r){{
    var isPass = r.classList.contains('pass');
    var isFail = r.classList.contains('fail');
    var match  = (mode === 'all') ||
                 (mode === 'passed' && isPass) ||
                 (mode === 'failed' && isFail);
    r.dataset.hidden = match ? '0' : '1';
  }});
  // Also hide spec-blk wrappers that have no visible rows
  document.querySelectorAll('.spec-blk').forEach(function(blk){{
    var visible = blk.querySelectorAll('.trow:not([data-hidden="1"])').length;
    blk.dataset.hidden = visible === 0 ? '1' : '0';
    if(visible > 0 && blk.querySelector('.spec-blk-body')){{
      blk.querySelector('.spec-blk-body').classList.add('open');
      var t = blk.querySelector('.spec-blk-toggle');
      if(t) t.textContent = '▼ Hide tests';
    }}
  }});
  // Update active button
  document.querySelectorAll('[data-test-filter]').forEach(function(b){{
    b.classList.toggle('active', b.dataset.testFilter === mode);
  }});
}}

function applyTestSearch(q){{
  q = (q || '').toLowerCase().trim();
  document.querySelectorAll('#spec-details .trow').forEach(function(r){{
    if(!q){{ r.dataset.hidden = '0'; return; }}
    var nm = (r.querySelector('.trow-name') || {{}}).textContent || '';
    var match = nm.toLowerCase().indexOf(q) !== -1;
    r.dataset.hidden = match ? '0' : '1';
  }});
  document.querySelectorAll('.spec-blk').forEach(function(blk){{
    var visible = blk.querySelectorAll('.trow:not([data-hidden="1"])').length;
    blk.dataset.hidden = visible === 0 ? '1' : '0';
    if(q && visible > 0 && blk.querySelector('.spec-blk-body')){{
      blk.querySelector('.spec-blk-body').classList.add('open');
    }}
  }});
}}

function applyBugFilter(sev){{
  // sev = "all" | "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"
  document.querySelectorAll('#bug-list .bug-card').forEach(function(c){{
    if(sev === 'all'){{ c.dataset.hidden = '0'; return; }}
    var match = c.querySelector('.badge.' + sev) !== null;
    c.dataset.hidden = match ? '0' : '1';
  }});
  document.querySelectorAll('[data-bug-filter]').forEach(function(b){{
    b.classList.toggle('active', b.dataset.bugFilter === sev);
  }});
}}

function expandAllTests(open){{
  document.querySelectorAll('#spec-details .trow').forEach(function(d){{
    if(open) d.setAttribute('open',''); else d.removeAttribute('open');
  }});
  document.querySelectorAll('#spec-details .spec-blk-body').forEach(function(b){{
    b.classList.toggle('open', !!open);
    var arrow = b.previousElementSibling && b.previousElementSibling.querySelector('.spec-blk-toggle');
    if(arrow) arrow.textContent = open ? '▼ Hide tests' : '▶ Show tests';
  }});
}}

function handleHash(){{
  var h = (location.hash || '').toLowerCase();
  if(h === '#passed') applyTestFilter('passed');
  else if(h === '#failed') applyTestFilter('failed');
  else if(h === '#all-tests' || h === '#tests') applyTestFilter('all');
  else if(h === '#bugs') applyBugFilter('all');
  else if(h.startsWith('#bug-')){{
    var sev = h.replace('#bug-','').toUpperCase();
    applyBugFilter(sev);
  }}
}}

// Wire up clicks on any `.stat[data-filter]` card to set the appropriate filter
document.addEventListener('click', function(e){{
  var stat = e.target.closest('.stat[data-filter]');
  if(stat){{
    var f = stat.dataset.filter;
    if(f === 'passed' || f === 'failed' || f === 'all'){{
      applyTestFilter(f);
      // Open spec blocks so the filtered tests are visible
      document.querySelectorAll('.spec-blk-body').forEach(function(b){{
        b.classList.add('open');
        var ar=b.previousElementSibling && b.previousElementSibling.querySelector('.spec-blk-toggle');
        if(ar) ar.textContent='▼ Hide tests';
      }});
    }}
    if(f === 'bugs') applyBugFilter('all');
  }}
  var fbtn = e.target.closest('[data-test-filter]');
  if(fbtn){{ applyTestFilter(fbtn.dataset.testFilter); }}
  var bbtn = e.target.closest('[data-bug-filter]');
  if(bbtn){{ applyBugFilter(bbtn.dataset.bugFilter); }}
  var act = e.target.closest('[data-action]');
  if(act){{
    if(act.dataset.action === 'expand-all')   expandAllTests(true);
    if(act.dataset.action === 'collapse-all') expandAllTests(false);
  }}
}});

document.addEventListener('input', function(e){{
  var s = e.target.closest('[data-search]');
  if(s){{ applyTestSearch(s.value); }}
}});

window.addEventListener('hashchange', handleHash);
window.addEventListener('DOMContentLoaded', handleHash);
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
    video = bug.get("video_path", "")  # relative path under reports/
    tdata = bug.get("test_data", "")
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

    # Expected / Actual — labels worded for non-engineers
    exp_act = f"""
<div class="two-col">
  <div class="info-block expected">
    <div class="ib-label">✓ What should happen</div>
    <div>{_esc(exp) or "<em style='color:var(--muted)'>Not specified</em>"}</div>
  </div>
  <div class="info-block actual">
    <div class="ib-label">✗ What actually happened</div>
    <div>{_esc(act) or "<em style='color:var(--muted)'>See error below</em>"}</div>
  </div>
</div>"""

    # Screenshot PoC — annotated with red banner showing the error
    if shot:
        shot_html = f"""
<div class="shot-wrap">
  <div class="shot-label">Proof of Concept — Screenshot (annotated with bug)</div>
  <img class="screenshot" src="{shot}" alt="Test failure screenshot"
       onclick="openShot(this.src)" title="Click to enlarge"/>
</div>"""
    else:
        shot_html = """
<div class="shot-wrap">
  <div class="shot-label">Proof of Concept — Screenshot</div>
  <div class="no-shot">No screenshot captured (test may have failed before page loaded)</div>
</div>"""

    # Video PoC — Playwright recording. Helps reviewers see the exact
    # sequence of actions that led to the failure.
    if video:
        video_html = f"""
<div class="video-wrap">
  <div class="video-label">Proof of Concept — Screen Recording</div>
  <video class="poc-video" controls preload="metadata"
         src="{_esc(video)}" type="video/webm">
    Your browser does not support embedded video.
  </video>
  <div><a class="video-cta" href="{_esc(video)}" download>⬇ Download .webm</a></div>
</div>"""
    else:
        video_html = ""

    # Test data row — what data was actually used (if any)
    if tdata:
        td_html = f"""
<div class="info-block analysis" style="margin-bottom:16px">
  <div class="ib-label">🧪 Test data used</div>
  <div style="font-family:'SF Mono',monospace;color:#a371f7;font-size:12px">
    {_esc(tdata)}
  </div>
</div>"""
    else:
        td_html = ""

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

    # Description — labeled for non-engineers
    desc_html = f"""
<div class="info-block analysis" style="margin-bottom:16px">
  <div class="ib-label">📋 What this test was checking</div>
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
    {td_html}
    {steps_html}
    {exp_act}
    {shot_html}
    {video_html}
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
    """Build a collapsible per-spec block listing every test (passed AND failed)
    with click-to-expand details: docstring, parametrize values, duration."""
    json_report = result.get("json_report")
    outcomes    = _load_pytest_outcomes(json_report) if json_report else {}

    tests_dir  = Path("tests")
    test_file  = tests_dir / f"test_{spec_name.replace('-', '_')}.py"
    test_info  = _parse_test_file(test_file) if test_file.exists() else {}

    # Pull pre-built passed/failed records from the consolidator if present.
    passed_recs: list[dict] = result.get("passed_tests", []) or []
    bug_recs:    list[dict] = result.get("bugs", []) or []

    # Build a unified list of {name, outcome, docstring, params, duration, friendly_*}
    rows: list[dict] = []

    # PASSED tests — from consolidator's passed_tests array (preferred)
    for rec in passed_recs:
        rows.append({
            "name":      rec.get("name", "unknown"),
            "outcome":   "passed",
            "docstring": rec.get("docstring") or test_info.get(rec.get("name", ""), {}).get("docstring", ""),
            "params":    rec.get("params", ""),
            "duration":  rec.get("duration", 0.0),
            "friendly_actual":   "",
            "friendly_expected": "",
        })

    # FAILED tests — from bug list
    for bug in bug_recs:
        rows.append({
            "name":      bug.get("test_name", "unknown"),
            "outcome":   "failed",
            "docstring": bug.get("docstring", "") or test_info.get(bug.get("test_name", ""), {}).get("docstring", ""),
            "params":    bug.get("test_data", ""),
            "duration":  0.0,
            "friendly_actual":   bug.get("actual", ""),
            "friendly_expected": bug.get("expected", ""),
            "bug_id":            bug.get("id", ""),
        })

    # Legacy path — if no consolidator data, fall back to raw outcomes + AST info
    if not rows and (outcomes or test_info):
        for fn in dict.fromkeys(list(test_info.keys()) + list(outcomes.keys())):
            info = test_info.get(fn, {})
            rows.append({
                "name":      fn,
                "outcome":   outcomes.get(fn, "unknown"),
                "docstring": info.get("docstring", ""),
                "params":    info.get("test_data", ""),
                "duration":  0.0,
                "friendly_actual":   "",
                "friendly_expected": "",
            })

    if not rows:
        return ""

    total   = len(rows)
    n_pass  = sum(1 for r in rows if r["outcome"] == "passed")
    n_fail  = total - n_pass
    icon    = "✅" if n_fail == 0 else "❌"
    body_id = f"spec-detail-{block_idx}"

    # Render each test as an expandable row. The `details` element gives us
    # click-to-expand for free with no JS, and the styled <summary> looks
    # like a clickable list item.
    test_rows = []
    for i, r in enumerate(rows):
        nm     = _esc(r["name"])
        out    = r["outcome"]
        ds     = _esc((r.get("docstring") or "").strip())
        params = _esc(r.get("params") or "")
        dur    = r.get("duration", 0.0)
        dur_s  = f"{dur:.2f}s" if dur else "—"

        if out == "passed":
            status_chip = '<span class="t-chip pass">✅ PASSED</span>'
            row_cls     = "trow pass"
        elif out in ("failed", "error"):
            status_chip = f'<span class="t-chip fail">❌ FAILED</span>'
            row_cls     = "trow fail"
        elif out == "skipped":
            status_chip = '<span class="t-chip skip">⏭ SKIPPED</span>'
            row_cls     = "trow skip"
        else:
            status_chip = f'<span class="t-chip unknown">— {_esc(out)}</span>'
            row_cls     = "trow unknown"

        # Build the expanded body: docstring (what the test verifies), params
        # (test data), duration, and for failed tests the friendly explanation.
        details_html_parts = []
        if ds:
            details_html_parts.append(
                f'<div class="td-row"><span class="td-lbl">What this test checks:</span>'
                f'<span class="td-val">{ds}</span></div>')
        else:
            details_html_parts.append(
                f'<div class="td-row"><span class="td-lbl">What this test checks:</span>'
                f'<span class="td-val td-empty">(no docstring — see test source)</span></div>')
        if params:
            details_html_parts.append(
                f'<div class="td-row"><span class="td-lbl">Test data used:</span>'
                f'<span class="td-val td-data">{params}</span></div>')
        details_html_parts.append(
            f'<div class="td-row"><span class="td-lbl">Duration:</span>'
            f'<span class="td-val">{dur_s}</span></div>')
        details_html_parts.append(
            f'<div class="td-row"><span class="td-lbl">Test function:</span>'
            f'<span class="td-val"><code>{nm}</code></span></div>')

        if out in ("failed", "error"):
            fa = _esc(r.get("friendly_actual", "") or "")
            fe = _esc(r.get("friendly_expected", "") or "")
            bug_id = r.get("bug_id", "")
            if fe:
                details_html_parts.append(
                    f'<div class="td-row"><span class="td-lbl exp">Expected:</span>'
                    f'<span class="td-val">{fe}</span></div>')
            if fa:
                details_html_parts.append(
                    f'<div class="td-row"><span class="td-lbl act">What happened:</span>'
                    f'<span class="td-val">{fa}</span></div>')
            if bug_id:
                details_html_parts.append(
                    f'<div class="td-row"><span class="td-lbl">Bug ticket:</span>'
                    f'<span class="td-val"><a href="#{bug_id}">{bug_id}</a> — '
                    f'see full details below</span></div>')

        details_html = "".join(details_html_parts)
        # Use <details>/<summary> for native click-to-expand, no JS needed
        test_rows.append(f"""
<details class="{row_cls}">
  <summary>
    {status_chip}
    <span class="trow-name">{nm}</span>
    {f'<span class="trow-params">{params}</span>' if params else ''}
    <span class="trow-dur">{dur_s}</span>
  </summary>
  <div class="trow-details">
    {details_html}
  </div>
</details>""")

    rows_html = "\n".join(test_rows)
    label = (f"{icon} <code>{_esc(spec_name)}</code> — "
             f"<span style='color:var(--c-pass)'>{n_pass} passed</span> · "
             f"<span style='color:var(--c-critical)'>{n_fail} failed</span> · "
             f"{total} total")

    return f"""
<div class="spec-blk">
  <div class="spec-blk-hdr" onclick="toggleSpec('{body_id}')">
    <span class="spec-blk-title">{label}</span>
    <span class="spec-blk-toggle">▶ Show tests</span>
  </div>
  <div class="spec-blk-body" id="{body_id}">
    <div class="trow-help">
      Click any test row below to expand and see what was verified, the test
      data used, and (for failures) what went wrong in plain English.
    </div>
    {rows_html}
  </div>
</div>"""


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def _build_cluster_summary(all_bugs: list[dict]) -> str:
    """Render a top-of-report banner showing root-cause clusters.

    Each bug is expected to have `fingerprint` + `category_title` keys
    (set by scripts/consolidate_reports.py via cluster_bugs()). This
    function aggregates them into a clickable summary that links to
    the individual bug tickets below."""
    if not all_bugs:
        return ""
    # Group by fingerprint
    by_fp: dict[str, dict] = {}
    for bug in all_bugs:
        fp = bug.get("fingerprint", "")
        if not fp:
            continue
        if fp not in by_fp:
            by_fp[fp] = {
                "title":    bug.get("category_title", "(uncategorized)"),
                "severity": bug.get("severity", "MEDIUM"),
                "priority": bug.get("priority", "P2"),
                "bugs":     [],
                "recurrence": bug.get("recurrence_count", 1),
            }
        by_fp[fp]["bugs"].append(bug)
        # Promote to most-severe in cluster
        sev_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        if sev_order.get(bug.get("severity", "MEDIUM"), 9) < \
           sev_order.get(by_fp[fp]["severity"], 9):
            by_fp[fp]["severity"] = bug.get("severity")
            by_fp[fp]["priority"] = bug.get("priority", "P2")

    if not by_fp:
        return ""

    # Sort: severity desc → cluster size desc
    sev_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    sorted_clusters = sorted(
        by_fp.items(),
        key=lambda kv: (sev_order.get(kv[1]["severity"], 9), -len(kv[1]["bugs"]))
    )

    rows_html = []
    for fp, c in sorted_clusters:
        bugs   = c["bugs"]
        sev    = c["severity"]
        pri    = c["priority"]
        n      = len(bugs)
        recur  = c["recurrence"]
        title  = _esc(c["title"])
        # Anchors to the affected bug tickets
        bug_links = " ".join(
            f'<a href="#{_esc(b.get("id",""))}" class="cluster-bug-link">'
            f'{_esc(b.get("id",""))}</a>'
            for b in bugs
        )
        recur_badge = (f'<span class="recurrence-badge">'
                       f'{recur}× consecutive runs</span>'
                       if recur >= 3 else "")
        rows_html.append(f"""
<div class="cluster-row">
  <div class="cluster-meta">
    <span class="badge {sev}">{sev}</span>
    <span class="badge {pri}">{pri}</span>
    <span class="cluster-count">{n}× affected</span>
    {recur_badge}
  </div>
  <div class="cluster-title">{title}</div>
  <div class="cluster-tickets">{bug_links}</div>
</div>""")

    n_clusters = len(by_fp)
    n_bugs     = sum(len(c["bugs"]) for c in by_fp.values())
    headline = (f"{n_bugs} bug ticket(s) → "
                f"<strong>{n_clusters} unique root cause(s)</strong>")

    return f"""
<div class="cluster-summary" id="clusters">
  <div class="sec-title" style="margin:24px 0 12px">
    🎯 Root-Cause Summary <span class="count">{n_clusters} clusters</span>
  </div>
  <div class="cluster-headline">{headline}</div>
  <div class="cluster-list">{"".join(rows_html)}</div>
  <div class="cluster-help">
    Bugs sharing a root cause are grouped here so you fix one thing
    instead of N. Click any ticket ID to jump to its full bug card below.
  </div>
</div>"""


def generate_report(all_results: dict, base_url: str, model: str,
                    output_filename: str = "bug-report.html",
                    extra_section_html: str = "",
                    base_path_prefix: str = "") -> Path:
    """Render the master or per-agent report.

    base_path_prefix:
      ""    — report lives at site root (e.g. /report.html).
              `index.html` is correct.
      "../" — report lives in /agents/ subdir. `../index.html` needed
              so 'Back to Dashboard' navigates correctly.
    """
    all_bugs = [b for r in all_results.values() for b in r.get("bugs", [])]

    total_passed = sum(r.get("passed", 0) for r in all_results.values())
    total_failed = sum(r.get("failed", 0) for r in all_results.values())
    total_tests  = sum(r.get("total",  0) for r in all_results.values())

    cnt = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for b in all_bugs:
        sev = b.get("severity", "MEDIUM").upper()
        cnt[sev] = cnt.get(sev, 0) + 1

    # ── Cluster summary banner ─────────────────────────────────────────────
    # consolidate-reports.py adds 'fingerprint' + 'category_title' to each
    # bug. Aggregate them into a top-of-report summary so users can grok
    # the report at a glance: "8 bugs, 4 unique root causes".
    cluster_summary = _build_cluster_summary(all_bugs)

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
        cluster_summary  = cluster_summary,
        extra_section_html = extra_section_html,
        bug_tickets_html = bug_tickets_html,
        results_rows     = results_rows,
        spec_details_html= spec_details_html,
        gaps_html        = gaps_html,
        back_link_path   = f"{base_path_prefix}index.html",
    )

    REPORTS_DIR.mkdir(exist_ok=True)
    out = REPORTS_DIR / output_filename
    out.write_text(html, encoding="utf-8")
    return out
