"""Canonical BUILD-003 state, strict v2/v1 migration, and atomic persistence."""

from __future__ import annotations

import copy
import json
import os
import re
import tempfile
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NoReturn

from golden_glory_lab.domain import DECIMAL_DIGIT_LIMIT, DecimalInputError
from golden_glory_lab.domain import parse_decimal_text

from . import codec_v2 as v2_codec

DOCUMENT_TYPE = v2_codec.DOCUMENT_TYPE
BUILD_STATE_SCHEMA_VERSION = "3.0.0"
APPLICATION_DATA_CONTRACT_VERSION = "3.0.0"
IMPORTER_CONTRACT_VERSION = v2_codec.IMPORTER_CONTRACT_VERSION
V2_BUILD_STATE_SCHEMA_VERSION = v2_codec.BUILD_STATE_SCHEMA_VERSION
V2_APPLICATION_DATA_CONTRACT_VERSION = v2_codec.APPLICATION_DATA_CONTRACT_VERSION
LEGACY_BUILD_STATE_SCHEMA_VERSION = v2_codec.LEGACY_BUILD_STATE_SCHEMA_VERSION
LEGACY_APPLICATION_DATA_CONTRACT_VERSION = (
    v2_codec.LEGACY_APPLICATION_DATA_CONTRACT_VERSION
)
MERCENARY_SOURCE_MODES = v2_codec.MERCENARY_SOURCE_MODES
MANUAL_ENTRY_LIMITS = v2_codec.MANUAL_ENTRY_LIMITS
MAX_USER_NOTES_CHARACTERS = v2_codec.MAX_USER_NOTES_CHARACTERS
BuildStateError = v2_codec.BuildStateError
COPIED_ROLES = v2_codec.COPIED_ROLES
ENMITY_EQUIPPED_STATES = v2_codec.ENMITY_EQUIPPED_STATES
EQUIPMENT_INCLUSION_STATES = v2_codec.EQUIPMENT_INCLUSION_STATES
TARGET_VERSION_ACKNOWLEDGEMENTS = v2_codec.TARGET_VERSION_ACKNOWLEDGEMENTS
MEASUREMENT_CONTEXT_FIELDS = v2_codec.MEASUREMENT_CONTEXT_FIELDS
MAX_CONTEXT_FIELD_CHARACTERS = v2_codec.MAX_CONTEXT_FIELD_CHARACTERS

ALLOCATED_STATES = {"unknown", "allocated", "not-allocated"}
MERCENARY_TARGET_STATES = {"unknown", "yes", "no"}
PROVENANCE_KINDS = {
    "manual-reviewed",
    "recognized-reviewed",
    "unreviewed",
    "catalog-default",
}
REVIEW_STATES = {"unreviewed", "reviewed"}
CONDITION_STATES = {"active", "inactive", "unknown"}
CONDITIONAL_KINDS = {"powerful-bond", "inspiring-bond", "manual"}
ACTIVE_STATES = {"unknown", "active", "inactive"}
BASE_LEVEL_PROVENANCES = {
    "manual-benchmark-default",
    "imported-recognized",
    "manual-reviewed",
}
ROUNDING_POLICY_ID = "modelled-nearest-integer-half-up-v1"
FORMULA_VERSION_ID = "flame-link-player-chain-v1"
DEFAULT_BASE_FLAME_LINK_LEVEL = 21
MAX_CONDITIONAL_CONTRIBUTIONS = 64
MAX_ADDITIONAL_LEVEL_CONTRIBUTIONS = 32
MAX_RAW_SOURCE_TEXT_CHARACTERS = 100_000
MAX_CONTRIBUTION_ID_CHARACTERS = 80
MAX_CONTRIBUTION_LABEL_CHARACTERS = 120
RECOGNITION_SOURCE_KINDS = {"none", "advisory-text", "pob-import", "copied-text"}
CATALOG_POWERFUL_BOND_ID = "powerful-bond"
CATALOG_INSPIRING_BOND_ID = "inspiring-bond"
CATALOG_EMPOWERED_BOND_ID = "empowered-bond"
CATALOG_BOND_VALUE_PCT = "20"
CATALOG_EMPOWERED_LEVELS = 2
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")

_JSON_ESCAPE_BYTES_PER_PYTHON_CHARACTER = 12
_MAX_DECIMAL_LEXEME_CHARACTERS = DECIMAL_DIGIT_LIMIT + 2
_MAX_FLAME_LINK_CANONICAL_CHARACTERS = (
    # golden glory + direct + life reviewed fields and enums/provenance/raw text
    3 * (_MAX_DECIMAL_LEXEME_CHARACTERS + 40 + MAX_RAW_SOURCE_TEXT_CHARACTERS)
    + MAX_CONDITIONAL_CONTRIBUTIONS
    * (
        MAX_CONTRIBUTION_ID_CHARACTERS
        + MAX_CONTRIBUTION_LABEL_CHARACTERS
        + _MAX_DECIMAL_LEXEME_CHARACTERS
        + 40
        + MAX_RAW_SOURCE_TEXT_CHARACTERS
    )
    + MAX_ADDITIONAL_LEVEL_CONTRIBUTIONS
    * (
        MAX_CONTRIBUTION_ID_CHARACTERS
        + MAX_CONTRIBUTION_LABEL_CHARACTERS
        + 16
        + 40
        + MAX_RAW_SOURCE_TEXT_CHARACTERS
    )
    + 64  # version ids and base level metadata
)
MAX_SAVED_STATE_FILE_BYTES = (
    v2_codec.MAX_SAVED_STATE_FILE_BYTES
    + _MAX_FLAME_LINK_CANONICAL_CHARACTERS
    * _JSON_ESCAPE_BYTES_PER_PYTHON_CHARACTER
)

