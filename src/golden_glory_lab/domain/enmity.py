"""Canonical isolated manual Enmity result and target comparison."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Mapping

from golden_glory_lab.evidence_gate.model import GateDecision

from .decimal_input import ParsedDecimal, parse_decimal_text

TARGET_GAME_VERSION = "Path of Exile 1 3.29.1"
ENMITY_OUTPUT_ID = "enmity-own-fire-penetration-contribution-v1"
ENMITY_TARGET_OUTPUT_ID = "enmity-only-target-comparison-v1"
ENMITY_OUTPUT_LABEL = "Enmity’s own Fire Penetration contribution"
ENMITY_CAP = 200

MEASUREMENT_CONTEXT_FIELDS = (
    "mercenaryIdentityLevel",
    "activeStateSelection",
    "zoneOrUiContext",
    "relevantEffectsConditions",
    "equipmentStateDescription",
    "captureTimingDescription",
)


@dataclass(frozen=True, slots=True)
class TargetResult:
    state: str
    targetLexeme: str | None
    gap: int | None
    surplus: int | None
    capHeadroom: int | None
    reasons: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "targetLexeme": self.targetLexeme,
            "gap": self.gap,
            "surplus": self.surplus,
            "capHeadroom": self.capHeadroom,
            "reasons": [dict(reason) for reason in self.reasons],
        }


@dataclass(frozen=True, slots=True)
class EnmityResult:
    outputId: str
    label: str
    targetGameVersion: str
    state: str
    available: bool
    value: int | None
    overcap: int | None
    itemSpecificCap: int | None
    inputBeyondCap: int | None
    inputLexemes: dict[str, str | None]
    reasons: tuple[dict[str, Any], ...]
    gateDecision: dict[str, Any]
    target: TargetResult

    def to_dict(self) -> dict[str, Any]:
        return {
            "outputId": self.outputId,
            "label": self.label,
            "targetGameVersion": self.targetGameVersion,
            "state": self.state,
            "available": self.available,
            "value": self.value,
            "overcap": self.overcap,
            "itemSpecificCap": self.itemSpecificCap,
            "inputBeyondCap": self.inputBeyondCap,
            "inputLexemes": dict(self.inputLexemes),
            "reasons": [dict(reason) for reason in self.reasons],
            "gateDecision": dict(self.gateDecision),
            "target": self.target.to_dict(),
        }


def _reason(code: str, message: str, **values: Any) -> dict[str, Any]:
    return {"code": code, "message": message, **values}


def _target_unavailable(
    state: str,
    lexeme: str | None,
    *reasons: dict[str, Any],
) -> TargetResult:
    return TargetResult(state, lexeme, None, None, None, tuple(reasons))


def _base_result(
    manual_input: Mapping[str, Any],
    gate: GateDecision,
    *,
    state: str,
    reasons: tuple[dict[str, Any], ...],
    target_state: str = "unavailable",
) -> EnmityResult:
    target_lexeme = manual_input.get("target")
    return EnmityResult(
        outputId=ENMITY_OUTPUT_ID,
        label=ENMITY_OUTPUT_LABEL,
        targetGameVersion=TARGET_GAME_VERSION,
        state=state,
        available=False,
        value=None,
        overcap=None,
        itemSpecificCap=None,
        inputBeyondCap=None,
        inputLexemes={
            "U": manual_input.get("finalUncappedFireResistance"),
            "M": manual_input.get("maximumFireResistance"),
        },
        reasons=reasons,
        gateDecision=gate.to_dict(),
        target=_target_unavailable(
            target_state,
            target_lexeme,
            _reason(
                "ENMITY_CONTRIBUTION_UNAVAILABLE",
                "Target reporting requires an available isolated Enmity contribution",
            ),
        ),
    )


def _parsed_optional(value: Any) -> ParsedDecimal | None:
    return None if value is None else parse_decimal_text(value)


def _measurement_context_complete(value: Any) -> tuple[bool, tuple[str, ...]]:
    if not isinstance(value, Mapping):
        return False, MEASUREMENT_CONTEXT_FIELDS
    missing = tuple(
        field
        for field in MEASUREMENT_CONTEXT_FIELDS
        if not isinstance(value.get(field), str) or not value[field].strip()
    )
    return not missing, missing


def _target_result(
    target: ParsedDecimal | None,
    contribution: int,
    gate: GateDecision,
) -> TargetResult:
    lexeme = None if target is None else target.lexeme
    if target is None:
        return TargetResult("not-configured", None, None, None, None, ())
    if not gate.available:
        return _target_unavailable(
            gate.state,
            lexeme,
            *(
                {
                    **reason.to_dict(),
                    "code": reason.code,
                }
                for reason in gate.reasons
            ),
        )
    if not target.integral:
        return _target_unavailable(
            "invalid-target",
            lexeme,
            _reason(
                "FRACTIONAL_TARGET_UNSUPPORTED",
                "A fractional target is preserved but BUILD-002 target reporting is integral only",
            ),
        )
    target_value = int(target.value)
    if target_value < 0:
        return _target_unavailable(
            "invalid-target",
            lexeme,
            _reason("TARGET_BELOW_ZERO", "An Enmity-only target below 0 is invalid"),
        )
    if target_value > ENMITY_CAP:
        return _target_unavailable(
            "unreachable-by-Enmity",
            lexeme,
            _reason(
                "TARGET_ABOVE_ENMITY_CAP",
                "The target is above Enmity's item-specific 200% contribution cap",
            ),
        )
    return TargetResult(
        state="available",
        targetLexeme=lexeme,
        gap=max(0, target_value - contribution),
        surplus=max(0, contribution - target_value),
        capHeadroom=max(0, ENMITY_CAP - contribution),
        reasons=(),
    )


def evaluate_enmity(
    manual_input: Mapping[str, Any],
    main_gate: GateDecision,
    target_gate: GateDecision,
) -> EnmityResult:
    """Evaluate BUILD-002's exact result-state precedence and isolated formula."""

    equipped = manual_input.get("equippedState")
    if equipped == "not-equipped":
        return _base_result(
            manual_input,
            main_gate,
            state="not-applicable",
            reasons=(
                _reason(
                    "ENMITY_NOT_EQUIPPED",
                    "The isolated Enmity contribution is not applicable",
                ),
            ),
            target_state="not-applicable",
        )
    if equipped != "equipped":
        return _base_result(
            manual_input,
            main_gate,
            state="unavailable",
            reasons=(
                _reason(
                    "ENMITY_EQUIPPED_STATE_UNKNOWN",
                    "Explicit equipped state is required and is never inferred from item recognition",
                ),
            ),
        )

    if not main_gate.available:
        return _base_result(
            manual_input,
            main_gate,
            state=main_gate.state,
            reasons=tuple(reason.to_dict() for reason in main_gate.reasons),
        )

    acknowledgement = manual_input.get("targetGameVersionAcknowledgement")
    if acknowledgement == "other-version":
        return _base_result(
            manual_input,
            main_gate,
            state="version-mismatched",
            reasons=(
                _reason(
                    "TARGET_GAME_VERSION_MISMATCH",
                    f"The manual result contract targets {TARGET_GAME_VERSION}",
                ),
            ),
        )
    if acknowledgement != "confirmed-3.29.1":
        return _base_result(
            manual_input,
            main_gate,
            state="unavailable",
            reasons=(
                _reason(
                    "TARGET_GAME_VERSION_NOT_CONFIRMED",
                    f"Explicit acknowledgement of {TARGET_GAME_VERSION} is required",
                ),
            ),
        )

    parsed_u = _parsed_optional(manual_input.get("finalUncappedFireResistance"))
    parsed_m = _parsed_optional(manual_input.get("maximumFireResistance"))
    if parsed_u is None or parsed_m is None:
        missing = []
        if parsed_u is None:
            missing.append("U")
        if parsed_m is None:
            missing.append("M")
        return _base_result(
            manual_input,
            main_gate,
            state="missing",
            reasons=(
                _reason(
                    "MISSING_MANUAL_INPUT",
                    f"Required final manual input(s) are missing: {', '.join(missing)}",
                    missingInputs=missing,
                ),
            ),
        )

    context_complete, missing_context = _measurement_context_complete(
        manual_input.get("measurementContext")
    )
    inclusion = manual_input.get("equipmentInclusionState")
    manual_reasons: list[dict[str, Any]] = []
    if not context_complete:
        manual_reasons.append(
            _reason(
                "MEASUREMENT_CONTEXT_INCOMPLETE",
                "Every structured measurement-context field must be recorded",
                missingFields=list(missing_context),
            )
        )
    if inclusion == "unrecorded":
        manual_reasons.append(
            _reason(
                "EQUIPMENT_INCLUSION_STATE_UNRECORDED",
                "Equipment inclusion must be explicitly recorded, including unknown",
            )
        )
    if manual_reasons:
        return _base_result(
            manual_input,
            main_gate,
            state="manually-required",
            reasons=tuple(manual_reasons),
        )

    if not parsed_u.integral or not parsed_m.integral:
        return _base_result(
            manual_input,
            main_gate,
            state="rounding-evidence-required",
            reasons=(
                _reason(
                    "FRACTIONAL_INPUT_REQUIRES_ROUNDING_EVIDENCE",
                    "Fractional U or M is preserved but receives no invented rounding",
                ),
            ),
        )

    zero = Decimal(0)
    overcap_decimal = max(zero, parsed_u.value - parsed_m.value)
    contribution_decimal = min(Decimal(ENMITY_CAP), overcap_decimal)
    overcap = int(overcap_decimal)
    contribution = int(contribution_decimal)
    beyond_cap = max(0, overcap - ENMITY_CAP)
    target = _parsed_optional(manual_input.get("target"))
    return EnmityResult(
        outputId=ENMITY_OUTPUT_ID,
        label=ENMITY_OUTPUT_LABEL,
        targetGameVersion=TARGET_GAME_VERSION,
        state="available",
        available=True,
        value=contribution,
        overcap=overcap,
        itemSpecificCap=ENMITY_CAP,
        inputBeyondCap=beyond_cap,
        inputLexemes={"U": parsed_u.lexeme, "M": parsed_m.lexeme},
        reasons=(),
        gateDecision=main_gate.to_dict(),
        target=_target_result(target, contribution, target_gate),
    )
