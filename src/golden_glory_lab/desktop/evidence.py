"""Evidence-gated BUILD-001 availability presentation.

These are nonnumeric derived statuses. No mechanics formula is implemented in
this module or elsewhere in BUILD-001.
"""

from __future__ import annotations

from typing import Any

MECHANICS_STATUS = "unavailable-pending-evidence"

_UNAVAILABLE = (
    (
        "derived-permanent-mercenary-sheet-values",
        "Derived permanent-Mercenary sheet values",
        "Field semantics, equipment inclusion, and comparable context remain unknown.",
        ("AUD-002-C03", "AUD-002-C04", "AUD-002-C05"),
    ),
    (
        "complete-light-radius-direct-link",
        "Complete Light Radius/direct-Link calculation",
        "Complete sources, condition activation, stacking, order, and rounding are not established.",
        ("AUD-003-C08", "AUD-003-C12"),
    ),
    (
        "golden-glory-arithmetic",
        "Golden Glory arithmetic",
        "The literal relation is known, but the numeric operation and cross-path order are not.",
        ("AUD-003-C12", "AUD-004-C09"),
    ),
    (
        "definitive-flame-link-granted-damage",
        "Definitive Flame Link granted damage",
        "Effect arithmetic and live-game rounding remain below their evidence gates.",
        ("AUD-003-C12", "AUD-004-C09", "AUD-004-C10"),
    ),
    (
        "sheet-derived-or-aggregate-enmity",
        "Sheet-derived or aggregate Enmity",
        "Sheet derivation, penalty behavior, and aggregation remain unsupported.",
        (
            "AUD-002-C03",
            "AUD-002-C04",
            "AUD-002-C05",
            "AUD-005-C05",
            "AUD-005-C06",
            "AUD-005-C07",
        ),
    ),
    (
        "total-penetration",
        "Total penetration",
        "Aggregation with other penetration and enemy-resistance order are unknown.",
        ("AUD-005-C07",),
    ),
    (
        "damage-and-dps",
        "Damage and DPS",
        "BUILD-001 has no combat model and Flame Link granted damage is not DPS.",
        ("AUD-004-C12", "AUD-005-C07"),
    ),
)


def mechanics_availability() -> list[dict[str, Any]]:
    return [
        {
            "id": identifier,
            "label": label,
            "status": MECHANICS_STATUS,
            "value": None,
            "explanation": explanation,
            "claimReferences": list(claims),
        }
        for identifier, label, explanation, claims in _UNAVAILABLE
    ]