_DOCUMENT_KEY_ORDER = (
    "documentType",
    "schemaVersion",
    "applicationDataContractVersion",
    "importerContractVersion",
    "importedResult",
    "importedResultSha256",
    "playerItemSetOccurrenceId",
    "mercenarySourceMode",
    "mercenaryItemSetOccurrenceId",
    "manualMercenaryEquipment",
    "copiedItemEntries",
    "enmityManualInput",
    "flameLinkPlayerChain",
    "userNotes",
)
_DOCUMENT_KEYS = set(_DOCUMENT_KEY_ORDER)
_MANUAL_ENTRY_KEY_ORDER = v2_codec._MANUAL_ENTRY_KEY_ORDER
_COPIED_ENTRY_KEY_ORDER = v2_codec._COPIED_ENTRY_KEY_ORDER
_ENMITY_KEY_ORDER = v2_codec._ENMITY_KEY_ORDER
_LOCATOR_KEY_ORDER = v2_codec._LOCATOR_KEY_ORDER

_GOLDEN_GLORY_KEY_ORDER = (
    "allocatedState",
    "mercenaryTargetState",
    "reviewedLightRadiusPct",
    "provenanceKind",
    "reviewState",
    "rawSourceText",
    "recognitionSource",
)
_DIRECT_KEY_ORDER = (
    "reviewedDirectPct",
    "provenanceKind",
    "reviewState",
    "rawSourceText",
    "recognitionSource",
)
_CONDITIONAL_KEY_ORDER = (
    "contributionId",
    "label",
    "valuePct",
    "conditionState",
    "kind",
    "provenanceKind",
    "rawSourceText",
    "recognitionSource",
)
_ADDITIONAL_LEVEL_KEY_ORDER = (
    "contributionId",
    "label",
    "levels",
    "activeState",
    "provenanceKind",
    "rawSourceText",
    "recognitionSource",
)
_LEVEL_KEY_ORDER = (
    "baseLevel",
    "baseLevelProvenance",
    "additionalLinkGemLevels",
)
_LIFE_KEY_ORDER = (
    "reviewedLife",
    "provenanceKind",
    "reviewState",
    "rawSourceText",
    "recognitionSource",
)
_RECOGNITION_SOURCE_KEY_ORDER = (
    "kind",
    "digest",
)
_FLAME_LINK_KEY_ORDER = (
    "goldenGlory",
    "directLinkBuffEffect",
    "conditionalContributions",
    "flameLinkLevel",
    "luminaryMaximumLife",
    "roundingPolicyId",
    "formulaVersionId",
)


@dataclass(frozen=True, slots=True)
class DecodedBuildState:
    document: dict[str, Any]
    sourceSchemaVersion: str
    migrated: bool
    canonicalV3Bytes: bytes


def _fail(code: str, message: str) -> NoReturn:
    raise BuildStateError(code, message)


def _require_object(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail("SHAPE_TYPE", f"{context} must be an object")
    return value


def _require_list(value: Any, context: str) -> list[Any]:
    if not isinstance(value, list):
        _fail("SHAPE_TYPE", f"{context} must be an array")
    return value


def _require_string(
    value: Any, context: str, *, nullable: bool = False
) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str):
        _fail("SHAPE_TYPE", f"{context} must be a string")
    return value


def _require_exact_keys(
    value: Mapping[str, Any], expected: set[str], context: str
) -> None:
    missing = sorted(expected - set(value))
    unknown = sorted(set(value) - expected)
    if missing:
        _fail("SHAPE_MISSING_FIELD", f"{context} is missing: {', '.join(missing)}")
    if unknown:
        _fail("SHAPE_UNKNOWN_FIELD", f"{context} has unknown fields: {', '.join(unknown)}")


def _require_utf8(value: str, context: str) -> None:
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeEncodeError as error:
        _fail(
            "STRICT_UTF8_REQUIRED",
            f"{context} is not strict UTF-8 encodable at character {error.start}",
        )


def _safe_deepcopy(value: Any, *, code: str, message: str) -> Any:
    try:
        return copy.deepcopy(value)
    except RecursionError:
        _fail(code, message)


def empty_measurement_context() -> dict[str, str]:
    return v2_codec.empty_measurement_context()


def empty_enmity_manual_input() -> dict[str, Any]:
    return v2_codec.empty_enmity_manual_input()


def empty_recognition_source() -> dict[str, Any]:
    return {"kind": "none", "digest": None}


