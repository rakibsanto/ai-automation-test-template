"""
Causal bug clustering + cross-run fingerprinting.

Two related ideas:
  1. CLUSTERING — group bug tickets within a single CI run by their
     root-cause fingerprint. Eight 'missing CSP'/'missing HSTS' findings
     across different pages are really ONE bug ('CSP not configured at
     edge'); the report should show ONE cluster with 8 affected tests.
  2. FINGERPRINTING — give each bug a stable hash that survives across
     runs. trends.json on gh-pages tracks recurrences. A bug seen in
     run #30, #31, #32 shows '3 runs in a row' — useful for prioritising.

Public API:
    clusters = cluster_bugs(bugs)            # list[dict]  →  list[Cluster]
    fingerprint = compute_fingerprint(bug)   # → 12-char stable hash
    update_trends(fingerprints, trends_path) # → updated trends.json
"""

from __future__ import annotations
import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

# ─── Fingerprint computation ──────────────────────────────────────────────────

# Patterns that normalize "noisy" bits of error messages so the same
# underlying bug fingerprints identically across runs/pages/tests.
_NORMALIZERS: list[tuple[re.Pattern, str]] = [
    # Specific values → placeholders
    (re.compile(r"\d{3,}ms"),                     "<MS>"),
    (re.compile(r"\d{4,}px"),                     "<PX>"),
    (re.compile(r"\d{5,}"),                       "<NUM>"),
    (re.compile(r"https?://[^\s'\"]+"),           "<URL>"),
    (re.compile(r"line\s+\d+"),                   "line <N>"),
    (re.compile(r"\b[a-f0-9]{8,}\b"),             "<HEX>"),
    (re.compile(r"port\s+\d+"),                   "port <P>"),
    (re.compile(r"timeout=\d+"),                  "timeout=<T>"),
    # Locator details
    (re.compile(r"selector=['\"][^'\"]*['\"]"),   "selector=<S>"),
    (re.compile(r"frame=<Frame[^>]*>"),           "frame=<F>"),
    # Whitespace
    (re.compile(r"\s+"),                          " "),
]


def _normalize(text: str) -> str:
    """Strip page-/run-specific noise so equivalent errors hash equally."""
    text = (text or "")[:500]
    for pat, repl in _NORMALIZERS:
        text = pat.sub(repl, text)
    return text.strip().lower()


# Semantic categories — each rule maps an error pattern to a cluster_key.
# Bugs sharing a cluster_key fall into the same cluster regardless of
# which test reported them. This is what catches "8 different missing
# headers" → 1 cluster, "navigation failed across 3 tests" → 1 cluster, etc.
_CATEGORY_RULES: list[tuple[re.Pattern, str, str]] = [
    # (regex, cluster_key, human-readable category title)
    (re.compile(r"missing\s+(?:strict-transport-security|hsts)", re.I),
     "sec_header_missing", "Security: HTTP-strict-transport-security misconfigured"),
    (re.compile(r"clickjacking|x-frame-options|frame-ancestors", re.I),
     "sec_header_clickjacking", "Security: clickjacking protection missing"),
    (re.compile(r"x-content-type-options|nosniff", re.I),
     "sec_header_nosniff", "Security: MIME-sniff protection missing"),
    (re.compile(r"referrer-policy", re.I),
     "sec_header_referrer", "Security: Referrer-Policy missing"),
    (re.compile(r"content-security-policy|csp(?!\w)", re.I),
     "sec_header_csp", "Security: CSP not configured"),
    (re.compile(r"server\s+version|x-powered-by", re.I),
     "sec_info_disclosure", "Security: framework version disclosed"),

    # Auth / OTP rate-limit
    (re.compile(r"send code (?:still |is )?disabled|otp.*expired|"
                r"rate.?limit|throttle|429", re.I),
     "auth_otp_unavailable", "Auth: OTP service rate-limited / unavailable"),
    (re.compile(r"login (?:did not |didn't )?succeed|"
                r"automations student|otp input did not appear", re.I),
     "auth_login_flow_broken", "Auth: full login flow broken"),
    (re.compile(r"locator\.fill: timeout", re.I),
     "input_not_actionable", "Input field never became actionable"),

    # Navigation
    (re.compile(r"did not navigate|did not (?:redirect|go) to|navigate.*find-tutors", re.I),
     "navigation_blocked", "Navigation: page did not change"),

    # Performance / Core Web Vitals
    (re.compile(r"ttfb\s+\d+", re.I),
     "perf_ttfb_over_budget", "Performance: TTFB over budget"),
    (re.compile(r"lcp\s+\d+", re.I),
     "perf_lcp_over_budget", "Performance: LCP (Largest Contentful Paint) over budget"),
    (re.compile(r"cls\s+\d+", re.I),
     "perf_cls_over_budget", "Performance: CLS (Cumulative Layout Shift) over budget"),
    (re.compile(r"page-load\s+\d+|page_load_ms", re.I),
     "perf_pageload_over_budget", "Performance: page-load over budget"),
    (re.compile(r"heap.+grew|memory.*leak|detached.+dom", re.I),
     "perf_memory_leak", "Performance: memory leak detected"),

    # Visual regression
    (re.compile(r"visual regression|pixels differ", re.I),
     "visual_drift", "Visual: page rendering differs from baseline"),

    # JS errors
    (re.compile(r"uncaught js error|pageerror|console\.error", re.I),
     "js_error", "JavaScript: uncaught runtime error"),

    # Accessibility
    (re.compile(r"no h1|missing.+lang|aria-label", re.I),
     "a11y_missing_attr", "Accessibility: required attribute missing"),

    # Generic asserts (fallback)
    (re.compile(r"assertion ?error: ([^\n]{10,80})", re.I),
     "generic_assertion", "Generic assertion failure"),
]


