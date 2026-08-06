"""Narrow manual Golden Glory Calculator domain seam.

Translates simple GUI fields into the existing Flame Link evaluator input and
the shared Enmity overcap helper. The GUI never sees provenance, recognition,
or build-state records.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_DOWN, Decimal
from typing import Any

from golden_glory_lab.domain.decimal_input import DecimalInputError, parse_decimal_text
from golden_glory_lab.domain.enmity import enmity_overcap_contribution
from golden_glory_lab.domain.flame_link import (
    FlameLinkLevelTable,
    evaluate_flame_link,
    load_flame_link_level_table,
)

MINIMUM_FLAME_LINK_LEVEL = 1
MAXIMUM_FLAME_LINK_LEVEL = 40
BOND_VALUE_PCT = "20"
EMPOWERED_BOND_LEVELS = 2

FIXED_LIGHT_RADIUS_SLOTS: tuple[str, ...] = (
    "Helmet",
    "Body Armour",
    "Boots",
    "Main Hand",
    "Off Hand",
    "Amulet",
    "Ring 1",
    "Ring 2",
    "Belt",
    "Passive Tree / Ascendancy",
    "Other / Misc",
)
INITIAL_JEWEL_COUNT = 3


@dataclass(frozen=True, slots=True)
class ManualCalculatorInput:
    maximum_life: str
    increased_light_radius_pct: str
    other_link_skill_buff_effect_pct: str
    flame_link_level: str
    golden_glory_allocated: bool
    powerful_bond_active: bool
    inspiring_bond_active: bool
    total_fire_resistance_on_gear: str
    luminary_aura_fire_resistance: str
    enmity_reduced_fire_resistance: str
    maximum_fire_resistance: str
    enmity_equipped: bool


@dataclass(frozen=True, slots=True)
class ManualCalculatorResult:
    net_link_skill_buff_effect_pct: str | None
    link_effect_multiplier: str | None
    flame_link_min: int | None
    flame_link_max: int | None
    pre_enmity_fire_resistance: str | None
    final_uncapped_fire_resistance: str | None
    overcapped_fire_resistance: str | None
    enmity_penetration: int | None
    flame_link_error: str | None
    enmity_error: str | None

    @property
    def flame_link_available(self) -> bool:
        return (
            self.flame_link_min is not None
            and self.flame_link_max is not None
            and self.flame_link_error is None
        )

    @property
    def enmity_available(self) -> bool:
        return self.enmity_penetration is not None and self.enmity_error is None


@dataclass
class LightRadiusBreakdown:
    """Optional Light Radius slot/jewel totals for the second calculator page."""

    slots: dict[str, Decimal] = field(default_factory=dict)
    jewels: list[Decimal] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.slots:
            self.slots = {name: Decimal(0) for name in FIXED_LIGHT_RADIUS_SLOTS}
        if not self.jewels:
            self.jewels = [Decimal(0) for _ in range(INITIAL_JEWEL_COUNT)]

    def total(self) -> Decimal:
        return sum(self.slots.values(), Decimal(0)) + sum(self.jewels, Decimal(0))

    def add_jewel(self) -> None:
        self.jewels.append(Decimal(0))

    def can_remove_jewel(self, index: int) -> bool:
        return index >= INITIAL_JEWEL_COUNT and 0 <= index < len(self.jewels)

    def remove_jewel(self, index: int) -> None:
        if not self.can_remove_jewel(index):
            raise ValueError("Only dynamically added jewel rows can be removed")
        del self.jewels[index]

    def reset(self) -> None:
        for name in FIXED_LIGHT_RADIUS_SLOTS:
            self.slots[name] = Decimal(0)
        self.jewels = [Decimal(0) for _ in range(INITIAL_JEWEL_COUNT)]


def _blank(text: str) -> bool:
    return not text.strip()


def _parse_optional_decimal(text: str) -> tuple[Decimal | None, str | None]:
    if _blank(text):
        return None, None
    try:
        return parse_decimal_text(text.strip()).value, None
    except DecimalInputError:
        return None, "Enter a valid number"


def _format_net_pct(lexeme: str | None) -> str | None:
    if lexeme is None:
        return None
    value = Decimal(lexeme)
    if value == value.to_integral_value():
        return str(int(value))
    return format(value.normalize(), "f")


def _format_multiplier(lexeme: str | None) -> str | None:
    if lexeme is None:
        return None
    value = Decimal(lexeme)
    quantized = value.quantize(Decimal("0.01"))
    return format(quantized, "f")


def _player_chain_from_manual(
    *,
    maximum_life: Decimal,
    light_radius_pct: Decimal,
    other_link_pct: Decimal,
    flame_link_level: int,
    golden_glory_allocated: bool,
    powerful_bond_active: bool,
    inspiring_bond_active: bool,
) -> dict[str, Any]:
    recognition = {"kind": "none", "digest": None}
    life_lexeme = parse_decimal_text(format(maximum_life, "f")).lexeme
    light_lexeme = parse_decimal_text(format(light_radius_pct, "f")).lexeme
    other_lexeme = parse_decimal_text(format(other_link_pct, "f")).lexeme
    return {
        "goldenGlory": {
            "allocatedState": (
                "allocated" if golden_glory_allocated else "not-allocated"
            ),
            "mercenaryTargetState": "yes",
            "reviewedLightRadiusPct": light_lexeme,
            "provenanceKind": "manual-reviewed",
            "reviewState": "reviewed",
            "rawSourceText": "",
            "recognitionSource": recognition,
        },
        "directLinkBuffEffect": {
            "reviewedDirectPct": other_lexeme,
            "provenanceKind": "manual-reviewed",
            "reviewState": "reviewed",
            "rawSourceText": "",
            "recognitionSource": recognition,
        },
        "conditionalContributions": [
            {
                "contributionId": "powerful-bond",
                "label": "Powerful Bond",
                "valuePct": BOND_VALUE_PCT,
                "conditionState": (
                    "active" if powerful_bond_active else "inactive"
                ),
                "kind": "powerful-bond",
                "provenanceKind": "catalog-default",
                "rawSourceText": "",
                "recognitionSource": recognition,
            },
            {
                "contributionId": "inspiring-bond",
                "label": "Inspiring Bond",
                "valuePct": BOND_VALUE_PCT,
                "conditionState": (
                    "active" if inspiring_bond_active else "inactive"
                ),
                "kind": "inspiring-bond",
                "provenanceKind": "catalog-default",
                "rawSourceText": "",
                "recognitionSource": recognition,
            },
        ],
        "flameLinkLevel": {
            "baseLevel": flame_link_level,
            "baseLevelProvenance": "manual-reviewed",
            "additionalLinkGemLevels": [
                {
                    "contributionId": "empowered-bond",
                    "label": "Empowered Bond",
                    "levels": EMPOWERED_BOND_LEVELS,
                    "activeState": "inactive",
                    "provenanceKind": "catalog-default",
                    "rawSourceText": "",
                    "recognitionSource": recognition,
                }
            ],
        },
        "luminaryMaximumLife": {
            "reviewedLife": life_lexeme,
            "provenanceKind": "manual-reviewed",
            "reviewState": "reviewed",
            "rawSourceText": "",
            "recognitionSource": recognition,
        },
        "roundingPolicyId": "modelled-nearest-integer-half-up-v1",
        "formulaVersionId": "flame-link-player-chain-v1",
    }


def _evaluate_flame_link_section(
    fields: ManualCalculatorInput,
    level_table: FlameLinkLevelTable,
) -> tuple[str | None, str | None, int | None, int | None, str | None]:
    if _blank(fields.maximum_life):
        return None, None, None, None, "Enter Maximum Life"
    life, life_error = _parse_optional_decimal(fields.maximum_life)
    if life_error is not None:
        return None, None, None, None, life_error
    assert life is not None
    if life < 0:
        return None, None, None, None, "Maximum Life must be nonnegative"

    if _blank(fields.increased_light_radius_pct):
        return None, None, None, None, "Enter Increased Light Radius Modifier"
    light, light_error = _parse_optional_decimal(fields.increased_light_radius_pct)
    if light_error is not None:
        return None, None, None, None, light_error
    assert light is not None

    if _blank(fields.other_link_skill_buff_effect_pct):
        return None, None, None, None, "Enter Other Link Skill Buff Effect"
    other, other_error = _parse_optional_decimal(
        fields.other_link_skill_buff_effect_pct
    )
    if other_error is not None:
        return None, None, None, None, other_error
    assert other is not None

    if _blank(fields.flame_link_level):
        return None, None, None, None, "Enter a Flame Link level from 1 to 40"
    level_parsed, level_error = _parse_optional_decimal(fields.flame_link_level)
    if level_error is not None:
        return None, None, None, None, level_error
    assert level_parsed is not None
    if level_parsed != level_parsed.to_integral_value():
        return None, None, None, None, "Enter a Flame Link level from 1 to 40"
    level = int(level_parsed)
    if level < MINIMUM_FLAME_LINK_LEVEL or level > MAXIMUM_FLAME_LINK_LEVEL:
        return None, None, None, None, "Enter a Flame Link level from 1 to 40"

    chain = _player_chain_from_manual(
        maximum_life=life,
        light_radius_pct=light,
        other_link_pct=other,
        flame_link_level=level,
        golden_glory_allocated=fields.golden_glory_allocated,
        powerful_bond_active=fields.powerful_bond_active,
        inspiring_bond_active=fields.inspiring_bond_active,
    )
    result = evaluate_flame_link(chain, level_table)
    if result.state == "unsupported-effect-multiplier":
        return (
            _format_net_pct(result.netLinkSkillBuffEffectPct),
            _format_multiplier(result.linkEffectMultiplier),
            None,
            None,
            "Link Effect Multiplier below zero is unsupported",
        )
    if not result.available:
        message = "Unable to calculate Flame Link result"
        if result.reasons:
            message = str(result.reasons[0].get("message", message))
        return None, None, None, None, message
    return (
        _format_net_pct(result.netLinkSkillBuffEffectPct),
        _format_multiplier(result.linkEffectMultiplier),
        result.modelledIntegerMin,
        result.modelledIntegerMax,
        None,
    )


def _format_resistance_pct(value: Decimal) -> str:
    if value == value.to_integral_value():
        return str(int(value))
    return format(value.normalize(), "f")


def _truncate_toward_zero(value: Decimal) -> Decimal:
    """Truncate a fractional resistance total the way current PoB does."""

    return value.to_integral_value(rounding=ROUND_DOWN)


def _evaluate_enmity_section(
    fields: ManualCalculatorInput,
) -> tuple[str | None, str | None, str | None, int | None, str | None]:
    """Return pre-Enmity, final uncapped, overcap, penetration, and error."""

    gear_blank = _blank(fields.total_fire_resistance_on_gear)
    if gear_blank:
        if fields.enmity_equipped:
            return None, None, None, None, "Enter Total Fire Resistance on Gear"
        return None, None, None, None, None

    gear, gear_error = _parse_optional_decimal(fields.total_fire_resistance_on_gear)
    if gear_error is not None:
        return None, None, None, None, gear_error
    assert gear is not None

    if _blank(fields.luminary_aura_fire_resistance):
        aura = Decimal(0)
    else:
        aura, aura_error = _parse_optional_decimal(
            fields.luminary_aura_fire_resistance
        )
        if aura_error is not None:
            return None, None, None, None, aura_error
        assert aura is not None

    pre_enmity = gear + aura
    pre_text = _format_resistance_pct(pre_enmity)

    if not fields.enmity_equipped:
        return pre_text, pre_text, None, None, None

    if _blank(fields.enmity_reduced_fire_resistance):
        return pre_text, None, None, None, "Enter Enmity Reduced Fire Resistance"
    reduction, reduction_error = _parse_optional_decimal(
        fields.enmity_reduced_fire_resistance
    )
    if reduction_error is not None:
        return pre_text, None, None, None, reduction_error
    assert reduction is not None

    if _blank(fields.maximum_fire_resistance):
        return pre_text, None, None, None, "Enter Maximum Fire Resistance"
    maximum, maximum_error = _parse_optional_decimal(fields.maximum_fire_resistance)
    if maximum_error is not None:
        return pre_text, None, None, None, maximum_error
    assert maximum is not None

    raw_final_uncapped = pre_enmity * (Decimal(1) - reduction / Decimal(100))
    final_uncapped = _truncate_toward_zero(raw_final_uncapped)
    overcap, penetration = enmity_overcap_contribution(
        int(final_uncapped), int(_truncate_toward_zero(maximum))
    )
    return (
        pre_text,
        _format_resistance_pct(final_uncapped),
        _format_resistance_pct(Decimal(overcap)),
        penetration,
        None,
    )


def evaluate_manual_calculator(
    fields: ManualCalculatorInput,
    level_table: FlameLinkLevelTable | None = None,
) -> ManualCalculatorResult:
    table = level_table if level_table is not None else load_flame_link_level_table()
    net, multiplier, flame_min, flame_max, flame_error = _evaluate_flame_link_section(
        fields, table
    )
    (
        pre_enmity,
        final_uncapped,
        overcap,
        enmity_value,
        enmity_error,
    ) = _evaluate_enmity_section(fields)
    return ManualCalculatorResult(
        net_link_skill_buff_effect_pct=net,
        link_effect_multiplier=multiplier,
        flame_link_min=flame_min,
        flame_link_max=flame_max,
        pre_enmity_fire_resistance=pre_enmity,
        final_uncapped_fire_resistance=final_uncapped,
        overcapped_fire_resistance=overcap,
        enmity_penetration=enmity_value,
        flame_link_error=flame_error,
        enmity_error=enmity_error,
    )


def default_manual_calculator_input() -> ManualCalculatorInput:
    return ManualCalculatorInput(
        maximum_life="",
        increased_light_radius_pct="",
        other_link_skill_buff_effect_pct="",
        flame_link_level="",
        golden_glory_allocated=False,
        powerful_bond_active=False,
        inspiring_bond_active=False,
        total_fire_resistance_on_gear="",
        luminary_aura_fire_resistance="",
        enmity_reduced_fire_resistance="",
        maximum_fire_resistance="",
        enmity_equipped=False,
    )