def empty_flame_link_player_chain() -> dict[str, Any]:
    return {
        "goldenGlory": {
            "allocatedState": "unknown",
            "mercenaryTargetState": "unknown",
            "reviewedLightRadiusPct": None,
            "provenanceKind": "unreviewed",
            "reviewState": "unreviewed",
            "rawSourceText": "",
            "recognitionSource": empty_recognition_source(),
        },
        "directLinkBuffEffect": {
            "reviewedDirectPct": None,
            "provenanceKind": "unreviewed",
            "reviewState": "unreviewed",
            "rawSourceText": "",
            "recognitionSource": empty_recognition_source(),
        },
        "conditionalContributions": [
            {
                "contributionId": CATALOG_POWERFUL_BOND_ID,
                "label": "Powerful Bond",
                "valuePct": CATALOG_BOND_VALUE_PCT,
                "conditionState": "unknown",
                "kind": "powerful-bond",
                "provenanceKind": "catalog-default",
                "rawSourceText": "",
                "recognitionSource": empty_recognition_source(),
            },
            {
                "contributionId": CATALOG_INSPIRING_BOND_ID,
                "label": "Inspiring Bond",
                "valuePct": CATALOG_BOND_VALUE_PCT,
                "conditionState": "unknown",
                "kind": "inspiring-bond",
                "provenanceKind": "catalog-default",
                "rawSourceText": "",
                "recognitionSource": empty_recognition_source(),
            },
        ],
        "flameLinkLevel": {
            "baseLevel": DEFAULT_BASE_FLAME_LINK_LEVEL,
            "baseLevelProvenance": "manual-benchmark-default",
            "additionalLinkGemLevels": [
                {
                    "contributionId": CATALOG_EMPOWERED_BOND_ID,
                    "label": "Empowered Bond",
                    "levels": CATALOG_EMPOWERED_LEVELS,
                    "activeState": "unknown",
                    "provenanceKind": "catalog-default",
                    "rawSourceText": "",
                    "recognitionSource": empty_recognition_source(),
                }
            ],
        },
        "luminaryMaximumLife": {
            "reviewedLife": None,
            "provenanceKind": "unreviewed",
            "reviewState": "unreviewed",
            "rawSourceText": "",
            "recognitionSource": empty_recognition_source(),
        },
        "roundingPolicyId": ROUNDING_POLICY_ID,
        "formulaVersionId": FORMULA_VERSION_ID,
    }


def empty_document() -> dict[str, Any]:
    document = v2_codec.empty_document()
    document["schemaVersion"] = BUILD_STATE_SCHEMA_VERSION
    document["applicationDataContractVersion"] = APPLICATION_DATA_CONTRACT_VERSION
    document["flameLinkPlayerChain"] = empty_flame_link_player_chain()
    return document


def imported_result_digest(imported_result: Mapping[str, Any]) -> str:
    return v2_codec.imported_result_digest(imported_result)


def _validate_optional_decimal(value: Any, context: str) -> None:
    if value is None:
        return
    text = _require_string(value, context)
    assert text is not None
    try:
        parse_decimal_text(text)
    except DecimalInputError as error:
        _fail(error.code, f"{context}: {error.message}")


def _validate_optional_nonnegative_decimal(value: Any, context: str) -> None:
    if value is None:
        return
    text = _require_string(value, context)
    assert text is not None
    try:
        parsed = parse_decimal_text(text)
    except DecimalInputError as error:
        _fail(error.code, f"{context}: {error.message}")
    if parsed.value < 0:
        _fail(
            "LUMINARY_MAXIMUM_LIFE_NEGATIVE",
            f"{context} must be nonnegative; zero is valid",
        )


def _validate_provenance(value: Any, context: str) -> str:
    provenance = _require_string(value, context)
    assert provenance is not None
    if provenance not in PROVENANCE_KINDS:
        _fail("FLAME_LINK_PROVENANCE", f"{context} is not recognized")
    return provenance


def _validate_review_state(value: Any, context: str) -> str:
    review_state = _require_string(value, context)
    assert review_state is not None
    if review_state not in REVIEW_STATES:
        _fail("FLAME_LINK_REVIEW_STATE", f"{context} is not recognized")
    return review_state


def _validate_raw_source(value: Any, context: str) -> str:
    text = _require_string(value, context)
    assert text is not None
    if len(text) > MAX_RAW_SOURCE_TEXT_CHARACTERS:
        _fail("FLAME_LINK_RAW_TEXT_LIMIT", f"{context} is too long")
    _require_utf8(text, context)
    return text


def _validate_recognition_source(value: Any, context: str) -> dict[str, Any]:
    source = _require_object(value, context)
    _require_exact_keys(source, set(_RECOGNITION_SOURCE_KEY_ORDER), context)
    kind = _require_string(source["kind"], f"{context}.kind")
    assert kind is not None
    if kind not in RECOGNITION_SOURCE_KINDS:
        _fail("FLAME_LINK_RECOGNITION_SOURCE", f"{context}.kind is not recognized")
    digest = source["digest"]
    if digest is None:
        if kind != "none":
            _fail(
                "FLAME_LINK_RECOGNITION_SOURCE",
                f"{context}.digest is required when kind is not none",
            )
        return source
    digest_text = _require_string(digest, f"{context}.digest")
    assert digest_text is not None
    if not _DIGEST_RE.fullmatch(digest_text):
        _fail(
            "FLAME_LINK_RECOGNITION_SOURCE",
            f"{context}.digest must be a 64-character lowercase hex digest",
        )
    return source


def _validate_reviewed_field_semantics(
    *,
    context: str,
    provenance: str,
    review_state: str,
    value: Any,
    raw_source_text: str,
    recognition_source: Mapping[str, Any],
) -> None:
    if provenance == "unreviewed":
        if review_state != "unreviewed":
            _fail(
                "FLAME_LINK_PROVENANCE_INVARIANT",
                f"{context}: unreviewed provenance requires unreviewed state",
            )
        return
    if provenance == "recognized-reviewed":
        if review_state != "reviewed" or value is None:
            _fail(
                "FLAME_LINK_PROVENANCE_INVARIANT",
                f"{context}: recognized-reviewed requires reviewed value",
            )
        has_raw = isinstance(raw_source_text, str) and bool(raw_source_text.strip())
        has_digest = (
            recognition_source.get("kind") != "none"
            and recognition_source.get("digest") is not None
        )
        if not has_raw and not has_digest:
            _fail(
                "FLAME_LINK_PROVENANCE_INVARIANT",
                f"{context}: recognized-reviewed requires rawSourceText or recognitionSource digest",
            )
        return
    if provenance == "manual-reviewed":
        if review_state != "reviewed" or value is None:
            _fail(
                "FLAME_LINK_PROVENANCE_INVARIANT",
                f"{context}: manual-reviewed requires reviewed value",
            )
        return
    if provenance == "catalog-default":
        return