def _semantic_category(error_text: str) -> tuple[str, str]:
    """Map error text to (cluster_key, human title). Falls back to a
    hash-based key when no rule matches — so unique unmatched errors
    each get their own cluster (no over-clustering)."""
    haystack = error_text or ""
    for pattern, key, title in _CATEGORY_RULES:
        if pattern.search(haystack):
            return key, title
    # Fall back: hash the normalized error so similar errors still cluster
    norm = _normalize(haystack)[:120]
    if not norm:
        return "no_error_text", "Unspecified failure"
    h = hashlib.sha256(norm.encode("utf-8")).hexdigest()[:8]
    return f"unknown_{h}", "Uncategorized failure"


def compute_fingerprint(bug: dict) -> str:
    """Stable 12-char hash that identifies the underlying defect.

    Uses semantic category mapping — bugs sharing a category cluster
    together regardless of which specific test reported them. This is
    what makes 'missing CSP', 'missing HSTS', 'missing Referrer-Policy'
    cluster as 'security headers' or remain separate per their category."""
    err = bug.get("error_message", "") or bug.get("actual", "")
    cluster_key, _title = _semantic_category(err)
    payload = cluster_key
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def compute_category_title(bug: dict) -> str:
    """Public — return the human-readable cluster title for one bug."""
    err = bug.get("error_message", "") or bug.get("actual", "")
    _key, title = _semantic_category(err)
    return title


# ─── Clustering ───────────────────────────────────────────────────────────────

@dataclass
class BugCluster:
    """A group of bug tickets that share a root cause."""
    fingerprint: str
    title:       str
    severity:    str             # max severity in the cluster
    priority:    str
    description: str             # representative description
    bugs:        list[dict]      = field(default_factory=list)

    def affected_count(self) -> int:
        return len(self.bugs)

    def affected_tests(self) -> list[str]:
        return [b.get("test_name", "?") for b in self.bugs]

    def cluster_id(self) -> str:
        return f"CLUSTER-{self.fingerprint[:8]}"

    def representative(self) -> dict:
        """Return the most useful single bug from the cluster as the
        face of the cluster: prefer the one with screenshot+video."""
        best = self.bugs[0]
        for b in self.bugs:
            if b.get("screenshot_b64") and not best.get("screenshot_b64"):
                best = b
            if b.get("video_path") and not best.get("video_path"):
                best = b
        return best


_SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}


