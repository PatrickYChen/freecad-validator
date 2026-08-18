"""Category registry + name-based auto-detection.

The ``categories/`` package holds one :class:`Category` subclass per
part family (gear, hex, washer, …). Each derives the "virtual" spec
params that have no directly-measurable face — a spur gear's
``pitch_diameter`` / ``module`` / ``addendum`` live in gear geometry,
not in any single circle the generic checks can anchor to.

Historically the only way to activate a category was to drop a
hand-written ``param_check.py`` next to the case's FCStd. The published
benchmark specs don't ship one, so the categories never ran and every
gear ground-truth model scored well below 1.0 against itself. This
module closes that gap: it exposes the categories as a name→instance
registry and infers which apply from the part name, so the checker can
activate them with no per-case file.

Two selection paths, resolved in :func:`resolve_categories`:

  1. **Explicit** — a spec's ``categories: ["gear", …]`` field (the
     field documented in the README). Author-controlled; wins outright
     when present.
  2. **Auto-detect** — :func:`detect_categories` maps the part *name*
     to categories by token match. Used only when the spec declares no
     explicit categories, so existing specs benefit with zero edits.

Auto-detection is conservative-by-construction: every category also
gates on geometry (and several, like key/washer, additionally gate on
the name), so a category matched to the wrong part derives nothing and
is a no-op. Reclassification can only move a finding
``not_found``/``inconsistent`` → ``consistent`` when the derived value
agrees with the spec, so an over-eager match can never *lower* a score.
"""
from __future__ import annotations

import logging
import re

from freecad_validator.consistency.categories.base import Category
from freecad_validator.consistency.categories.box import BoxCategory
from freecad_validator.consistency.categories.flange_plate import FlangePlateCategory
from freecad_validator.consistency.categories.gear import GearCategory
from freecad_validator.consistency.categories.helical_gear import HelicalGearCategory
from freecad_validator.consistency.categories.hex import HexCategory
from freecad_validator.consistency.categories.impeller import ImpellerCategory
from freecad_validator.consistency.categories.key import KeyCategory
from freecad_validator.consistency.categories.keyway import KeywayCategory
from freecad_validator.consistency.categories.pin import PinCategory
from freecad_validator.consistency.categories.pipe_elbow import PipeElbowCategory
from freecad_validator.consistency.categories.pulley import PulleyCategory
from freecad_validator.consistency.categories.spline import SplineCategory
from freecad_validator.consistency.categories.spring import SpringCategory
from freecad_validator.consistency.categories.spring_clip import SpringClipCategory
from freecad_validator.consistency.categories.washer import WasherCategory
from freecad_validator.spec.parser import StructuredSpec

log = logging.getLogger(__name__)

# name → singleton instance. Categories are stateless, so one shared
# instance per family is safe to reuse across every case in a batch.
CATEGORY_REGISTRY: dict[str, Category] = {
    c.name: c
    for c in (
        BoxCategory(),
        FlangePlateCategory(),
        GearCategory(),
        HelicalGearCategory(),
        HexCategory(),
        ImpellerCategory(),
        KeyCategory(),
        KeywayCategory(),
        PinCategory(),
        PipeElbowCategory(),
        PulleyCategory(),
        SplineCategory(),
        SpringCategory(),
        SpringClipCategory(),
        WasherCategory(),
    )
}

# Part-name token → category name. A category fires when ANY of its
# tokens appears as a whole word in the tokenized part name. Kept as
# whole-token matches (not substrings) so ``keyway`` doesn't trip the
# ``key`` category and ``helical`` is distinguishable from a plain gear.
_NAME_TOKENS: dict[str, frozenset[str]] = {
    "helical_gear": frozenset({"helical"}),
    "gear":         frozenset({"gear"}),
    "spline":       frozenset({"spline"}),
    "keyway":       frozenset({"keyway"}),
    "key":          frozenset({"key"}),
    "hex":          frozenset({"hex"}),
    "washer":       frozenset({"washer"}),
    "pin":          frozenset({"pin"}),
    "flange_plate": frozenset({"flange", "plate"}),
    "pipe_elbow":   frozenset({"elbow"}),
    "spring_clip":  frozenset({"clip"}),
    "spring":       frozenset({"spring"}),
    "pulley":       frozenset({"pulley"}),
    "impeller":     frozenset({"impeller"}),
    "box":          frozenset({"box", "drawer"}),
}

# When the more-specific family is detected, drop the generic one it
# subsumes so the generic doesn't derive against the wrong geometry.
# (helical gears are not plain spur gears; a spring clip is not a coil
# spring.) Keyed generic → specific-that-suppresses-it.
_SUPPRESSED_BY: dict[str, str] = {
    "gear": "helical_gear",
    "spring": "spring_clip",
}

_TOKEN_SPLIT_RE = re.compile(r"[^a-z0-9]+")


def _name_tokens(name: str) -> frozenset[str]:
    """Lowercase the part name and split on any non-alphanumeric run, so
    ``external-hex coupling nut`` → {external, hex, coupling, nut} and
    ``disc_spring`` → {disc, spring}. Whole-token matching then keeps
    ``keyway`` from matching the ``key`` category."""
    return frozenset(t for t in _TOKEN_SPLIT_RE.split(name.lower()) if t)


def detect_categories(name: str) -> list[str]:
    """Category names whose keywords appear as whole tokens in the part
    ``name``, most-specific first, with subsumed generics removed.

    Returns ``[]`` when nothing matches (the common case for a plain
    prismatic part with no family). Order matters only cosmetically —
    reclassification is order-independent since a param, once
    ``consistent``, is never revisited."""
    toks = _name_tokens(name)
    matched = {
        cat for cat, keywords in _NAME_TOKENS.items() if keywords & toks
    }
    for generic, specific in _SUPPRESSED_BY.items():
        if specific in matched:
            matched.discard(generic)
    # Emit in the fixed _NAME_TOKENS order (specific families are listed
    # first) so logs/reports read deterministically.
    return [cat for cat in _NAME_TOKENS if cat in matched]


def resolve_categories(spec: StructuredSpec) -> list[Category]:
    """The categories to apply for ``spec``.

    Explicit ``spec.categories`` wins when non-empty (unknown names are
    warned about and skipped); otherwise fall back to name-based
    :func:`detect_categories`. Returns instances from
    :data:`CATEGORY_REGISTRY`, ready to ``apply()``.
    """
    if spec.categories:
        names: list[str] = []
        for raw in spec.categories:
            key = raw.strip().lower()
            if key in CATEGORY_REGISTRY:
                names.append(key)
            else:
                log.warning(
                    "unknown category %r (known: %s)",
                    raw, ", ".join(sorted(CATEGORY_REGISTRY)),
                )
    else:
        names = detect_categories(spec.name)
    return [CATEGORY_REGISTRY[n] for n in names]