def _ensure_recognition_source(container: dict[str, Any]) -> None:
    if "recognitionSource" not in container or not isinstance(
        container.get("recognitionSource"), dict
    ):
        container["recognitionSource"] = empty_recognition_source()
        return
    source = container["recognitionSource"]
    if "kind" not in source:
        source["kind"] = "none"
    if "digest" not in source:
        source["digest"] = None


def inject_recognition_source_defaults(chain: Mapping[str, Any]) -> dict[str, Any]:
    """Inject recognitionSource defaults for pre-repair v3 documents."""

    updated = _safe_deepcopy(
        chain,
        code="OPEN_STATE_NESTING",
        message="Flame Link migration exceeds safe copy nesting limits",
    )
    for key in ("goldenGlory", "directLinkBuffEffect", "luminaryMaximumLife"):
        block = updated.get(key)
        if isinstance(block, dict):
            _ensure_recognition_source(block)
    conditionals = updated.get("conditionalContributions")
    if isinstance(conditionals, list):
        for entry in conditionals:
            if isinstance(entry, dict):
                _ensure_recognition_source(entry)
    level = updated.get("flameLinkLevel")
    if isinstance(level, dict):
        additions = level.get("additionalLinkGemLevels")
        if isinstance(additions, list):
            for entry in additions:
                if isinstance(entry, dict):
                    _ensure_recognition_source(entry)
    return updated


