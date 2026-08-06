"""Canonical BUILD-003 domain exports."""

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
from .flame_link import (
    FORMULA_VERSION_ID as FLAME_LINK_FORMULA_VERSION_ID,
    OUTPUT_ID as FLAME_LINK_OUTPUT_ID,
    OUTPUT_LABEL as FLAME_LINK_OUTPUT_LABEL,
    ROUNDING_POLICY_ID as FLAME_LINK_ROUNDING_POLICY_ID,
    FlameLinkLevelTable,
    FlameLinkResult,
    FlameLinkTableError,
    evaluate_flame_link,
    load_flame_link_level_table,
    parse_flame_link_level_table_bytes,
    round_half_up,
)
from .player_chain_recognition import (
    RecognizedPlayerChainLine,
    recognize_player_chain_sources,
    recognize_player_chain_text,
)

__all__ = [
    "DECIMAL_DIGIT_LIMIT",
    "ENMITY_CAP",
    "ENMITY_OUTPUT_ID",
    "ENMITY_OUTPUT_LABEL",
    "ENMITY_TARGET_OUTPUT_ID",
    "FLAME_LINK_FORMULA_VERSION_ID",
    "FLAME_LINK_OUTPUT_ID",
    "FLAME_LINK_OUTPUT_LABEL",
    "FLAME_LINK_ROUNDING_POLICY_ID",
    "TARGET_GAME_VERSION",
    "DecimalInputError",
    "EnmityResult",
    "FlameLinkLevelTable",
    "FlameLinkResult",
    "FlameLinkTableError",
    "ParsedDecimal",
    "RecognizedPlayerChainLine",
    "TargetResult",
    "evaluate_enmity",
    "evaluate_flame_link",
    "load_flame_link_level_table",
    "parse_decimal_text",
    "parse_flame_link_level_table_bytes",
    "recognize_player_chain_sources",
    "recognize_player_chain_text",
    "round_half_up",
]
