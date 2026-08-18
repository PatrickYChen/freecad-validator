"""End-to-end: built-in categories activate without a param_check.py.

These run the real :class:`ConsistencyChecker` against a committed
spur-gear ground-truth fixture. They require FreeCAD (marked
``needs_freecad``) and are skipped on hosts without it.

The regression they lock down: before category auto-activation, a gear
ground-truth model scored ~0.53 against *its own spec* because the
derived gear params (``pitch_diameter``, ``gear_module``, ``addendum``,
``dedendum``, ``circular_pitch``, ``tooth_thickness``) had no
generic-check anchor. With the gear category reachable, a ground-truth
model scores a perfect self-match.
"""
from __future__ import annotations

from pathlib import Path

import pytest

import freecad_validator.consistency.checker as checker_mod
from freecad_validator.consistency.checker import ConsistencyChecker
from freecad_validator.spec.parser import load_spec_json

_GEAR_CASE = Path(__file__).resolve().parent.parent / "fixtures" / "spur_gear"

pytestmark = pytest.mark.needs_freecad


def _score(spec: dict) -> float:
    fcstd = str(_GEAR_CASE / "reference.FCStd")
    return ConsistencyChecker().check(spec, fcstd).summary.consistency_rate


def test_gear_ground_truth_self_matches_perfectly():
    """Auto-detected from the ``spur gear`` name (no categories field,
    no param_check.py) — the ground truth should score 1.0 on itself."""
    spec = load_spec_json(_GEAR_CASE / "spec.json")
    assert "categories" not in spec  # relies purely on name auto-detect
    assert _score(spec) == pytest.approx(1.0)


def test_disabling_categories_reproduces_the_old_ceiling():
    """With category resolution stubbed out, the same case falls back to
    the generic-only score (well below 1.0) — proving the categories are
    what closes the gap, not some other change."""
    spec = load_spec_json(_GEAR_CASE / "spec.json")
    orig = checker_mod.resolve_categories
    checker_mod.resolve_categories = lambda _spec: []
    try:
        generic_only = _score(spec)
    finally:
        checker_mod.resolve_categories = orig
    assert generic_only < 0.75
    assert _score(spec) > generic_only  # re-enabled path beats it


def test_explicit_categories_field_activates_gear():
    """An explicit ``categories: ["gear"]`` reaches the same 1.0 even if
    the name wouldn't auto-detect (here it would, but the field is the
    author-controlled path)."""
    spec = load_spec_json(_GEAR_CASE / "spec.json")
    spec["categories"] = ["gear"]
    assert _score(spec) == pytest.approx(1.0)
