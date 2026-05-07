"""
Spec-directive parser — honors author-written skip directives in .md spec files.

When a user writes things like:
    - Don't test phone responsiveness
    - Skip mobile viewport
    - Ignore RTL tests
    - Do not test OTP flow

…we extract those phrases and filter out matching test types / individual
tests at runtime so we never run what the spec author asked us to skip.

Public API:
    parsed = parse_directives_for_spec(spec_path)
    if should_skip_test_type(parsed, "responsive"):    # → True if matched
    if should_skip_test_name(parsed, "test_qa01_otp_input_appears_after_send_code"):

Used by:
    • ai_engine/test_generator.py  — drops whole test types from generation
    • tests/test_qa_comprehensive.py — pytest skip_if hook reads these too
    • scripts/consolidate_reports.py — reports show "skipped per spec directive"
"""
from __future__ import annotations
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Iterable

# ─── Regex catalog: phrases that mean "skip this" ─────────────────────────
# The pattern matches a directive verb + (optional filler) + a target phrase
# all the way to end-of-sentence. The captured target phrase is what we
# match against test types/names.
_DIRECTIVE_VERBS = (
    r"don'?t test",
    r"do\s*n'?t test",
    r"do not test",
    r"skip",
    r"ignore",
    r"exclude",
    r"omit",
    r"no need to test",
    r"avoid testing",
    r"please skip",
    r"please ignore",
    r"please don'?t test",
    r"please do not test",
    r"please exclude",
)
_DIRECTIVE_PATTERN = re.compile(
    r"(?im)^\s*[-*•]?\s*("
    r"(?:" + r"|".join(_DIRECTIVE_VERBS) + r")"
    r")\s+(.{2,140}?)(?:[.!?\n]|$)"
)

# ─── Canonical test types we know about (from test_generator.py + QA classes) ─
KNOWN_TEST_TYPES = {
    "smoke", "functional", "validation", "negative", "boundary",
    "data_driven", "deep_form", "security", "api_network",
    "accessibility", "responsive", "navigation", "session_auth",
    "performance", "console_errors", "error_states", "visual",
    "cross_browser", "i18n", "rate_limiting", "cookie_storage",
    # Phase 2/3 additions:
    "security_headers", "cookies", "owasp",
    "lighthouse", "memory_leak", "network_resilience",
    "visual_regression", "js_errors",
}

# ─── Synonym map: phrase fragment → canonical test_type token ─────────────
# Order matters: more specific phrases first.
_SYNONYM_MAP: list[tuple[str, str]] = [
    # i18n / locale
    (r"\bi18n\b|\binternationaliz",                 "i18n"),
    (r"\brtl\b|\barabic\b|\blocali[sz]ation\b",     "i18n"),
    (r"\blanguage[\s-]?switch",                      "i18n"),
    # responsive / mobile
    (r"\bresponsiv|\bmobile[\s-]?viewport|\bbreakpoint",  "responsive"),
    (r"\bmobile\b",                                  "responsive"),
    (r"\bphone[\s-]?(responsiv|view|mobile)",       "responsive"),
    # accessibility
    (r"\baccessibility\b|\ba11y\b|\bwcag\b|\bscreen[\s-]?reader",  "accessibility"),
    (r"\bkeyboard[\s-]?(?:nav|access)",              "accessibility"),
    # security / OWASP
    (r"\bxss\b",                                     "security"),
    (r"\bsqli?\b|\bsql[\s-]?injection",              "security"),
    (r"\bcsrf\b",                                    "security"),
    (r"\bsecurity[\s-]?header",                      "security_headers"),
    (r"\bcookie[\s-]?(security|flag)",               "cookies"),
    (r"\bowasp\b",                                   "owasp"),
    (r"\bsecurity\b",                                "security"),
    # performance
    (r"\bperformance\b|\bspeed\b|\blcp\b|\bcls\b|\bttfb\b",  "performance"),
    (r"\blighthouse\b|\bcore[\s-]?web[\s-]?vitals",  "lighthouse"),
    (r"\bmemory[\s-]?leak|\bheap[\s-]?growth",       "memory_leak"),
    # network
    (r"\bnetwork\b|\boffline\b|\b3g\b|\bthrottl",    "network_resilience"),
    (r"\bapi\b",                                     "api_network"),
    # visual / UI
    (r"\bvisual[\s-]?regression|\bpixel[\s-]?diff",  "visual_regression"),
    (r"\bvisual\b|\bui[\s-]?regression",             "visual"),
    (r"\bcross[\s-]?browser|\bfirefox|\bsafari",     "cross_browser"),
    # SEO
    (r"\bseo\b|\bmeta[\s-]?tag",                     "seo"),
    # functional buckets
    (r"\bsmoke\b",                                   "smoke"),
    (r"\bfunctional\b",                              "functional"),
    (r"\bvalidation\b",                              "validation"),
    (r"\bnegative\b",                                "negative"),
    (r"\bboundary\b|\bedge[\s-]?case",                "boundary"),
    (r"\bsession\b|\bauth(?:entication)?",          "session_auth"),
    (r"\botp\b|\bsend[\s-]?code|\bverification[\s-]?code",  "otp"),
    (r"\bhallucinat",                                "hallucination"),
    (r"\bconsole[\s-]?error|\bjs[\s-]?error|\bjavascript[\s-]?error", "js_errors"),
    (r"\b(rate[\s-]?limit|throttle)",                "rate_limiting"),
]


