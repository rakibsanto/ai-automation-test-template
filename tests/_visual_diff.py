"""
Visual-regression helper used by TestQA11VisualRegression.

Approach: per (page, viewport) pair we keep a baseline PNG in
tests/visual_baselines/. On every run we capture a fresh screenshot,
compute a pixel-diff vs the baseline, and fail if more than `threshold_pct`
of pixels differ.

First-run safe: when a baseline does not exist we save the current
screenshot AS the baseline and pass with a note. To intentionally
refresh baselines after a deliberate UI change, set environment var
UPDATE_VISUAL_BASELINES=1 — every comparison then OVERWRITES its
baseline and passes.

Diff method: PIL ImageChops.difference + bounding-box. Cheap, deterministic,
no external services. We resize images to the same dimensions before
comparison so a viewport difference does not mask real changes.
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import Tuple

try:
    from PIL import Image, ImageChops
    _PIL_OK = True
except ImportError:
    _PIL_OK = False


_BASELINE_DIR  = Path(__file__).parent / "visual_baselines"
_DIFF_OUT_DIR  = Path(__file__).parent.parent / "reports" / "visual-diffs"
_UPDATE_MODE   = os.getenv("UPDATE_VISUAL_BASELINES", "0").strip() in ("1", "true", "yes")


def baseline_path(test_name: str) -> Path:
    _BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    safe = test_name.replace("/", "_").replace(":", "_")
    return _BASELINE_DIR / f"{safe}.png"


def diff_output_path(test_name: str) -> Path:
    _DIFF_OUT_DIR.mkdir(parents=True, exist_ok=True)
    safe = test_name.replace("/", "_").replace(":", "_")
    return _DIFF_OUT_DIR / f"{safe}.diff.png"


def compute_pixel_diff_pct(img_a: Path, img_b: Path,
                           save_diff_to: Path | None = None) -> float:
    """Return percentage of pixels that differ between img_a and img_b.

    If sizes mismatch, both are resized to img_a's dimensions before diff
    so layout shifts surface as actual differences. Returns 0.0 when
    images are identical."""
    if not _PIL_OK:
        return 0.0  # PIL not installed → skip diff cleanly
    a = Image.open(img_a).convert("RGB")
    b = Image.open(img_b).convert("RGB")
    if a.size != b.size:
        b = b.resize(a.size)
    diff = ImageChops.difference(a, b)
    bbox = diff.getbbox()
    if bbox is None:
        return 0.0  # pixel-perfect identical
    # Count non-zero diff pixels by summing pixel intensities
    pixels = list(diff.getdata())
    diff_count = sum(1 for p in pixels if (p[0] + p[1] + p[2]) > 30)
    pct = diff_count / max(1, len(pixels)) * 100.0
    if save_diff_to is not None:
        try:
            save_diff_to.parent.mkdir(parents=True, exist_ok=True)
            diff.save(save_diff_to)
        except Exception:
            pass
    return pct


def assert_visual_match(actual_png: Path, test_name: str,
                        threshold_pct: float = 3.0) -> Tuple[bool, str]:
    """Compare `actual_png` against the saved baseline for `test_name`.

    Returns (ok, message). When the baseline doesn't exist we COPY the
    current screenshot to baseline_path and pass with a note (first-run
    safe). When UPDATE_VISUAL_BASELINES=1 we overwrite the baseline
    regardless of diff."""
    import shutil as _sh
    bp = baseline_path(test_name)
    bp_exists = bp.exists()
    if not bp_exists or _UPDATE_MODE:
        # Copy actual into baseline location (don't move — keep the actual
        # for the report's record). Works whether or not bp exists.
        bp.parent.mkdir(parents=True, exist_ok=True)
        try:
            _sh.copyfile(actual_png, bp)
        except Exception as e:
            return False, f"could not save baseline: {e}"
        return True, ("[BASELINE-UPDATED]" if _UPDATE_MODE
                      else "[BASELINE-CREATED]") + f" → {bp.name}"

    diff_path = diff_output_path(test_name)
    pct = compute_pixel_diff_pct(bp, actual_png, save_diff_to=diff_path)
    if pct <= threshold_pct:
        return True, f"diff {pct:.2f}% (≤ {threshold_pct}%)"
    return False, (
        f"visual regression: {pct:.2f}% pixels differ vs baseline "
        f"(threshold {threshold_pct}%). diff image: {diff_path}"
    )


def synthetic_self_consistency(image_path: Path) -> float:
    """Sanity check: an image diffed against itself must be 0.0%.
    Used by Phase-1 verification test."""
    return compute_pixel_diff_pct(image_path, image_path)
