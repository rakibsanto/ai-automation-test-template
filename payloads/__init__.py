"""Security payload loader for authorized testing of your own application."""
from pathlib import Path

_DIR = Path(__file__).parent

def load(name: str) -> list[str]:
    """Load payloads from a txt file. Returns list of non-empty lines."""
    f = _DIR / f"{name}.txt"
    if not f.exists():
        return []
    return [l.strip() for l in f.read_text().splitlines()
            if l.strip() and not l.startswith("#")]

XSS      = load("xss")
SQLI     = load("sqli")
BOUNDARY = load("boundary")

# Quick subsets are now broader — the per-spec security generator uses these
# directly via parametrize, so a larger QUICK list means more tests per spec
# without the agent emitting more code (parametrize multiplies cheaply).
XSS_QUICK      = XSS[:50]
SQLI_QUICK     = SQLI[:50]
BOUNDARY_QUICK = BOUNDARY[:50]