@dataclass
class SpecDirectives:
    """What the spec author asked us to skip for this spec."""
    spec_path:           Path
    raw_directives:      list[str]   = field(default_factory=list)
    skip_test_types:     set[str]    = field(default_factory=set)
    skip_keywords:       set[str]    = field(default_factory=set)  # general substrings

    def empty(self) -> bool:
        return not self.skip_test_types and not self.skip_keywords


# Stop-words that, when alone, indicate a non-actionable directive (e.g. "skip
# this" without saying what "this" refers to). Anything else is treated as a
# real skip target.
_NOISE_TARGETS = {"this", "that", "it", "them", "test", "tests", "step",
                   "section", "if needed", "for now"}


def _extract_directives(md_text: str) -> list[tuple[str, str]]:
    """Return a list of (verb, target_phrase) tuples from the spec text."""
    out: list[tuple[str, str]] = []
    for m in _DIRECTIVE_PATTERN.finditer(md_text):
        verb   = m.group(1).strip().lower()
        target = m.group(2).strip().strip("`*_")
        # Drop only true noise: single-word targets that are stop-words like
        # "this"/"test". A specific target like "XSS" or "OTP" is kept.
        if target.lower() in _NOISE_TARGETS:
            continue
        out.append((verb, target))
    return out


def _phrase_to_canonical_types(phrase: str) -> set[str]:
    """Map a free-text phrase to one or more canonical test_type tokens."""
    phrase = phrase.lower()
    found: set[str] = set()
    for pattern, canonical in _SYNONYM_MAP:
        if re.search(pattern, phrase):
            found.add(canonical)
    # If phrase mentions an exact canonical type, include it directly
    for word in re.findall(r"[a-z_]+", phrase):
        if word in KNOWN_TEST_TYPES:
            found.add(word)
    return found


def parse_directives_for_spec(spec_path: str | Path) -> SpecDirectives:
    """Parse one .md spec for skip directives. Returns SpecDirectives.

    Empty / non-existent file returns an empty SpecDirectives — never raises."""
    p = Path(spec_path)
    out = SpecDirectives(spec_path=p)
    if not p.exists() or not p.is_file():
        return out
    try:
        text = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return out

    for verb, target in _extract_directives(text):
        out.raw_directives.append(f"{verb}: {target}")
        canonicals = _phrase_to_canonical_types(target)
        out.skip_test_types.update(canonicals)
        # Keep original keywords too — used for fuzzy test-name matching
        for word in re.findall(r"[a-zA-Z][a-zA-Z\-_]+", target):
            w = word.lower()
            if len(w) >= 4:
                out.skip_keywords.add(w)
    return out


def parse_directives_dir(specs_dir: str | Path) -> dict[str, SpecDirectives]:
    """Parse every *.md under specs_dir. Returns {spec_stem: SpecDirectives}."""
    sd = Path(specs_dir)
    out: dict[str, SpecDirectives] = {}
    if not sd.exists():
        return out
    for md in sd.glob("*.md"):
        out[md.stem] = parse_directives_for_spec(md)
    return out


def should_skip_test_type(directives: SpecDirectives, test_type: str) -> bool:
    """Return True if `test_type` matches a skip directive in this spec."""
    if not directives or directives.empty():
        return False
    return test_type.lower() in directives.skip_test_types


def should_skip_test_name(directives: SpecDirectives,
                           test_name: str) -> tuple[bool, str]:
    """Return (skip?, reason). Used by pytest skip hooks."""
    if not directives or directives.empty():
        return False, ""
    nm = test_name.lower()
    # 1. Direct test_type match (e.g. "responsive" → tests with "responsive" prefix)
    for tt in directives.skip_test_types:
        if tt in nm:
            return True, f"skipped per spec directive: type='{tt}'"
    # 2. Keyword match — at least 2 keywords from the directive must hit
    matches = [k for k in directives.skip_keywords if k in nm]
    if len(matches) >= 2:
        return True, f"skipped per spec directive: keywords={matches[:3]}"
    return False, ""


# ─── Aggregate API: union of directives across all specs in the project ───
# Used by pytest hooks where we don't know which spec a test came from.

_AGGREGATE: SpecDirectives | None = None


def aggregate_directives(specs_dir: str | Path = "specs") -> SpecDirectives:
    """Cached union of all spec directives (used by pytest collection hook)."""
    global _AGGREGATE
    if _AGGREGATE is not None:
        return _AGGREGATE
    agg = SpecDirectives(spec_path=Path(specs_dir))
    for sd in parse_directives_dir(specs_dir).values():
        agg.raw_directives.extend(sd.raw_directives)
        agg.skip_test_types.update(sd.skip_test_types)
        agg.skip_keywords.update(sd.skip_keywords)
    _AGGREGATE = agg
    return agg


def reset_cache() -> None:
    """For tests — discard the aggregate cache."""
    global _AGGREGATE
    _AGGREGATE = None