def _validate_flame_link_player_chain(value: Any) -> None:
    chain = _require_object(value, "flameLinkPlayerChain")
    _require_exact_keys(chain, set(_FLAME_LINK_KEY_ORDER), "flameLinkPlayerChain")

    golden = _require_object(chain["goldenGlory"], "flameLinkPlayerChain.goldenGlory")
    _require_exact_keys(golden, set(_GOLDEN_GLORY_KEY_ORDER), "flameLinkPlayerChain.goldenGlory")
    allocated = _require_string(
        golden["allocatedState"], "flameLinkPlayerChain.goldenGlory.allocatedState"
    )
    if allocated not in ALLOCATED_STATES:
        _fail("GOLDEN_GLORY_ALLOCATED_STATE", "Golden Glory allocated state is not recognized")
    target = _require_string(
        golden["mercenaryTargetState"],
        "flameLinkPlayerChain.goldenGlory.mercenaryTargetState",
    )
    if target not in MERCENARY_TARGET_STATES:
        _fail("GOLDEN_GLORY_TARGET_STATE", "Golden Glory Mercenary target state is not recognized")
    _validate_optional_decimal(
        golden["reviewedLightRadiusPct"],
        "flameLinkPlayerChain.goldenGlory.reviewedLightRadiusPct",
    )
    golden_provenance = _validate_provenance(
        golden["provenanceKind"], "flameLinkPlayerChain.goldenGlory.provenanceKind"
    )
    golden_review = _validate_review_state(
        golden["reviewState"], "flameLinkPlayerChain.goldenGlory.reviewState"
    )
    golden_raw = _validate_raw_source(
        golden["rawSourceText"], "flameLinkPlayerChain.goldenGlory.rawSourceText"
    )
    golden_recognition = _validate_recognition_source(
        golden["recognitionSource"],
        "flameLinkPlayerChain.goldenGlory.recognitionSource",
    )
    _validate_reviewed_field_semantics(
        context="flameLinkPlayerChain.goldenGlory",
        provenance=golden_provenance,
        review_state=golden_review,
        value=golden["reviewedLightRadiusPct"],
        raw_source_text=golden_raw,
        recognition_source=golden_recognition,
    )

    direct = _require_object(
        chain["directLinkBuffEffect"], "flameLinkPlayerChain.directLinkBuffEffect"
    )
    _require_exact_keys(
        direct, set(_DIRECT_KEY_ORDER), "flameLinkPlayerChain.directLinkBuffEffect"
    )
    _validate_optional_decimal(
        direct["reviewedDirectPct"],
        "flameLinkPlayerChain.directLinkBuffEffect.reviewedDirectPct",
    )
    direct_provenance = _validate_provenance(
        direct["provenanceKind"],
        "flameLinkPlayerChain.directLinkBuffEffect.provenanceKind",
    )
    direct_review = _validate_review_state(
        direct["reviewState"], "flameLinkPlayerChain.directLinkBuffEffect.reviewState"
    )
    direct_raw = _validate_raw_source(
        direct["rawSourceText"],
        "flameLinkPlayerChain.directLinkBuffEffect.rawSourceText",
    )
    direct_recognition = _validate_recognition_source(
        direct["recognitionSource"],
        "flameLinkPlayerChain.directLinkBuffEffect.recognitionSource",
    )
    _validate_reviewed_field_semantics(
        context="flameLinkPlayerChain.directLinkBuffEffect",
        provenance=direct_provenance,
        review_state=direct_review,
        value=direct["reviewedDirectPct"],
        raw_source_text=direct_raw,
        recognition_source=direct_recognition,
    )

    conditionals = _require_list(
        chain["conditionalContributions"],
        "flameLinkPlayerChain.conditionalContributions",
    )
    if len(conditionals) > MAX_CONDITIONAL_CONTRIBUTIONS:
        _fail(
            "CONDITIONAL_CONTRIBUTION_LIMIT",
            "Too many conditional Link Buff Effect contributions",
        )
    seen_conditional_ids: set[str] = set()
    for index, raw in enumerate(conditionals):
        context = f"flameLinkPlayerChain.conditionalContributions[{index}]"
        entry = _require_object(raw, context)
        _require_exact_keys(entry, set(_CONDITIONAL_KEY_ORDER), context)
        contribution_id = _require_string(entry["contributionId"], f"{context}.contributionId")
        label = _require_string(entry["label"], f"{context}.label")
        assert contribution_id is not None and label is not None
        if not contribution_id or len(contribution_id) > MAX_CONTRIBUTION_ID_CHARACTERS:
            _fail("CONDITIONAL_CONTRIBUTION_ID", f"{context}.contributionId is empty or too long")
        if contribution_id in seen_conditional_ids:
            _fail(
                "CONDITIONAL_CONTRIBUTION_ID",
                f"Duplicate conditional contribution ID {contribution_id}",
            )
        seen_conditional_ids.add(contribution_id)
        _require_utf8(contribution_id, f"{context}.contributionId")
        if not label or len(label) > MAX_CONTRIBUTION_LABEL_CHARACTERS:
            _fail("CONDITIONAL_CONTRIBUTION_LABEL", f"{context}.label is empty or too long")
        _require_utf8(label, f"{context}.label")
        _validate_optional_decimal(entry["valuePct"], f"{context}.valuePct")
        condition_state = _require_string(entry["conditionState"], f"{context}.conditionState")
        if condition_state not in CONDITION_STATES:
            _fail("CONDITIONAL_CONDITION_STATE", f"{context}.conditionState is not recognized")
        kind = _require_string(entry["kind"], f"{context}.kind")
        if kind not in CONDITIONAL_KINDS:
            _fail("CONDITIONAL_KIND", f"{context}.kind is not recognized")
        if contribution_id == CATALOG_POWERFUL_BOND_ID:
            if kind != "powerful-bond" or entry["valuePct"] != CATALOG_BOND_VALUE_PCT:
                _fail(
                    "CONDITIONAL_CATALOG_INVARIANT",
                    "powerful-bond catalog contribution must use kind powerful-bond and valuePct 20",
                )
        elif contribution_id == CATALOG_INSPIRING_BOND_ID:
            if kind != "inspiring-bond" or entry["valuePct"] != CATALOG_BOND_VALUE_PCT:
                _fail(
                    "CONDITIONAL_CATALOG_INVARIANT",
                    "inspiring-bond catalog contribution must use kind inspiring-bond and valuePct 20",
                )
        elif kind in {"powerful-bond", "inspiring-bond"}:
            _fail(
                "CONDITIONAL_CATALOG_INVARIANT",
                f"{context}: catalog kinds require matching catalog contribution IDs",
            )
        provenance = _validate_provenance(entry["provenanceKind"], f"{context}.provenanceKind")
        raw_text = _validate_raw_source(entry["rawSourceText"], f"{context}.rawSourceText")
        recognition = _validate_recognition_source(
            entry["recognitionSource"], f"{context}.recognitionSource"
        )
        if provenance == "unreviewed":
            _fail(
                "FLAME_LINK_PROVENANCE_INVARIANT",
                f"{context}: conditional contributions do not use unreviewed provenance",
            )
        if provenance == "recognized-reviewed":
            has_raw = bool(raw_text.strip())
            has_digest = (
                recognition.get("kind") != "none" and recognition.get("digest") is not None
            )
            if entry["valuePct"] is None or (not has_raw and not has_digest):
                _fail(
                    "FLAME_LINK_PROVENANCE_INVARIANT",
                    f"{context}: recognized-reviewed requires value and source identity",
                )
        if provenance == "manual-reviewed" and entry["valuePct"] is None:
            _fail(
                "FLAME_LINK_PROVENANCE_INVARIANT",
                f"{context}: manual-reviewed requires valuePct",
            )

    level = _require_object(chain["flameLinkLevel"], "flameLinkPlayerChain.flameLinkLevel")
    _require_exact_keys(level, set(_LEVEL_KEY_ORDER), "flameLinkPlayerChain.flameLinkLevel")
    base_level = level["baseLevel"]
    if not isinstance(base_level, int) or isinstance(base_level, bool):
        _fail("FLAME_LINK_BASE_LEVEL", "Base Flame Link level must be an integer")
    provenance = _require_string(
        level["baseLevelProvenance"],
        "flameLinkPlayerChain.flameLinkLevel.baseLevelProvenance",
    )
    if provenance not in BASE_LEVEL_PROVENANCES:
        _fail(
            "FLAME_LINK_BASE_LEVEL_PROVENANCE",
            "Base Flame Link level provenance is not recognized",
        )
    if provenance == "manual-benchmark-default":
        if base_level != DEFAULT_BASE_FLAME_LINK_LEVEL:
            _fail(
                "FLAME_LINK_BASE_LEVEL_PROVENANCE",
                "manual-benchmark-default requires baseLevel 21",
            )
    additions = _require_list(
        level["additionalLinkGemLevels"],
        "flameLinkPlayerChain.flameLinkLevel.additionalLinkGemLevels",
    )
    if len(additions) > MAX_ADDITIONAL_LEVEL_CONTRIBUTIONS:
        _fail(
            "ADDITIONAL_LINK_LEVEL_LIMIT",
            "Too many additional Link gem level contributions",
        )
    seen_level_ids: set[str] = set()
    for index, raw in enumerate(additions):
        context = (
            f"flameLinkPlayerChain.flameLinkLevel.additionalLinkGemLevels[{index}]"
        )
        entry = _require_object(raw, context)
        _require_exact_keys(entry, set(_ADDITIONAL_LEVEL_KEY_ORDER), context)
        contribution_id = _require_string(entry["contributionId"], f"{context}.contributionId")
        label = _require_string(entry["label"], f"{context}.label")
        assert contribution_id is not None and label is not None
        if not contribution_id or len(contribution_id) > MAX_CONTRIBUTION_ID_CHARACTERS:
            _fail("ADDITIONAL_LINK_LEVEL_ID", f"{context}.contributionId is empty or too long")
        if contribution_id in seen_level_ids:
            _fail(
                "ADDITIONAL_LINK_LEVEL_ID",
                f"Duplicate additional Link level contribution ID {contribution_id}",
            )
        seen_level_ids.add(contribution_id)
        _require_utf8(contribution_id, f"{context}.contributionId")
        if not label or len(label) > MAX_CONTRIBUTION_LABEL_CHARACTERS:
            _fail("ADDITIONAL_LINK_LEVEL_LABEL", f"{context}.label is empty or too long")
        _require_utf8(label, f"{context}.label")
        levels = entry["levels"]
        if not isinstance(levels, int) or isinstance(levels, bool):
            _fail("ADDITIONAL_LINK_LEVEL_VALUE", f"{context}.levels must be an integer")
        if contribution_id == CATALOG_EMPOWERED_BOND_ID:
            if levels != CATALOG_EMPOWERED_LEVELS:
                _fail(
                    "ADDITIONAL_LINK_LEVEL_CATALOG",
                    "empowered-bond catalog contribution must use levels 2",
                )
        if contribution_id in {CATALOG_POWERFUL_BOND_ID, CATALOG_INSPIRING_BOND_ID}:
            _fail(
                "ADDITIONAL_LINK_LEVEL_CATALOG",
                "Powerful/Inspiring Bond catalog IDs cannot be additional level contributions",
            )
        active_state = _require_string(entry["activeState"], f"{context}.activeState")
        if active_state not in ACTIVE_STATES:
            _fail("ADDITIONAL_LINK_LEVEL_STATE", f"{context}.activeState is not recognized")
        level_provenance = _validate_provenance(
            entry["provenanceKind"], f"{context}.provenanceKind"
        )
        level_raw = _validate_raw_source(entry["rawSourceText"], f"{context}.rawSourceText")
        level_recognition = _validate_recognition_source(
            entry["recognitionSource"], f"{context}.recognitionSource"
        )
        if level_provenance == "recognized-reviewed":
            has_raw = bool(level_raw.strip())
            has_digest = (
                level_recognition.get("kind") != "none"
                and level_recognition.get("digest") is not None
            )
            if not has_raw and not has_digest:
                _fail(
                    "FLAME_LINK_PROVENANCE_INVARIANT",
                    f"{context}: recognized-reviewed requires source identity",
                )

    life = _require_object(
        chain["luminaryMaximumLife"], "flameLinkPlayerChain.luminaryMaximumLife"
    )
    _require_exact_keys(life, set(_LIFE_KEY_ORDER), "flameLinkPlayerChain.luminaryMaximumLife")
    _validate_optional_nonnegative_decimal(
        life["reviewedLife"], "flameLinkPlayerChain.luminaryMaximumLife.reviewedLife"
    )
    life_provenance = _validate_provenance(
        life["provenanceKind"],
        "flameLinkPlayerChain.luminaryMaximumLife.provenanceKind",
    )
    life_review = _validate_review_state(
        life["reviewState"], "flameLinkPlayerChain.luminaryMaximumLife.reviewState"
    )
    life_raw = _validate_raw_source(
        life["rawSourceText"],
        "flameLinkPlayerChain.luminaryMaximumLife.rawSourceText",
    )
    life_recognition = _validate_recognition_source(
        life["recognitionSource"],
        "flameLinkPlayerChain.luminaryMaximumLife.recognitionSource",
    )
    _validate_reviewed_field_semantics(
        context="flameLinkPlayerChain.luminaryMaximumLife",
        provenance=life_provenance,
        review_state=life_review,
        value=life["reviewedLife"],
        raw_source_text=life_raw,
        recognition_source=life_recognition,
    )

    rounding = _require_string(
        chain["roundingPolicyId"], "flameLinkPlayerChain.roundingPolicyId"
    )
    if rounding != ROUNDING_POLICY_ID:
        _fail("FLAME_LINK_ROUNDING_POLICY", "Rounding policy ID must match the modelled v1 policy")
    formula = _require_string(
        chain["formulaVersionId"], "flameLinkPlayerChain.formulaVersionId"
    )
    if formula != FORMULA_VERSION_ID:
        _fail("FLAME_LINK_FORMULA_VERSION", "Formula version ID must match flame-link-player-chain-v1")


