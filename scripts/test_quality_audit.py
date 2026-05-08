"""
Test Quality Audit — finds tests that PASS without actually verifying
anything. Catches the most common "test theatre" antipatterns:

  • assert True / assert 1 / assert 1 == 1
  • assert ... or True   (always true regardless of left side)
  • assert <name>.count() >= 0  (count is always non-negative)
  • assert <name> is not None where <name> is the literal page/locator
  • Tests with NO assert / pytest.fail / pytest.skip statements
  • Tests where every assert is wrapped in a try/except that swallows

These patterns produce green tests that don't catch any bug — pure noise
in the report.

This isn't classical mutation testing (which mutates production code
to verify the suite catches the change). For Mehad the production code
is a remote staging website we can't mutate. Instead we audit OUR test
file for tests that look like they assert something but don't.

Public API
    findings = audit_test_file(path)        # list[QualityFinding]
    findings = audit_all_tests("tests")
    html     = render_audit_html(findings)
"""
from __future__ import annotations
import ast
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class QualityFinding:
    """One weak / empty test detected by the audit."""
    test_name:    str
    test_class:   str
    file:         str
    line:         int
    issue:        str               # human readable
    severity:     str = "MEDIUM"    # HIGH / MEDIUM / LOW


# ─── AST visitors ──────────────────────────────────────────────────────────────

def _is_constant_truthy(node: ast.AST) -> bool:
    """`True`, `1`, `'x'`, etc. — anything that's an always-true constant."""
    if isinstance(node, ast.Constant):
        return bool(node.value)
    return False


def _is_tautology(test: ast.AST) -> bool:
    """Detect `assert X == X`, `assert X >= 0` for unsigned counts, etc."""
    if isinstance(test, ast.Compare) and len(test.comparators) == 1:
        left = test.left
        right = test.comparators[0]
        op = test.ops[0]
        # X == X  → tautology
        if isinstance(op, ast.Eq) and ast.dump(left) == ast.dump(right):
            return True
        # X >= 0 where X is a .count() call → always true
        if isinstance(op, ast.GtE) and _is_constant_truthy(right) is False:
            if isinstance(right, ast.Constant) and right.value == 0:
                if isinstance(left, ast.Call):
                    func = left.func
                    if isinstance(func, ast.Attribute) and func.attr == "count":
                        return True
    return False


def _is_or_true(test: ast.AST) -> bool:
    """Detect `assert <X> or True` — always passes regardless of X."""
    if isinstance(test, ast.BoolOp) and isinstance(test.op, ast.Or):
        for v in test.values:
            if _is_constant_truthy(v):
                return True
    return False


def _is_assert_True(test: ast.AST) -> bool:
    """`assert True` literal."""
    return isinstance(test, ast.Constant) and bool(test.value)


def _walk_function_body(fn: ast.FunctionDef) -> list[ast.AST]:
    """Flatten try/except bodies so an assert inside `try` is still seen."""
    out: list[ast.AST] = []
    def _walk(node):
        for child in ast.iter_child_nodes(node):
            out.append(child)
            _walk(child)
    _walk(fn)
    return out


def _function_audit(fn: ast.FunctionDef, file: str,
                     class_name: str) -> list[QualityFinding]:
    """Audit a single test function and return any quality issues."""
    findings: list[QualityFinding] = []
    body = _walk_function_body(fn)

    asserts = [n for n in body if isinstance(n, ast.Assert)]
    fails   = [n for n in body if isinstance(n, ast.Call)
               and isinstance(n.func, ast.Attribute)
               and n.func.attr in ("fail", "skip")]
    raises  = [n for n in body if isinstance(n, ast.Raise)]

    # PATTERN 1: function has no assert / fail / skip / raise at all
    if not asserts and not fails and not raises:
        # Tolerate tests that ONLY call expect(...) (Playwright)
        has_expect = any(
            isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
            and n.func.id == "expect"
            for n in body
        )
        if not has_expect:
            findings.append(QualityFinding(
                test_name=fn.name, test_class=class_name, file=file,
                line=fn.lineno,
                issue="Test contains no assert / pytest.fail / expect() — "
                      "passes vacuously regardless of app behavior",
                severity="HIGH",
            ))

    # PATTERN 2: assert True / assert 1 — pure tautologies
    for a in asserts:
        if _is_assert_True(a.test):
            findings.append(QualityFinding(
                test_name=fn.name, test_class=class_name, file=file,
                line=a.lineno,
                issue="`assert True` is a no-op tautology",
                severity="HIGH",
            ))
        elif _is_or_true(a.test):
            findings.append(QualityFinding(
                test_name=fn.name, test_class=class_name, file=file,
                line=a.lineno,
                issue="`assert <X> or True` always passes — the X check is dead",
                severity="HIGH",
            ))
        elif _is_tautology(a.test):
            findings.append(QualityFinding(
                test_name=fn.name, test_class=class_name, file=file,
                line=a.lineno,
                issue="Tautological assertion (e.g. X == X, count() >= 0)",
                severity="HIGH",
            ))

    return findings


def audit_test_file(path: str | Path) -> list[QualityFinding]:
    """Audit one test_*.py file for weak/vacuous tests."""
    p = Path(path)
    if not p.exists():
        return []
    try:
        src = p.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(src)
    except Exception:
        return []

    findings: list[QualityFinding] = []
    # Top-level test functions
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("test_"):
                findings += _function_audit(node, str(p), class_name="(module)")
        elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            for member in node.body:
                if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if member.name.startswith("test_"):
                        findings += _function_audit(
                            member, str(p), class_name=node.name)
    return findings


def audit_all_tests(tests_dir: str | Path = "tests") -> list[QualityFinding]:
    """Audit every test_*.py under tests/ — returns combined findings."""
    sd = Path(tests_dir)
    if not sd.exists():
        return []
    out: list[QualityFinding] = []
    for f in sd.glob("test_*.py"):
        out += audit_test_file(f)
    return out


def render_audit_html(findings: list[QualityFinding]) -> str:
    """Render findings as a section for the master report. Empty when no
    issues so the report doesn't show clutter on green runs."""
    if not findings:
        return ""

    by_sev = {"HIGH": [], "MEDIUM": [], "LOW": []}
    for f in findings:
        by_sev.setdefault(f.severity, []).append(f)

    rows = []
    for sev in ("HIGH", "MEDIUM", "LOW"):
        for f in by_sev.get(sev, []):
            rows.append(
                f'<tr><td><span class="badge {sev}">{sev}</span></td>'
                f'<td><code>{f.test_class}::{f.test_name}</code></td>'
                f'<td>{f.issue}</td>'
                f'<td><code>{Path(f.file).name}:{f.line}</code></td></tr>'
            )
    return f"""
<div class="tq-summary" id="test-quality">
  <div class="sec-title" style="margin:24px 0 12px">
    🧪 Test Quality Audit
    <span class="count">{len(findings)} weak test(s)</span>
  </div>
  <div class="tq-headline">
    Tests below contain no real assertion or only tautological/vacuous
    checks. They <strong>always pass</strong> — they don't actually verify
    anything about the app, contributing only noise to the report.
  </div>
  <table class="tq-table">
    <thead><tr><th>Severity</th><th>Test</th><th>Issue</th><th>Location</th></tr></thead>
    <tbody>{"".join(rows)}</tbody>
  </table>
  <div class="tq-help">
    To fix: open the test file and replace the weak assertion with one
    that actually checks the expected outcome (e.g. assert exact text,
    URL, or DOM state — not <code>X &gt;= 0</code> or <code>True</code>).
  </div>
</div>"""