def _max_severity(severities: Iterable[str]) -> str:
    valid = [s for s in severities if s in _SEVERITY_ORDER]
    if not valid:
        return "MEDIUM"
    return min(valid, key=_SEVERITY_ORDER.get)


def cluster_bugs(bugs: list[dict]) -> list[BugCluster]:
    """Group bugs by causal fingerprint. Returns clusters sorted by
    severity descending then size descending."""
    if not bugs:
        return []
    by_fp: dict[str, BugCluster] = {}
    for bug in bugs:
        fp = compute_fingerprint(bug)
        category_title = compute_category_title(bug)
        bug["fingerprint"] = fp                    # attach for renderer
        bug["category_title"] = category_title
        if fp not in by_fp:
            by_fp[fp] = BugCluster(
                fingerprint=fp,
                title       = category_title,      # use semantic title, not 1st bug title
                severity    = bug.get("severity", "MEDIUM"),
                priority    = bug.get("priority", "P2"),
                description = bug.get("description", ""),
            )
        by_fp[fp].bugs.append(bug)

    # Promote each cluster's severity to the worst seen
    for cluster in by_fp.values():
        cluster.severity = _max_severity(b.get("severity", "MEDIUM")
                                          for b in cluster.bugs)
        # Promote priority to most urgent (P0 < P1 < P2 < P3)
        priorities = [b.get("priority", "P2") for b in cluster.bugs]
        cluster.priority = min(priorities, key=lambda p: int(p[1:]) if p[1:].isdigit() else 9)

    # Sort: severity asc (CRITICAL=0 first), then largest cluster first
    sorted_clusters = sorted(
        by_fp.values(),
        key=lambda c: (_SEVERITY_ORDER.get(c.severity, 9),
                       -c.affected_count())
    )
    return sorted_clusters


# ─── Cross-run trend tracking ─────────────────────────────────────────────────

def load_trends(path: str | Path) -> dict:
    """Load existing trends.json or return an empty structure.
    Accepts str or Path."""
    p = Path(path) if not isinstance(path, Path) else path
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"runs": [], "fingerprints": {}}


def update_trends(trends: dict, run_number: int | str, run_url: str,
                  totals: dict, fingerprints_seen: list[str]) -> dict:
    """Append this run's data to the trends record. Returns updated dict.

    Each fingerprint tracks: first_seen_run, last_seen_run, runs_seen_count.
    A fingerprint NOT seen this run gets last_seen_run incremented as
    'last seen' (not 'still seen') — useful for distinguishing
    fixed-bugs vs persistent-bugs."""
    run_num = int(run_number)

    # Append this run to the runs array (cap history to last 50 runs)
    trends.setdefault("runs", []).append({
        "run_number": run_num,
        "run_url":    run_url,
        "passed":     totals.get("total_passed", 0),
        "failed":     totals.get("total_failed", 0),
        "total":      totals.get("total_tests", 0),
        "bugs":       totals.get("total_bugs", 0),
        "pass_rate":  totals.get("pass_rate", "N/A"),
    })
    trends["runs"] = trends["runs"][-50:]

    # Update fingerprint records
    fp_db: dict = trends.setdefault("fingerprints", {})
    seen = set(fingerprints_seen)
    for fp in seen:
        if fp not in fp_db:
            fp_db[fp] = {
                "first_seen_run": run_num,
                "last_seen_run":  run_num,
                "runs_seen":      [run_num],
            }
        else:
            fp_db[fp]["last_seen_run"] = run_num
            runs = fp_db[fp].setdefault("runs_seen", [])
            if run_num not in runs:
                runs.append(run_num)
            fp_db[fp]["runs_seen"] = runs[-30:]  # cap

    return trends


def fingerprint_recurrence_count(trends: dict, fp: str) -> int:
    """How many times has this fingerprint been seen across runs?"""
    return len(trends.get("fingerprints", {}).get(fp, {}).get("runs_seen", []))


def is_persistent_bug(trends: dict, fp: str, threshold: int = 3) -> bool:
    """A bug is 'persistent' if it has been seen in ≥ threshold runs."""
    return fingerprint_recurrence_count(trends, fp) >= threshold
