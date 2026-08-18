"""Unit tests for category auto-activation wiring.

Pure-Python surface — no FreeCAD needed. Covers:

  * ``_parse_categories`` — spec-field normalization (list / string /
    comma / junk).
  * ``detect_categories`` — name→category token matching, whole-token
    (not substring) semantics, and specific-over-generic precedence.
  * ``resolve_categories`` — explicit field wins over auto-detect;
    unknown names are skipped.

The end-to-end score lift these produce (a gear ground-truth model
scoring 1.0 against itself) is covered in the ``needs_freecad``
integration test.
"""
from __future__ import annotations

from freecad_validator.consistency.categories.registry import (
    CATEGORY_REGISTRY,
    detect_categories,
    resolve_categories,
)
from freecad_validator.spec.parser import _parse_categories, parse_spec

# --- _parse_categories ------------------------------------------------------

def test_parse_categories_accepts_list():
    assert _parse_categories(["Gear", "HEX"]) == ["gear", "hex"]


def test_parse_categories_accepts_comma_string():
    assert _parse_categories("gear, washer") == ["gear", "washer"]
    assert _parse_categories("gear") == ["gear"]


def test_parse_categories_tolerates_junk():
    # None / numbers / empty entries never raise — just yield [].
    assert _parse_categories(None) == []
    assert _parse_categories(42) == []
    assert _parse_categories(["", "  ", "gear"]) == ["gear"]


def test_parse_spec_populates_categories_field():
    spec = parse_spec({"name": "x", "key_parameters": "", "categories": ["gear"]})
    assert spec.categories == ["gear"]
    # Absent field → empty list, never None.
    assert parse_spec({"name": "x", "key_parameters": ""}).categories == []


# --- detect_categories ------------------------------------------------------

def test_detect_plain_gear():
    assert detect_categories("spur gear") == ["gear"]
    assert detect_categories("spur gear stock") == ["gear"]


def test_detect_helical_gear_suppresses_plain_gear():
    # "helical gear" contains the "gear" token but must resolve to the
    # more-specific helical_gear only.
    assert detect_categories("helical gear") == ["helical_gear"]


def test_keyway_does_not_trigger_key():
    # Whole-token match: "keyway" must not match the "key" category.
    assert detect_categories("shaft with keyway") == ["keyway"]
    assert detect_categories("round_key") == ["key"]


def test_detect_splits_hyphens_and_underscores():
    # "external-hex" → {external, hex}; "disc_spring" → {disc, spring}.
    assert detect_categories("external-hex coupling nut") == ["hex"]
    assert detect_categories("disc_spring") == ["spring"]


def test_detect_no_match_returns_empty():
    assert detect_categories("smooth shaft") == []
    assert detect_categories("lego brick") == []


# --- resolve_categories -----------------------------------------------------

def test_explicit_field_wins_over_name():
    # Name says gear, but the explicit field says hex → honor the field.
    spec = parse_spec({"name": "spur gear", "key_parameters": "",
                       "categories": ["hex"]})
    assert [c.name for c in resolve_categories(spec)] == ["hex"]


def test_auto_detect_when_no_explicit_field():
    spec = parse_spec({"name": "spur gear", "key_parameters": ""})
    assert [c.name for c in resolve_categories(spec)] == ["gear"]


def test_unknown_explicit_name_is_skipped():
    spec = parse_spec({"name": "x", "key_parameters": "",
                       "categories": ["bogus", "gear"]})
    assert [c.name for c in resolve_categories(spec)] == ["gear"]


def test_registry_covers_every_category_module():
    # Guards against adding a categories/*.py without registering it.
    assert len(CATEGORY_REGISTRY) == 15
    assert "gear" in CATEGORY_REGISTRY
    assert all(name == cat.name for name, cat in CATEGORY_REGISTRY.items())
