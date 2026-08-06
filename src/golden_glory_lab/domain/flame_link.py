"""Canonical manual-first Flame Link player-chain calculation (BUILD-003)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, localcontext
from importlib import resources
from typing import Any, Mapping

from .decimal_input import ParsedDecimal, numeric_context_for, parse_decimal_text

OUTPUT_ID = "flame-link-added-fire-damage-granted-v1"
OUTPUT_LABEL = "Added Fire Damage granted to linked Mercenary"
FORMULA_VERSION_ID = "flame-link-player-chain-v1"
ROUNDING_POLICY_ID = "modelled-nearest-integer-half-up-v1"
ROUNDING_POLICY_LABEL = "Modelled nearest-integer result"
TARGET_GAME_VERSION = "Path of Exile 1 3.29.1"
SOURCE_DATA_VERSION = "Path of Exile 1 3.29.0"
ARTIFACT_ID = "flame-link-level-table-v1"
LIFE_COMPONENT_FRACTION = Decimal("0.05")
LEVEL_TABLE_RESOURCE = "flame-link-level-table-v1.json"
_RESOURCE_PACKAGE = "golden_glory_lab.runtime_data"
MINIMUM_EFFECTIVE_LEVEL = 1
MAXIMUM_EFFECTIVE_LEVEL = 40
EXPECTED_TABLE_ROW_COUNT = 40
EXPECTED_ARTIFACT_ID = ARTIFACT_ID
EXPECTED_FORMULA_VERSION_ID = FORMULA_VERSION_ID
EXPECTED_ROUNDING_POLICY_ID = ROUNDING_POLICY_ID
EXPECTED_TARGET_GAME_VERSION = TARGET_GAME_VERSION
EXPECTED_SOURCE_DATA_VERSION = SOURCE_DATA_VERSION

_TABLE_ROOT_KEYS = frozenset(
    {
        "schemaVersion",
        "artifactId",
        "artifactType",
        "formulaVersionId",
        "roundingPolicyId",
        "targetGameVersion",
        "sourceDataVersion",
        "versionState",
        "verificationStatus",
        "sourceIds",
        "provenance",
        "tableBounds",
        "compactAnchors",
        "rows",
    }
)
_TABLE_BOUNDS_KEYS = frozenset({"minimumLevel", "maximumLevel", "rowCount"})
_TABLE_ROW_KEYS = frozenset({"level", "requirementLevel", "flatMin", "flatMax"})
_TABLE_PROVENANCE_KEYS = frozenset(
    {
        "derivation",
        "sourceCommitSha",
        "sourceCommitUrl",
        "recordLocations",
        "lifeComponentPercent",
        "lifeComponentBasis",
        "qualityAffectsGrantedDamage",
        "notAuthorityForLiveRounding",
        "retainedMaterial",
    }
)
_TABLE_RECORD_LOCATION_KEYS = frozenset({"skill", "interpolation", "constants"})


class FlameLinkTableError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True, slots=True)
class FlameLinkLevelRow:
    level: int
    requirementLevel: int
    flatMin: Decimal
    flatMax: Decimal


@dataclass(frozen=True, slots=True)
class FlameLinkLevelTable:
    artifactId: str
    formulaVersionId: str
    roundingPolicyId: str
    targetGameVersion: str
    minimumLevel: int
    maximumLevel: int
    rows: dict[int, FlameLinkLevelRow]

    def row_for(self, level: int) -> FlameLinkLevelRow | None:
        return self.rows.get(level)


@dataclass(frozen=True, slots=True)
class FlameLinkResult:
    outputId: str
    label: str
    targetGameVersion: str
    formulaVersionId: str
    roundingPolicyId: str
    roundingPolicyLabel: str
    state: str
    available: bool
    goldenGloryContributionPct: str | None
    directLinkContributionPct: str | None
    conditionalContributionPct: str | None
    netLinkSkillBuffEffectPct: str | None
    linkEffectMultiplier: str | None
    baseFlameLinkLevel: int | None
    additionalLinkGemLevels: int | None
    effectiveFlameLinkLevel: int | None
    luminaryMaximumLife: str | None
    lifeComponent: str | None
    levelFlatMin: str | None
    levelFlatMax: str | None
    unscaledMin: str | None
    unscaledMax: str | None
    exactPreRoundMin: str | None
    exactPreRoundMax: str | None
    modelledIntegerMin: int | None
    modelledIntegerMax: int | None
    contributionBreakdown: dict[str, Any]
    levelBreakdown: dict[str, Any]
    reasons: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "outputId": self.outputId,
            "label": self.label,
            "targetGameVersion": self.targetGameVersion,
            "formulaVersionId": self.formulaVersionId,
            "roundingPolicyId": self.roundingPolicyId,
            "roundingPolicyLabel": self.roundingPolicyLabel,
            "state": self.state,
            "available": self.available,
            "goldenGloryContributionPct": self.goldenGloryContributionPct,
            "directLinkContributionPct": self.directLinkContributionPct,
            "conditionalContributionPct": self.conditionalContributionPct,
            "netLinkSkillBuffEffectPct": self.netLinkSkillBuffEffectPct,
            "linkEffectMultiplier": self.linkEffectMultiplier,
            "baseFlameLinkLevel": self.baseFlameLinkLevel,
            "additionalLinkGemLevels": self.additionalLinkGemLevels,
            "effectiveFlameLinkLevel": self.effectiveFlameLinkLevel,
            "luminaryMaximumLife": self.luminaryMaximumLife,
            "lifeComponent": self.lifeComponent,
            "levelFlatMin": self.levelFlatMin,
            "levelFlatMax": self.levelFlatMax,
            "unscaledMin": self.unscaledMin,
            "unscaledMax": self.unscaledMax,
            "exactPreRoundMin": self.exactPreRoundMin,
            "exactPreRoundMax": self.exactPreRoundMax,
            "modelledIntegerMin": self.modelledIntegerMin,
            "modelledIntegerMax": self.modelledIntegerMax,
            "contributionBreakdown": dict(self.contributionBreakdown),
            "levelBreakdown": dict(self.levelBreakdown),
            "reasons": [dict(reason) for reason in self.reasons],
        }


def round_half_up(value: Decimal) -> int:
    """Nearest-integer rounding with .5 ties rounding away from zero (up for >= 0)."""

    if value < 0:
        raise ValueError("round_half_up supports nonnegative modelled outputs only")
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def table_sha256(data: bytes) -> str:
    """Return the lowercase hex SHA-256 digest of packaged table bytes."""

    return hashlib.sha256(data).hexdigest()


def _reason(code: str, message: str, **values: Any) -> dict[str, Any]:
    return {"code": code, "message": message, **values}


def _lexeme(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text if text else "0"


def _parsed_optional(value: Any) -> ParsedDecimal | None:
    return None if value is None else parse_decimal_text(value)


def _require_exact_string(root: Mapping[str, Any], key: str, expected: str) -> str:
    if key not in root:
        raise FlameLinkTableError(
            "FLAME_LINK_TABLE_METADATA",
            f"Flame Link level table is missing required metadata field {key}",
        )
    value = root[key]
    if not isinstance(value, str) or value != expected:
        raise FlameLinkTableError(
            "FLAME_LINK_TABLE_METADATA",
            f"Flame Link level table {key} must be exactly {expected!r}",
        )
    return value


def _require_strict_int(value: Any, context: str, *, positive: bool = False) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise FlameLinkTableError(
            "FLAME_LINK_TABLE_INVALID",
            f"{context} must be a strict JSON integer",
        )
    if positive and value <= 0:
        raise FlameLinkTableError(
            "FLAME_LINK_TABLE_INVALID",
            f"{context} must be a positive integer",
        )
    return value


def _require_nonnegative_int(value: Any, context: str) -> int:
    number = _require_strict_int(value, context)
    if number < 0:
        raise FlameLinkTableError(
            "FLAME_LINK_TABLE_INVALID",
            f"{context} must be a nonnegative integer",
        )
    return number


def _reject_unknown_keys(
    mapping: Mapping[str, Any],
    allowed: frozenset[str],
    context: str,
) -> None:
    unknown = sorted(set(mapping) - allowed)
    if unknown:
        raise FlameLinkTableError(
            "FLAME_LINK_TABLE_UNKNOWN_FIELD",
            f"{context} contains unknown field(s): {', '.join(unknown)}",
        )


def load_flame_link_level_table(
    package: str = _RESOURCE_PACKAGE,
    resource_name: str = LEVEL_TABLE_RESOURCE,
) -> FlameLinkLevelTable:
    try:
        data = resources.files(package).joinpath(resource_name).read_bytes()
    except (FileNotFoundError, ModuleNotFoundError, OSError, TypeError) as error:
        raise FlameLinkTableError(
            "FLAME_LINK_TABLE_MISSING",
            f"Packaged Flame Link level table is unavailable: {error}",
        ) from error
    return parse_flame_link_level_table_bytes(data)


def parse_flame_link_level_table_bytes(data: bytes) -> FlameLinkLevelTable:
    try:
        root = json.loads(data.decode("utf-8"), parse_constant=_reject_json_constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise FlameLinkTableError(
            "FLAME_LINK_TABLE_INVALID",
            f"Flame Link level table is not valid JSON: {error}",
        ) from error
    except FlameLinkTableError:
        raise
    except ValueError as error:
        raise FlameLinkTableError(
            "FLAME_LINK_TABLE_NONFINITE",
            f"Flame Link level table contains a non-finite JSON constant: {error}",
        ) from error
    if not isinstance(root, dict):
        raise FlameLinkTableError(
            "FLAME_LINK_TABLE_INVALID",
            "Flame Link level table root must be an object",
        )
    _reject_unknown_keys(root, _TABLE_ROOT_KEYS, "Flame Link level table root")
    artifact_id = _require_exact_string(root, "artifactId", EXPECTED_ARTIFACT_ID)
    formula_version = _require_exact_string(
        root, "formulaVersionId", EXPECTED_FORMULA_VERSION_ID
    )
    rounding_policy = _require_exact_string(
        root, "roundingPolicyId", EXPECTED_ROUNDING_POLICY_ID
    )
    target_version = _require_exact_string(
        root, "targetGameVersion", EXPECTED_TARGET_GAME_VERSION
    )
    _require_exact_string(root, "sourceDataVersion", EXPECTED_SOURCE_DATA_VERSION)

    provenance = root.get("provenance")
    if not isinstance(provenance, dict):
        raise FlameLinkTableError(
            "FLAME_LINK_TABLE_INVALID",
            "Flame Link level table provenance must be an object",
        )
    _reject_unknown_keys(provenance, _TABLE_PROVENANCE_KEYS, "provenance")
    record_locations = provenance.get("recordLocations")
    if not isinstance(record_locations, dict):
        raise FlameLinkTableError(
            "FLAME_LINK_TABLE_INVALID",
            "provenance.recordLocations must be an object",
        )
    _reject_unknown_keys(
        record_locations, _TABLE_RECORD_LOCATION_KEYS, "provenance.recordLocations"
    )

    bounds = root.get("tableBounds")
    rows_value = root.get("rows")
    if not isinstance(bounds, dict) or not isinstance(rows_value, list):
        raise FlameLinkTableError(
            "FLAME_LINK_TABLE_INVALID",
            "Flame Link level table is missing bounds or rows",
        )
    _reject_unknown_keys(bounds, _TABLE_BOUNDS_KEYS, "tableBounds")
    minimum = _require_strict_int(bounds.get("minimumLevel"), "tableBounds.minimumLevel")
    maximum = _require_strict_int(bounds.get("maximumLevel"), "tableBounds.maximumLevel")
    row_count = _require_strict_int(bounds.get("rowCount"), "tableBounds.rowCount")
    if (
        minimum != MINIMUM_EFFECTIVE_LEVEL
        or maximum != MAXIMUM_EFFECTIVE_LEVEL
        or row_count != EXPECTED_TABLE_ROW_COUNT
    ):
        raise FlameLinkTableError(
            "FLAME_LINK_TABLE_BOUNDS",
            "Flame Link level table bounds must be min=1 max=40 rowCount=40",
        )
    if len(rows_value) != EXPECTED_TABLE_ROW_COUNT:
        raise FlameLinkTableError(
            "FLAME_LINK_TABLE_BOUNDS",
            "Flame Link level table rowCount must match the rows array length",
        )

    rows: dict[int, FlameLinkLevelRow] = {}
    for index, raw in enumerate(rows_value):
        if not isinstance(raw, dict):
            raise FlameLinkTableError(
                "FLAME_LINK_TABLE_INVALID",
                f"Flame Link level row {index} must be an object",
            )
        _reject_unknown_keys(raw, _TABLE_ROW_KEYS, f"rows[{index}]")
        try:
            level = _require_strict_int(raw["level"], f"rows[{index}].level")
            requirement = _require_strict_int(
                raw["requirementLevel"],
                f"rows[{index}].requirementLevel",
                positive=True,
            )
            flat_min = _require_nonnegative_int(raw["flatMin"], f"rows[{index}].flatMin")
            flat_max = _require_nonnegative_int(raw["flatMax"], f"rows[{index}].flatMax")
        except KeyError as error:
            raise FlameLinkTableError(
                "FLAME_LINK_TABLE_INVALID",
                f"Flame Link level row {index} is missing field {error}",
            ) from error
        if flat_min > flat_max:
            raise FlameLinkTableError(
                "FLAME_LINK_TABLE_INVALID",
                f"Flame Link level row {index} flatMin must be <= flatMax",
            )
        if level in rows:
            raise FlameLinkTableError(
                "FLAME_LINK_TABLE_DUPLICATE_LEVEL",
                f"Duplicate Flame Link level {level}",
            )
        rows[level] = FlameLinkLevelRow(
            level,
            requirement,
            Decimal(flat_min),
            Decimal(flat_max),
        )
    expected = set(range(MINIMUM_EFFECTIVE_LEVEL, MAXIMUM_EFFECTIVE_LEVEL + 1))
    if set(rows) != expected:
        raise FlameLinkTableError(
            "FLAME_LINK_TABLE_INCOMPLETE",
            "Flame Link level table must contain exactly levels 1-40 once each",
        )

    anchors = root.get("compactAnchors")
    if not isinstance(anchors, list):
        raise FlameLinkTableError(
            "FLAME_LINK_TABLE_ANCHORS",
            "Flame Link level table compactAnchors must be an array",
        )
    for anchor_index, anchor in enumerate(anchors):
        if not isinstance(anchor, dict):
            raise FlameLinkTableError(
                "FLAME_LINK_TABLE_ANCHORS",
                "Flame Link compact anchor must be an object",
            )
        _reject_unknown_keys(anchor, _TABLE_ROW_KEYS, f"compactAnchors[{anchor_index}]")
        level = _require_strict_int(anchor.get("level"), "compactAnchors.level")
        row = rows.get(level)
        if row is None:
            raise FlameLinkTableError(
                "FLAME_LINK_TABLE_ANCHORS",
                f"compactAnchors level {level} is missing from rows",
            )
        requirement = _require_strict_int(
            anchor.get("requirementLevel"),
            "compactAnchors.requirementLevel",
            positive=True,
        )
        flat_min = _require_nonnegative_int(anchor.get("flatMin"), "compactAnchors.flatMin")
        flat_max = _require_nonnegative_int(anchor.get("flatMax"), "compactAnchors.flatMax")
        if (
            requirement != row.requirementLevel
            or Decimal(flat_min) != row.flatMin
            or Decimal(flat_max) != row.flatMax
        ):
            raise FlameLinkTableError(
                "FLAME_LINK_TABLE_ANCHORS",
                f"compactAnchors for level {level} do not match rows",
            )
    for required_level in (1, 20):
        if not any(
            isinstance(anchor, dict) and anchor.get("level") == required_level
            for anchor in anchors
        ):
            raise FlameLinkTableError(
                "FLAME_LINK_TABLE_ANCHORS",
                f"compactAnchors must include level {required_level}",
            )

    return FlameLinkLevelTable(
        artifactId=artifact_id,
        formulaVersionId=formula_version,
        roundingPolicyId=rounding_policy,
        targetGameVersion=target_version,
        minimumLevel=MINIMUM_EFFECTIVE_LEVEL,
        maximumLevel=MAXIMUM_EFFECTIVE_LEVEL,
        rows=rows,
    )


def _reject_json_constant(value: str) -> None:
    raise FlameLinkTableError(
        "FLAME_LINK_TABLE_NONFINITE",
        f"Flame Link level table rejects JSON constant {value}",
    )


def _unavailable(
    *,
    state: str,
    reasons: tuple[dict[str, Any], ...],
    contribution_breakdown: dict[str, Any] | None = None,
    level_breakdown: dict[str, Any] | None = None,
    base_level: int | None = None,
    additional_levels: int | None = None,
    effective_level: int | None = None,
    life_lexeme: str | None = None,
) -> FlameLinkResult:
    return FlameLinkResult(
        outputId=OUTPUT_ID,
        label=OUTPUT_LABEL,
        targetGameVersion=TARGET_GAME_VERSION,
        formulaVersionId=FORMULA_VERSION_ID,
        roundingPolicyId=ROUNDING_POLICY_ID,
        roundingPolicyLabel=ROUNDING_POLICY_LABEL,
        state=state,
        available=False,
        goldenGloryContributionPct=None,
        directLinkContributionPct=None,
        conditionalContributionPct=None,
        netLinkSkillBuffEffectPct=None,
        linkEffectMultiplier=None,
        baseFlameLinkLevel=base_level,
        additionalLinkGemLevels=additional_levels,
        effectiveFlameLinkLevel=effective_level,
        luminaryMaximumLife=life_lexeme,
        lifeComponent=None,
        levelFlatMin=None,
        levelFlatMax=None,
        unscaledMin=None,
        unscaledMax=None,
        exactPreRoundMin=None,
        exactPreRoundMax=None,
        modelledIntegerMin=None,
        modelledIntegerMax=None,
        contributionBreakdown=contribution_breakdown or {},
        levelBreakdown=level_breakdown or {},
        reasons=reasons,
    )


def _resolve_golden_glory(
    golden: Mapping[str, Any],
) -> tuple[Decimal | None, str | None, dict[str, Any], list[dict[str, Any]]]:
    allocated = golden.get("allocatedState")
    target = golden.get("mercenaryTargetState")
    review_state = golden.get("reviewState")
    parsed = _parsed_optional(golden.get("reviewedLightRadiusPct"))
    detail = {
        "allocatedState": allocated,
        "mercenaryTargetState": target,
        "reviewState": review_state,
        "reviewedLightRadiusPct": None if parsed is None else parsed.lexeme,
        "provenanceKind": golden.get("provenanceKind"),
        "rawSourceText": golden.get("rawSourceText", ""),
        "contributionPct": None,
        "counted": False,
    }
    reasons: list[dict[str, Any]] = []
    if allocated == "not-allocated":
        detail["contributionPct"] = "0"
        detail["counted"] = True
        return Decimal(0), "0", detail, reasons
    if allocated == "unknown" or target == "unknown":
        reasons.append(
            _reason(
                "GOLDEN_GLORY_ELIGIBILITY_UNKNOWN",
                "Golden Glory allocation and Mercenary target must be explicit before Light Radius contributes",
            )
        )
        return None, None, detail, reasons
    if allocated != "allocated":
        reasons.append(
            _reason(
                "GOLDEN_GLORY_ALLOCATED_STATE_INVALID",
                "Golden Glory allocated state is not recognized",
            )
        )
        return None, None, detail, reasons
    if target == "no":
        detail["contributionPct"] = "0"
        detail["counted"] = True
        return Decimal(0), "0", detail, reasons
    if target != "yes":
        reasons.append(
            _reason(
                "GOLDEN_GLORY_TARGET_STATE_INVALID",
                "Golden Glory Mercenary target state is not recognized",
            )
        )
        return None, None, detail, reasons
    if review_state != "reviewed" or parsed is None:
        reasons.append(
            _reason(
                "GOLDEN_GLORY_LIGHT_RADIUS_UNREVIEWED",
                "Reviewed Light Radius percent is required when Golden Glory is allocated to an active permanent Mercenary",
            )
        )
        return None, None, detail, reasons
    detail["contributionPct"] = parsed.lexeme
    detail["counted"] = True
    return parsed.value, parsed.lexeme, detail, reasons


def _resolve_direct(
    direct: Mapping[str, Any],
) -> tuple[Decimal | None, str | None, dict[str, Any], list[dict[str, Any]]]:
    review_state = direct.get("reviewState")
    parsed = _parsed_optional(direct.get("reviewedDirectPct"))
    detail = {
        "reviewState": review_state,
        "reviewedDirectPct": None if parsed is None else parsed.lexeme,
        "provenanceKind": direct.get("provenanceKind"),
        "rawSourceText": direct.get("rawSourceText", ""),
        "contributionPct": None,
        "counted": False,
    }
    reasons: list[dict[str, Any]] = []
    if review_state != "reviewed" or parsed is None:
        reasons.append(
            _reason(
                "DIRECT_LINK_BUFF_EFFECT_UNREVIEWED",
                "Reviewed direct Link Skill Buff Effect percent is required",
            )
        )
        return None, None, detail, reasons
    detail["contributionPct"] = parsed.lexeme
    detail["counted"] = True
    return parsed.value, parsed.lexeme, detail, reasons


def _resolve_conditionals(
    contributions: Any,
) -> tuple[list[Decimal] | None, list[dict[str, Any]], list[dict[str, Any]]]:
    """Collect active conditional Decimals without summing under ambient context."""

    if not isinstance(contributions, list):
        return (
            None,
            [],
            [
                _reason(
                    "CONDITIONAL_CONTRIBUTIONS_SHAPE",
                    "Conditional Link Buff Effect contributions must be an array",
                )
            ],
        )
    active_values: list[Decimal] = []
    details: list[dict[str, Any]] = []
    reasons: list[dict[str, Any]] = []
    for index, raw in enumerate(contributions):
        if not isinstance(raw, Mapping):
            reasons.append(
                _reason(
                    "CONDITIONAL_CONTRIBUTION_SHAPE",
                    f"Conditional contribution {index} must be an object",
                )
            )
            continue
        state = raw.get("conditionState")
        parsed = _parsed_optional(raw.get("valuePct"))
        detail = {
            "contributionId": raw.get("contributionId"),
            "label": raw.get("label"),
            "kind": raw.get("kind"),
            "conditionState": state,
            "valuePct": None if parsed is None else parsed.lexeme,
            "provenanceKind": raw.get("provenanceKind"),
            "rawSourceText": raw.get("rawSourceText", ""),
            "contributionPct": None,
            "counted": False,
        }
        if state == "inactive":
            details.append(detail)
            continue
        if state == "unknown":
            reasons.append(
                _reason(
                    "CONDITIONAL_CONTRIBUTION_UNKNOWN",
                    "An unknown conditional Link Buff Effect source blocks final resolution",
                    contributionId=raw.get("contributionId"),
                    label=raw.get("label"),
                )
            )
            details.append(detail)
            continue
        if state != "active":
            reasons.append(
                _reason(
                    "CONDITIONAL_CONTRIBUTION_STATE_INVALID",
                    "Conditional contribution state is not recognized",
                    contributionId=raw.get("contributionId"),
                )
            )
            details.append(detail)
            continue
        if parsed is None:
            reasons.append(
                _reason(
                    "CONDITIONAL_CONTRIBUTION_VALUE_MISSING",
                    "An active conditional contribution requires a reviewed valuePct",
                    contributionId=raw.get("contributionId"),
                )
            )
            details.append(detail)
            continue
        detail["contributionPct"] = parsed.lexeme
        detail["counted"] = True
        details.append(detail)
        active_values.append(parsed.value)
    if reasons:
        return None, details, reasons
    return active_values, details, reasons


def _resolve_levels(
    level_block: Mapping[str, Any],
) -> tuple[int | None, int | None, int | None, dict[str, Any], list[dict[str, Any]]]:
    reasons: list[dict[str, Any]] = []
    try:
        base_level = int(level_block["baseLevel"])
    except (KeyError, TypeError, ValueError):
        return (
            None,
            None,
            None,
            {},
            [
                _reason(
                    "FLAME_LINK_BASE_LEVEL_INVALID",
                    "Base Flame Link level must be an integer",
                )
            ],
        )
    additions = level_block.get("additionalLinkGemLevels", [])
    if not isinstance(additions, list):
        return (
            None,
            None,
            None,
            {},
            [
                _reason(
                    "ADDITIONAL_LINK_LEVELS_SHAPE",
                    "Additional Link gem levels must be an array",
                )
            ],
        )
    additional_total = 0
    addition_details: list[dict[str, Any]] = []
    for index, raw in enumerate(additions):
        if not isinstance(raw, Mapping):
            reasons.append(
                _reason(
                    "ADDITIONAL_LINK_LEVEL_SHAPE",
                    f"Additional Link level contribution {index} must be an object",
                )
            )
            continue
        active_state = raw.get("activeState")
        provenance = raw.get("provenanceKind")
        contribution_id = raw.get("contributionId")
        try:
            levels = int(raw["levels"])
        except (KeyError, TypeError, ValueError):
            reasons.append(
                _reason(
                    "ADDITIONAL_LINK_LEVEL_VALUE_INVALID",
                    "Additional Link gem level contribution must provide integer levels",
                    contributionId=contribution_id,
                )
            )
            addition_details.append(
                {
                    "contributionId": contribution_id,
                    "label": raw.get("label"),
                    "levels": raw.get("levels"),
                    "activeState": active_state,
                    "counted": False,
                }
            )
            continue
        detail = {
            "contributionId": contribution_id,
            "label": raw.get("label"),
            "levels": levels,
            "activeState": active_state,
            "provenanceKind": provenance,
            "rawSourceText": raw.get("rawSourceText", ""),
            "counted": False,
        }
        if active_state == "inactive":
            addition_details.append(detail)
            continue
        if active_state == "unknown":
            reasons.append(
                _reason(
                    "ADDITIONAL_LINK_LEVEL_UNKNOWN",
                    "An unknown additional Link gem level contribution blocks final resolution",
                    contributionId=contribution_id,
                    label=raw.get("label"),
                )
            )
            addition_details.append(detail)
            continue
        if active_state != "active":
            reasons.append(
                _reason(
                    "ADDITIONAL_LINK_LEVEL_STATE_INVALID",
                    "Additional Link gem level active state is not recognized",
                    contributionId=contribution_id,
                )
            )
            addition_details.append(detail)
            continue
        if provenance in {None, "unreviewed"} or provenance == "":
            reasons.append(
                _reason(
                    "ADDITIONAL_LINK_LEVEL_UNREVIEWED",
                    "An active additional Link gem level contribution requires reviewed provenance",
                    contributionId=contribution_id,
                    label=raw.get("label"),
                )
            )
            addition_details.append(detail)
            continue
        if provenance == "catalog-default":
            if contribution_id != "empowered-bond" or levels != 2:
                reasons.append(
                    _reason(
                        "ADDITIONAL_LINK_LEVEL_UNREVIEWED",
                        "catalog-default additional Link levels are only valid for empowered-bond with levels 2",
                        contributionId=contribution_id,
                        label=raw.get("label"),
                    )
                )
                addition_details.append(detail)
                continue
        detail["counted"] = True
        addition_details.append(detail)
        additional_total += levels
    breakdown = {
        "baseLevel": base_level,
        "baseLevelProvenance": level_block.get("baseLevelProvenance"),
        "additionalLinkGemLevels": addition_details,
        "additionalTotal": additional_total if not reasons else None,
        "effectiveLevel": None if reasons else base_level + additional_total,
    }
    if reasons:
        return base_level, None, None, breakdown, reasons
    effective = base_level + additional_total
    return base_level, additional_total, effective, breakdown, reasons


def evaluate_flame_link(
    player_chain_input: Mapping[str, Any],
    level_table: FlameLinkLevelTable,
) -> FlameLinkResult:
    """Evaluate the owner-approved manual-first Flame Link player-chain formula."""

    golden = player_chain_input.get("goldenGlory")
    direct = player_chain_input.get("directLinkBuffEffect")
    conditionals = player_chain_input.get("conditionalContributions")
    level_block = player_chain_input.get("flameLinkLevel")
    life_block = player_chain_input.get("luminaryMaximumLife")
    if not all(
        isinstance(value, Mapping)
        for value in (golden, direct, level_block, life_block)
    ):
        return _unavailable(
            state="unavailable",
            reasons=(
                _reason(
                    "FLAME_LINK_INPUT_SHAPE",
                    "Flame Link player-chain input is missing required objects",
                ),
            ),
        )
    assert isinstance(golden, Mapping)
    assert isinstance(direct, Mapping)
    assert isinstance(level_block, Mapping)
    assert isinstance(life_block, Mapping)

    gg_value, gg_lexeme, gg_detail, gg_reasons = _resolve_golden_glory(golden)
    direct_value, direct_lexeme, direct_detail, direct_reasons = _resolve_direct(direct)
    active_conditionals, conditional_details, conditional_reasons = (
        _resolve_conditionals(conditionals)
    )
    base_level, additional_levels, effective_level, level_breakdown, level_reasons = (
        _resolve_levels(level_block)
    )

    life_review = life_block.get("reviewState")
    life_parsed = _parsed_optional(life_block.get("reviewedLife"))
    life_lexeme = None if life_parsed is None else life_parsed.lexeme
    life_reasons: list[dict[str, Any]] = []
    if life_review != "reviewed" or life_parsed is None:
        life_reasons.append(
            _reason(
                "LUMINARY_MAXIMUM_LIFE_UNREVIEWED",
                "Reviewed Luminary Maximum Life is required",
            )
        )
    elif life_parsed.value < 0:
        life_reasons.append(
            _reason(
                "LUMINARY_MAXIMUM_LIFE_NEGATIVE",
                "Reviewed Luminary Maximum Life must be nonnegative; zero is valid",
            )
        )

    contribution_breakdown = {
        "goldenGlory": gg_detail,
        "directLinkBuffEffect": direct_detail,
        "conditionalContributions": conditional_details,
    }
    blocking = (
        gg_reasons
        + direct_reasons
        + conditional_reasons
        + level_reasons
        + life_reasons
    )
    if blocking:
        return _unavailable(
            state="unavailable",
            reasons=tuple(blocking),
            contribution_breakdown=contribution_breakdown,
            level_breakdown=level_breakdown,
            base_level=base_level,
            additional_levels=additional_levels,
            effective_level=effective_level,
            life_lexeme=life_lexeme,
        )

    assert gg_value is not None and direct_value is not None
    assert active_conditionals is not None
    assert effective_level is not None and life_parsed is not None
    assert base_level is not None and additional_levels is not None

    row_for_level = level_table.row_for(effective_level)
    operands = [
        gg_value,
        direct_value,
        life_parsed.value,
        LIFE_COMPONENT_FRACTION,
        Decimal(100),
        Decimal(1),
        *active_conditionals,
    ]
    if row_for_level is not None:
        operands.extend((row_for_level.flatMin, row_for_level.flatMax))

    with localcontext(numeric_context_for(*operands)):
        conditional_value = sum(active_conditionals, start=Decimal(0))
        conditional_lexeme = _lexeme(conditional_value)
        net = gg_value + direct_value + conditional_value
        multiplier = Decimal(1) + (net / Decimal(100))
        if multiplier < 0:
            return _unavailable(
                state="unsupported-effect-multiplier",
                reasons=(
                    _reason(
                        "UNSUPPORTED_EFFECT_MULTIPLIER",
                        "Link effect multiplier must be nonnegative; negative multipliers are not clamped",
                        netLinkSkillBuffEffectPct=_lexeme(net),
                        linkEffectMultiplier=_lexeme(multiplier),
                    ),
                ),
                contribution_breakdown={
                    **contribution_breakdown,
                    "netLinkSkillBuffEffectPct": _lexeme(net),
                    "linkEffectMultiplier": _lexeme(multiplier),
                },
                level_breakdown=level_breakdown,
                base_level=base_level,
                additional_levels=additional_levels,
                effective_level=effective_level,
                life_lexeme=life_lexeme,
            )

        if (
            effective_level < level_table.minimumLevel
            or effective_level > level_table.maximumLevel
        ):
            return _unavailable(
                state="unsupported-effective-level",
                reasons=(
                    _reason(
                        "UNSUPPORTED_EFFECTIVE_LEVEL",
                        "Effective Flame Link level is outside the supported 1-40 table; values are not clamped or extrapolated",
                        effectiveFlameLinkLevel=effective_level,
                    ),
                ),
                contribution_breakdown={
                    **contribution_breakdown,
                    "netLinkSkillBuffEffectPct": _lexeme(net),
                    "linkEffectMultiplier": _lexeme(multiplier),
                },
                level_breakdown=level_breakdown,
                base_level=base_level,
                additional_levels=additional_levels,
                effective_level=effective_level,
                life_lexeme=life_lexeme,
            )

        row = level_table.row_for(effective_level)
        if row is None:  # pragma: no cover - guarded by table completeness
            return _unavailable(
                state="unavailable",
                reasons=(
                    _reason(
                        "FLAME_LINK_LEVEL_ROW_MISSING",
                        f"Flame Link level table has no row for effective level {effective_level}",
                    ),
                ),
                level_breakdown=level_breakdown,
                base_level=base_level,
                additional_levels=additional_levels,
                effective_level=effective_level,
                life_lexeme=life_lexeme,
            )

        life_component = life_parsed.value * LIFE_COMPONENT_FRACTION
        unscaled_min = row.flatMin + life_component
        unscaled_max = row.flatMax + life_component
        exact_min = unscaled_min * multiplier
        exact_max = unscaled_max * multiplier
        if multiplier == 0:
            modelled_min = 0
            modelled_max = 0
        else:
            modelled_min = round_half_up(exact_min)
            modelled_max = round_half_up(exact_max)

        return FlameLinkResult(
            outputId=OUTPUT_ID,
            label=OUTPUT_LABEL,
            targetGameVersion=TARGET_GAME_VERSION,
            formulaVersionId=FORMULA_VERSION_ID,
            roundingPolicyId=ROUNDING_POLICY_ID,
            roundingPolicyLabel=ROUNDING_POLICY_LABEL,
            state="available",
            available=True,
            goldenGloryContributionPct=gg_lexeme,
            directLinkContributionPct=direct_lexeme,
            conditionalContributionPct=conditional_lexeme,
            netLinkSkillBuffEffectPct=_lexeme(net),
            linkEffectMultiplier=_lexeme(multiplier),
            baseFlameLinkLevel=base_level,
            additionalLinkGemLevels=additional_levels,
            effectiveFlameLinkLevel=effective_level,
            luminaryMaximumLife=life_lexeme,
            lifeComponent=_lexeme(life_component),
            levelFlatMin=_lexeme(row.flatMin),
            levelFlatMax=_lexeme(row.flatMax),
            unscaledMin=_lexeme(unscaled_min),
            unscaledMax=_lexeme(unscaled_max),
            exactPreRoundMin=_lexeme(exact_min),
            exactPreRoundMax=_lexeme(exact_max),
            modelledIntegerMin=modelled_min,
            modelledIntegerMax=modelled_max,
            contributionBreakdown={
                **contribution_breakdown,
                "netLinkSkillBuffEffectPct": _lexeme(net),
                "linkEffectMultiplier": _lexeme(multiplier),
            },
            levelBreakdown=level_breakdown,
            reasons=(),
        )
