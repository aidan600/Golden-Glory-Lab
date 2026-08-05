"""Canonical BUILD domain calculations and input parsers."""

from .decimal_input import (
    DECIMAL_DIGIT_LIMIT,
    DecimalInputError,
    ParsedDecimal,
    parse_decimal_text,
)
from .enmity import (
    ENMITY_CAP,
    ENMITY_OUTPUT_ID,
    ENMITY_OUTPUT_LABEL,
    ENMITY_TARGET_OUTPUT_ID,
    TARGET_GAME_VERSION,
    EnmityResult,
    TargetResult,
    evaluate_enmity,
)

__all__ = [
    "DECIMAL_DIGIT_LIMIT",
    "ENMITY_CAP",
    "ENMITY_OUTPUT_ID",
    "ENMITY_OUTPUT_LABEL",
    "ENMITY_TARGET_OUTPUT_ID",
    "TARGET_GAME_VERSION",
    "DecimalInputError",
    "EnmityResult",
    "ParsedDecimal",
    "TargetResult",
    "evaluate_enmity",
    "parse_decimal_text",
]