def validate_document(document_value: Any) -> None:
    document = _require_object(document_value, "build state")
    _require_exact_keys(document, _DOCUMENT_KEYS, "build state")
    if document["documentType"] != DOCUMENT_TYPE:
        _fail("DOCUMENT_TYPE", f"Document type must be {DOCUMENT_TYPE}")
    if document["schemaVersion"] != BUILD_STATE_SCHEMA_VERSION:
        _fail("SCHEMA_VERSION", "Build-state schema version must be 3.0.0")
    if document["applicationDataContractVersion"] != APPLICATION_DATA_CONTRACT_VERSION:
        _fail("APPLICATION_CONTRACT_VERSION", "Application data-contract version must be 3.0.0")
    if document["importerContractVersion"] != IMPORTER_CONTRACT_VERSION:
        _fail("IMPORTER_CONTRACT_VERSION", "Importer contract version must be 1.0.0")

    # Unchanged BUILD-002 structures retain exact runtime semantics via v2.
    v2_projection = {
        key: document[key]
        for key in v2_codec._DOCUMENT_KEY_ORDER
    }
    v2_projection["schemaVersion"] = V2_BUILD_STATE_SCHEMA_VERSION
    v2_projection["applicationDataContractVersion"] = (
        V2_APPLICATION_DATA_CONTRACT_VERSION
    )
    v2_codec.validate_document(v2_projection)
    _validate_flame_link_player_chain(document["flameLinkPlayerChain"])


