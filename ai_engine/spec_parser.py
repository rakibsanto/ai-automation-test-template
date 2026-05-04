"""
Parses a structured .md spec file into sections the AI can process
one focused chunk at a time — prevents token overflow.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ParsedSpec:
    page_name: str
    slug: str                        # e.g. "login", "reset-password"
    url: str
    path: str                        # e.g. "/login"
    requirements: list[str]
    flows: list[dict]                # [{name, steps:[str]}]
    edge_cases: list[dict]           # [{id, scenario, expected}]
    validation_rules: list[str]
    test_data_valid: list[str]
    test_data_invalid: list[str]
    security_inputs: list[str]
    api_endpoints: list[dict]        # [{method, endpoint, trigger}]
    raw: str                         # full original text (for fallback)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _between(text: str, start_heading: str, stop_headings: list[str]) -> str:
    """Extract text between start_heading and the next matching stop heading."""
    pattern = re.escape(start_heading)
    starts = list(re.finditer(pattern, text, re.IGNORECASE))
    if not starts:
        return ""
    pos = starts[0].end()
    chunk = text[pos:]
    for stop in stop_headings:
        m = re.search(r"^#{1,3}\s+" + re.escape(stop), chunk, re.MULTILINE | re.IGNORECASE)
        if m:
            chunk = chunk[: m.start()]
    return chunk.strip()


def _lines(text: str) -> list[str]:
    return [l.strip() for l in text.splitlines() if l.strip()]


# ── Parser ────────────────────────────────────────────────────────────────────

def parse(spec_path: Path) -> ParsedSpec:
    raw = spec_path.read_text()
    slug = spec_path.stem
    page_name = slug.replace("-", " ").title()

    # ── URL / path ────────────────────────────────────────────────────────────
    url_match = re.search(r"\*\*URL:\*\*\s*`(.+?)`", raw)
    url = url_match.group(1).strip() if url_match else ""
    path_match = re.search(r"https?://[^/]+(/[^\s`\)]+)", url)
    path = path_match.group(1) if path_match else f"/{slug}"

    # ── Requirements ──────────────────────────────────────────────────────────
    requirements = re.findall(r"(REQ-[A-Z\-\d]+:.+)", raw)

    # ── User flows ────────────────────────────────────────────────────────────
    flows_section = _between(raw, "## User Flows", ["## Validation", "## Edge", "## Expected", "## Test Data", "## API"])
    flow_blocks = re.split(r"###\s+Flow\s+\d+", flows_section, flags=re.IGNORECASE)
    flows = []
    for i, block in enumerate(flow_blocks):
        if not block.strip():
            continue
        title_m = re.match(r":?\s*(.+)", block.strip())
        title = title_m.group(1).split("\n")[0].strip() if title_m else f"Flow {i}"
        steps = re.findall(r"\d+\.\s+(.+)", block)
        if steps:
            flows.append({"name": title[:60], "steps": steps[:10]})

    # ── Edge cases (table) ────────────────────────────────────────────────────
    edge_cases = []
    for row in re.finditer(
        r"\|\s*(EC-[A-Z\-\d]+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|", raw
    ):
        edge_cases.append({
            "id":       row.group(1),
            "scenario": row.group(2).strip(),
            "expected": row.group(3).strip(),
        })

    # ── Validation rules ──────────────────────────────────────────────────────
    val_section = _between(raw, "## Validation Rules", ["## Edge", "## Expected", "## Test Data", "## API"])
    validation_rules = [l for l in _lines(val_section) if l.startswith("-") or re.match(r"###|Must|Should|Required", l)]

    # ── Test data ─────────────────────────────────────────────────────────────
    td_section = _between(raw, "## Test Data", ["## API", "## Related", "## Coverage"])
    valid_block   = _between(td_section, "### Valid",   ["### Invalid", "### Malformed", "### Injection"])
    invalid_block = _between(td_section, "### Invalid", ["### Injection", "### Security", "---"])
    security_block= _between(td_section, "### Injection", ["---", "##"])
    if not security_block:
        security_block = _between(td_section, "### Security", ["---", "##"])

    td_valid    = [l for l in _lines(valid_block)   if l.startswith(("email:", "password:", "name:", "username:"))]
    td_invalid  = [l for l in _lines(invalid_block) if l.startswith(("email:", "password:", "name:"))]
    td_security = [l for l in _lines(security_block) if l.startswith(("email:", "name:", "password:"))]

    # ── API endpoints ─────────────────────────────────────────────────────────
    api_endpoints = []
    for row in re.finditer(r"\|\s*(GET|POST|PUT|DELETE|PATCH)\s*\|\s*(`?.+?`?)\s*\|", raw):
        api_endpoints.append({
            "method":   row.group(1),
            "endpoint": row.group(2).strip("`").strip(),
        })

    return ParsedSpec(
        page_name=page_name,
        slug=slug,
        url=url,
        path=path,
        requirements=requirements[:20],
        flows=flows[:8],
        edge_cases=edge_cases[:15],
        validation_rules=validation_rules[:15],
        test_data_valid=td_valid[:5],
        test_data_invalid=td_invalid[:8],
        security_inputs=td_security[:5],
        api_endpoints=api_endpoints[:6],
        raw=raw,
    )


# ── Section summaries for focused AI prompts ──────────────────────────────────

def flows_prompt_section(spec: ParsedSpec) -> str:
    if not spec.flows:
        return ""
    lines = [f"PAGE: {spec.page_name}  URL: {spec.url}\n"]
    for i, f in enumerate(spec.flows, 1):
        lines.append(f"FLOW {i}: {f['name']}")
        for s in f["steps"]:
            lines.append(f"  {s}")
    return "\n".join(lines)


def edge_cases_prompt_section(spec: ParsedSpec) -> str:
    if not spec.edge_cases:
        return ""
    lines = [f"PAGE: {spec.page_name}  URL: {spec.url}\n", "EDGE CASES:"]
    for ec in spec.edge_cases:
        lines.append(f"  {ec['id']}: Input={ec['scenario'][:80]} → Expected={ec['expected'][:80]}")
    return "\n".join(lines)


def validation_prompt_section(spec: ParsedSpec) -> str:
    parts = [f"PAGE: {spec.page_name}  URL: {spec.url}\n"]
    if spec.validation_rules:
        parts.append("VALIDATION RULES:")
        for r in spec.validation_rules[:10]:
            parts.append(f"  {r}")
    if spec.test_data_invalid:
        parts.append("\nINVALID TEST INPUTS:")
        for t in spec.test_data_invalid:
            parts.append(f"  {t}")
    return "\n".join(parts)


def security_prompt_section(spec: ParsedSpec) -> str:
    parts = [f"PAGE: {spec.page_name}  URL: {spec.url}\n", "SECURITY TEST INPUTS:"]
    inputs = spec.security_inputs or [
        "email: <script>alert(1)</script>@test.com",
        "email: ' OR '1'='1'--@test.com",
        "name: <img src=x onerror=alert(1)>",
    ]
    for s in inputs:
        parts.append(f"  {s}")
    return "\n".join(parts)
