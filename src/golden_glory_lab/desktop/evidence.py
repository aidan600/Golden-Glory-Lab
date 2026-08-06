"""Evidence-gated unavailable-output presentation for BUILD-003.

These are nonnumeric derived statuses for outputs that remain blocked. The
manual-first Flame Link player chain and isolated Enmity formulas live in the
domain package, not here.
"""

from __future__ import annotations

from typing import Any

MECHANICS_STATUS = "partial-manual-first"

_UNAVAILABLE = (
    (
        "derived-permanent-mercenary-sheet-values",
        "Derived permanent-Mercenary sheet values",
        "Field semantics, equipment inclusion, and comparable context remain unknown.",
        ("AUD-002-C03", "AUD-002-C04", "AUD-002-C05"),
    ),
    (
        "live-game-flame-link-rounding",
        "Live-game Flame Link rounding confirmation",
        "BUILD-003 ships a modelled nearest-integer half-up policy; live client rounding remains unconfirmed.",
        ("AUD-004-C09", "AUD-004-C10"),
    ),
    (
        "powerful-bond-auto-activation",
        "Powerful Bond automatic activation",
        "Conditional Powerful Bond / Inspiring Bond states remain explicit manual three-state inputs.",
        ("AUD-003-C08",),
    ),
    (
        "exhaustive-player-chain-recognition",
        "Exhaustive player-chain source recognition",
        "Recognition is bounded and advisory; reviewed manual totals remain authoritative.",
        ("AUD-003-C12",),
    ),
    (
        "sheet-derived-or-aggregate-enmity",
        "Sheet-derived or aggregate Enmity",
        "Sheet derivation, penalty behavior, and aggregation remain unsupported. Isolated manual Enmity remains separate.",
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
        "BUILD-003 has no combat model. Flame Link output is Added Fire Damage granted, never DPS.",
        ("AUD-004-C12", "AUD-005-C07"),
    ),
)


def mechanics_availability() -> list[dict[str, Any]]:
    return [
        {
            "id": identifier,
            "label": label,
            "status": "unavailable-pending-evidence",
            "value": None,
            "explanation": explanation,
            "claimReferences": list(claims),
        }
        for identifier, label, explanation, claims in _UNAVAILABLE
    ]