def item_set_occurrence_ids(document: Mapping[str, Any]) -> tuple[str, ...]:
    validate_document(document)
    imported = document["importedResult"]
    if imported is None:
        return ()
    return tuple(value["occurrenceId"] for value in imported["document"]["itemSets"])


def _ordered_flame_link(chain: Mapping[str, Any]) -> dict[str, Any]:
    ordered = {key: chain[key] for key in _FLAME_LINK_KEY_ORDER}
    ordered["goldenGlory"] = {
        key: chain["goldenGlory"][key] for key in _GOLDEN_GLORY_KEY_ORDER
    }
    ordered["goldenGlory"]["recognitionSource"] = {
        key: chain["goldenGlory"]["recognitionSource"][key]
        for key in _RECOGNITION_SOURCE_KEY_ORDER
    }
    ordered["directLinkBuffEffect"] = {
        key: chain["directLinkBuffEffect"][key] for key in _DIRECT_KEY_ORDER
    }
    ordered["directLinkBuffEffect"]["recognitionSource"] = {
        key: chain["directLinkBuffEffect"]["recognitionSource"][key]
        for key in _RECOGNITION_SOURCE_KEY_ORDER
    }
    ordered["conditionalContributions"] = []
    for entry in chain["conditionalContributions"]:
        ordered_entry = {key: entry[key] for key in _CONDITIONAL_KEY_ORDER}
        ordered_entry["recognitionSource"] = {
            key: entry["recognitionSource"][key] for key in _RECOGNITION_SOURCE_KEY_ORDER
        }
        ordered["conditionalContributions"].append(ordered_entry)
    level = chain["flameLinkLevel"]
    ordered_level = {key: level[key] for key in _LEVEL_KEY_ORDER}
    ordered_level["additionalLinkGemLevels"] = []
    for entry in level["additionalLinkGemLevels"]:
        ordered_entry = {key: entry[key] for key in _ADDITIONAL_LEVEL_KEY_ORDER}
        ordered_entry["recognitionSource"] = {
            key: entry["recognitionSource"][key] for key in _RECOGNITION_SOURCE_KEY_ORDER
        }
        ordered_level["additionalLinkGemLevels"].append(ordered_entry)
    ordered["flameLinkLevel"] = ordered_level
    ordered["luminaryMaximumLife"] = {
        key: chain["luminaryMaximumLife"][key] for key in _LIFE_KEY_ORDER
    }
    ordered["luminaryMaximumLife"]["recognitionSource"] = {
        key: chain["luminaryMaximumLife"]["recognitionSource"][key]
        for key in _RECOGNITION_SOURCE_KEY_ORDER
    }
    return ordered


def _ordered_document(document: Mapping[str, Any]) -> dict[str, Any]:
    ordered = {key: document[key] for key in _DOCUMENT_KEY_ORDER}
    ordered["manualMercenaryEquipment"] = [
        {key: entry[key] for key in _MANUAL_ENTRY_KEY_ORDER}
        for entry in document["manualMercenaryEquipment"]
    ]
    ordered["copiedItemEntries"] = [
        {key: entry[key] for key in _COPIED_ENTRY_KEY_ORDER}
        for entry in document["copiedItemEntries"]
    ]
    enmity = document["enmityManualInput"]
    ordered_enmity = {key: enmity[key] for key in _ENMITY_KEY_ORDER}
    ordered_enmity["measurementContext"] = {
        key: enmity["measurementContext"][key]
        for key in MEASUREMENT_CONTEXT_FIELDS
    }
    if enmity["observedItemReference"] is not None:
        ordered_enmity["observedItemReference"] = {
            key: enmity["observedItemReference"][key]
            for key in _LOCATOR_KEY_ORDER
        }
    ordered["enmityManualInput"] = ordered_enmity
    ordered["flameLinkPlayerChain"] = _ordered_flame_link(document["flameLinkPlayerChain"])
    return ordered


def serialize(document: Mapping[str, Any]) -> bytes:
    validate_document(document)
    try:
        text = json.dumps(
            _ordered_document(document),
            ensure_ascii=True,
            allow_nan=False,
            indent=2,
            separators=(",", ": "),
            sort_keys=False,
        )
    except RecursionError:
        _fail("SERIALIZATION_NESTING", "Build state exceeds JSON nesting limits")
    except (TypeError, ValueError) as error:
        _fail("SERIALIZATION", f"Build state is not JSON serializable: {error}")
    return (text + "\n").encode("utf-8")


def _reject_constant(value: str) -> NoReturn:
    _fail("JSON_NONFINITE", f"JSON constant {value} is not permitted")


def _strict_object(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail("JSON_DUPLICATE_KEY", f"Duplicate JSON object key: {key}")
        result[key] = value
    return result


def _decode_json(data: bytes) -> dict[str, Any]:
    if not isinstance(data, bytes):
        _fail("OPEN_BYTES_REQUIRED", "Build-state input must be bytes")
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        _fail("OPEN_UTF8", f"Build-state file is not strict UTF-8: {error}")
    try:
        value = json.loads(
            text,
            parse_constant=_reject_constant,
            object_pairs_hook=_strict_object,
        )
    except BuildStateError:
        raise
    except json.JSONDecodeError as error:
        _fail(
            "OPEN_JSON",
            f"Build-state file is not strict JSON at line {error.lineno}, column {error.colno}",
        )
    except RecursionError:
        _fail("OPEN_JSON_NESTING", "Build-state JSON exceeds decoder nesting limits")
    except ValueError as error:
        _fail(
            "OPEN_JSON_NUMERIC_LIMIT",
            f"Build-state JSON exceeds the interpreter numeric resource limit: {error}",
        )
    return _require_object(value, "build state")


def migrate_v2_document(document_value: Any) -> dict[str, Any]:
    v2_codec.validate_document(document_value)
    document = _safe_deepcopy(
        document_value,
        code="MIGRATION_NESTING",
        message="Build-state migration exceeds safe copy nesting limits",
    )
    document["schemaVersion"] = BUILD_STATE_SCHEMA_VERSION
    document["applicationDataContractVersion"] = APPLICATION_DATA_CONTRACT_VERSION
    document["flameLinkPlayerChain"] = empty_flame_link_player_chain()
    validate_document(document)
    serialize(document)
    return document


def migrate_v1_document(document_value: Any) -> dict[str, Any]:
    migrated_v2 = v2_codec.migrate_v1_document(document_value)
    return migrate_v2_document(migrated_v2)


def decode(data: bytes) -> DecodedBuildState:
    parsed = _decode_json(data)
    schema_version = parsed.get("schemaVersion")
    if schema_version == BUILD_STATE_SCHEMA_VERSION:
        if isinstance(parsed.get("flameLinkPlayerChain"), dict):
            parsed["flameLinkPlayerChain"] = inject_recognition_source_defaults(
                parsed["flameLinkPlayerChain"]
            )
        validate_document(parsed)
        document = _safe_deepcopy(
            parsed,
            code="OPEN_STATE_NESTING",
            message="Build-state document exceeds safe copy nesting limits",
        )
        return DecodedBuildState(document, schema_version, False, serialize(document))
    if schema_version == V2_BUILD_STATE_SCHEMA_VERSION:
        v2_codec.validate_document(parsed)
        migrated = migrate_v2_document(parsed)
        return DecodedBuildState(
            _safe_deepcopy(
                migrated,
                code="OPEN_STATE_NESTING",
                message="Migrated build-state document exceeds safe copy nesting limits",
            ),
            schema_version,
            True,
            serialize(migrated),
        )
    if schema_version == LEGACY_BUILD_STATE_SCHEMA_VERSION:
        migrated = migrate_v1_document(parsed)
        return DecodedBuildState(
            _safe_deepcopy(
                migrated,
                code="OPEN_STATE_NESTING",
                message="Migrated build-state document exceeds safe copy nesting limits",
            ),
            schema_version,
            True,
            serialize(migrated),
        )
    _fail(
        "SCHEMA_VERSION",
        "Build-state schema version must be 1.0.0, 2.0.0, or 3.0.0; future versions are rejected",
    )


def deserialize(data: bytes) -> dict[str, Any]:
    return decode(data).document


def _bounded_read(path: Path) -> bytes:
    try:
        observed_size = path.stat().st_size
    except OSError as error:
        _fail("OPEN_FILE_ACCESS", f"Could not inspect build-state file: {error}")
    if observed_size > MAX_SAVED_STATE_FILE_BYTES:
        _fail(
            "OPEN_FILE_TOO_LARGE",
            f"Build-state file is {observed_size} bytes; the supported limit is {MAX_SAVED_STATE_FILE_BYTES} bytes",
        )
    try:
        with path.open("rb") as handle:
            data = handle.read(MAX_SAVED_STATE_FILE_BYTES + 1)
    except OSError as error:
        _fail("OPEN_FILE_ACCESS", f"Could not read build-state file: {error}")
    if len(data) > MAX_SAVED_STATE_FILE_BYTES:
        _fail(
            "OPEN_FILE_GREW",
            "Build-state file grew past the supported limit while it was being read",
        )
    return data


def load_file_result(path_value: str | os.PathLike[str]) -> tuple[DecodedBuildState, bytes]:
    data = _bounded_read(Path(path_value))
    return decode(data), data


def load_file(path_value: str | os.PathLike[str]) -> tuple[dict[str, Any], bytes]:
    result, data = load_file_result(path_value)
    return result.document, data


def atomic_save(
    path_value: str | os.PathLike[str],
    document: Mapping[str, Any],
    *,
    replace: Callable[[str | os.PathLike[str], str | os.PathLike[str]], Any] = os.replace,
) -> bytes:
    destination = Path(path_value)
    data = serialize(document)
    parent = destination.parent
    if not parent.is_dir():
        _fail("SAVE_PARENT", f"Save directory does not exist: {parent}")
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="xb",
            prefix=f".{destination.name}.",
            suffix=".tmp",
            dir=parent,
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        replace(temporary_path, destination)
    except BuildStateError:
        raise
    except OSError as error:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
        _fail("SAVE_FAILED", f"Atomic save failed: {error}")
    return data
