"""Canonical BUILD-001 build-state codec and atomic persistence.

The Draft 2020-12 schemas are build/test contracts. This module deliberately
implements only the runtime checks needed by BUILD-001 and does not attempt to
be a generic JSON Schema engine or a second full neutral-import schema.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import Any, NoReturn

from golden_glory_lab.pob_import import DEFAULT_IMPORT_LIMITS, deterministic_json_bytes

DOCUMENT_TYPE = "golden-glory-lab-build-state"
BUILD_STATE_SCHEMA_VERSION = "1.0.0"
APPLICATION_DATA_CONTRACT_VERSION = "1.0.0"
IMPORTER_CONTRACT_VERSION = "1.0.0"
MERCENARY_SOURCE_MODES = {
    "not-yet-selected",
    "mapped-item-set",
    "manual-equipment",
}
MANUAL_ENTRY_LIMITS = {
    "maxEntries": 64,
    "maxSlotLabelCharacters": 80,
    "maxRawTextCharacters": 100_000,
    "maxNoteCharacters": 10_000,
}
MAX_USER_NOTES_CHARACTERS = 100_000

# Saved files retain the complete neutral result. This support envelope is
# derived from current producer limits rather than an arbitrary round number.
# Eight conservative XML copies cover the envelope input, decoded XML, source
# tree, item character projection, ordered child material, classified unknown
# material, retained report material, and metadata/attribute projection. The
# bound then adds the separately retained share-code envelope, structural
# indentation across every permitted element/depth pair, every maximum
# manual/user string at the twelve-byte maximum for one non-BMP Python
# character, and 1 MiB for fixed contract/report metadata. Externally authored
# files above this envelope are unsupported even if they resemble the schema.
_JSON_ESCAPE_BYTES_PER_SOURCE_BYTE = 6
_JSON_ESCAPE_BYTES_PER_PYTHON_CHARACTER = 12
_NEUTRAL_XML_RETENTION_COPIES = 8
_STRUCTURAL_BYTES_PER_ELEMENT_DEPTH = 32
_FIXED_CONTRACT_AND_REPORT_BYTES = 1_048_576
_MAX_MANUAL_AND_NOTE_CHARACTERS = (
    MANUAL_ENTRY_LIMITS["maxEntries"]
    * (
        80  # entryId runtime maximum
        + MANUAL_ENTRY_LIMITS["maxSlotLabelCharacters"]
        + MANUAL_ENTRY_LIMITS["maxRawTextCharacters"]
        + MANUAL_ENTRY_LIMITS["maxNoteCharacters"]
    )
    + MAX_USER_NOTES_CHARACTERS
)
MAX_SAVED_STATE_FILE_BYTES = (
    DEFAULT_IMPORT_LIMITS.maxRawXmlBytes
    * _NEUTRAL_XML_RETENTION_COPIES
    * _JSON_ESCAPE_BYTES_PER_SOURCE_BYTE
    + DEFAULT_IMPORT_LIMITS.maxShareCodeCharacters
    * _JSON_ESCAPE_BYTES_PER_SOURCE_BYTE
    + DEFAULT_IMPORT_LIMITS.maxXmlElements
    * DEFAULT_IMPORT_LIMITS.maxXmlDepth
    * _STRUCTURAL_BYTES_PER_ELEMENT_DEPTH
    + _MAX_MANUAL_AND_NOTE_CHARACTERS * _JSON_ESCAPE_BYTES_PER_PYTHON_CHARACTER
    + _FIXED_CONTRACT_AND_REPORT_BYTES
)


_DOCUMENT_KEYS = {
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
    "userNotes",
}
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
    "userNotes",
)

_MANUAL_ENTRY_KEYS = {
    "entryId",
    "slotLabel",
    "rawText",
    "reviewState",
    "note",
}
_MANUAL_ENTRY_KEY_ORDER = (
    "entryId",
    "slotLabel",
    "rawText",
    "reviewState",
    "note",
)



class BuildStateError(ValueError):
    """Stable expected failure at the build-state boundary."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _fail(code: str, message: str) -> NoReturn:
    raise BuildStateError(code, message)


def empty_document() -> dict[str, Any]:
    """Return a new canonical empty document with no session fields."""

    return {
        "documentType": DOCUMENT_TYPE,
        "schemaVersion": BUILD_STATE_SCHEMA_VERSION,
        "applicationDataContractVersion": APPLICATION_DATA_CONTRACT_VERSION,
        "importerContractVersion": IMPORTER_CONTRACT_VERSION,
        "importedResult": None,
        "importedResultSha256": None,
        "playerItemSetOccurrenceId": None,
        "mercenarySourceMode": "not-yet-selected",
        "mercenaryItemSetOccurrenceId": None,
        "manualMercenaryEquipment": [],
        "userNotes": "",
    }


def imported_result_digest(imported_result: Mapping[str, Any]) -> str:
    """Hash the adopted importer's canonical bytes, not the enclosing state."""

    if not isinstance(imported_result, dict):
        _fail("IMPORTED_RESULT_TYPE", "Imported result must be an object")
    try:
        encoded = deterministic_json_bytes(imported_result)
    except RecursionError:
        _fail(
            "IMPORTED_RESULT_NESTING",
            "Imported result exceeds deterministic serialization nesting limits",
        )
    except (TypeError, ValueError) as error:
        _fail(
            "IMPORTED_RESULT_SERIALIZATION",
            f"Imported result cannot be deterministically serialized: {error}",
        )
    return hashlib.sha256(encoded).hexdigest()


def _require_object(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail("SHAPE_TYPE", f"{context} must be an object")
    return value


def _require_list(value: Any, context: str) -> list[Any]:
    if not isinstance(value, list):
        _fail("SHAPE_TYPE", f"{context} must be an array")
    return value


def _require_string(value: Any, context: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str):
        _fail("SHAPE_TYPE", f"{context} must be a string")
    return value


def _require_nonempty_string(value: Any, context: str) -> str:
    result = _require_string(value, context)
    assert result is not None
    if not result:
        _fail("NEUTRAL_RESULT_SHAPE", f"{context} must be nonempty")
    return result


def _require_nonnegative_integer(value: Any, context: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        _fail("NEUTRAL_RESULT_SHAPE", f"{context} must be a nonnegative integer")
    return value


def _require_integer_or_none(value: Any, context: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        _fail("SHAPE_TYPE", f"{context} must be an integer or null")
    return value


def _require_string_list(value: Any, context: str) -> None:
    entries = _require_list(value, context)
    if not all(isinstance(entry, str) for entry in entries):
        _fail("SHAPE_TYPE", f"{context} must contain only strings")


def _require_exact_keys(
    value: Mapping[str, Any], expected: set[str], context: str
) -> None:
    actual = set(value)
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if missing:
        _fail("SHAPE_MISSING_FIELD", f"{context} is missing: {', '.join(missing)}")
    if unknown:
        _fail("SHAPE_UNKNOWN_FIELD", f"{context} has unknown fields: {', '.join(unknown)}")


def _validate_raw_state(value: Any, context: str) -> None:
    raw = _require_object(value, context)
    if set(raw) != {"state", "value"}:
        _fail("NEUTRAL_RESULT_SHAPE", f"{context} must contain state and value")
    state = _require_string(raw["state"], f"{context}.state")
    if state not in {"missing", "empty", "present"}:
        _fail("NEUTRAL_RESULT_SHAPE", f"{context}.state is not recognized")
    observed = raw["value"]
    if state == "missing" and observed is not None:
        _fail("NEUTRAL_RESULT_SHAPE", f"{context}.value must be null when missing")
    if state == "empty" and observed != "":
        _fail("NEUTRAL_RESULT_SHAPE", f"{context}.value must be empty")
    if state == "present" and (not isinstance(observed, str) or not observed):
        _fail("NEUTRAL_RESULT_SHAPE", f"{context}.value must be a non-empty string")


def _validate_boolean_value(value: Any, context: str) -> None:
    boolean_value = _require_object(value, context)
    if set(boolean_value) != {"raw", "parsed"}:
        _fail("NEUTRAL_RESULT_SHAPE", f"{context} must contain raw and parsed")
    _validate_raw_state(boolean_value["raw"], f"{context}.raw")
    if boolean_value["parsed"] is not None and not isinstance(
        boolean_value["parsed"], bool
    ):
        _fail("NEUTRAL_RESULT_SHAPE", f"{context}.parsed must be boolean or null")


def _validate_resolution(
    value: Any, context: str, *, equipment: bool = False
) -> None:
    resolution = _require_object(value, context)
    if set(resolution) != {"state", "candidateOccurrences"}:
        _fail(
            "NEUTRAL_RESULT_SHAPE",
            f"{context} must contain state and candidateOccurrences",
        )
    state = _require_string(resolution["state"], f"{context}.state")
    if state not in {
        "missing",
        "malformed",
        "empty-reference",
        "unresolved",
        "ambiguous",
        "resolved",
    }:
        _fail("NEUTRAL_RESULT_SHAPE", f"{context}.state is not recognized")
    candidates = _require_list(
        resolution["candidateOccurrences"], f"{context}.candidateOccurrences"
    )
    if not all(isinstance(candidate, str) for candidate in candidates):
        _fail(
            "NEUTRAL_RESULT_SHAPE",
            f"{context}.candidateOccurrences must contain only strings",
        )
    if equipment and state == "missing":
        _fail("NEUTRAL_RESULT_SHAPE", f"{context}.state cannot be missing")
    expected_zero = {"missing", "malformed", "empty-reference", "unresolved"}
    if state in expected_zero and candidates:
        _fail("NEUTRAL_RESULT_SHAPE", f"{context} requires zero candidates")
    if state == "resolved" and len(candidates) != 1:
        _fail("NEUTRAL_RESULT_SHAPE", f"{context} requires exactly one candidate")
    if state == "ambiguous" and len(candidates) < 2:
        _fail("NEUTRAL_RESULT_SHAPE", f"{context} requires at least two candidates")


def _validate_assignment(value: Any, context: str) -> str:
    assignment = _require_object(value, context)
    consumed = {
        "occurrenceId",
        "sourceOccurrenceIndex",
        "sourcePath",
        "originalSlotName",
        "rawItemReference",
        "parsedItemId",
        "active",
        "resolution",
        "derivedAbyssalParent",
        "warnings",
    }
    missing = sorted(consumed - set(assignment))
    if missing:
        _fail(
            "NEUTRAL_RESULT_SHAPE",
            f"{context} is missing consumed fields: {', '.join(missing)}",
        )
    occurrence_id = _require_nonempty_string(
        assignment["occurrenceId"], f"{context}.occurrenceId"
    )
    _require_nonnegative_integer(
        assignment["sourceOccurrenceIndex"], f"{context}.sourceOccurrenceIndex"
    )
    _require_string(assignment["sourcePath"], f"{context}.sourcePath")
    _validate_raw_state(assignment["originalSlotName"], f"{context}.originalSlotName")
    _validate_raw_state(assignment["rawItemReference"], f"{context}.rawItemReference")
    _require_integer_or_none(assignment["parsedItemId"], f"{context}.parsedItemId")
    _validate_boolean_value(assignment["active"], f"{context}.active")
    _validate_resolution(
        assignment["resolution"], f"{context}.resolution", equipment=True
    )
    parent = assignment["derivedAbyssalParent"]
    if parent is not None and not isinstance(parent, dict):
        _fail("NEUTRAL_RESULT_SHAPE", f"{context}.derivedAbyssalParent is invalid")
    _require_string_list(assignment["warnings"], f"{context}.warnings")
    return occurrence_id


def _validate_imported_result(value: Any) -> set[str]:
    result = _require_object(value, "importedResult")
    for field in ("contractVersion", "status", "document", "report"):
        if field not in result:
            _fail("NEUTRAL_RESULT_SHAPE", f"importedResult is missing {field}")
    if result["contractVersion"] != IMPORTER_CONTRACT_VERSION:
        _fail(
            "IMPORTER_CONTRACT_VERSION",
            "Embedded importer contract must be 1.0.0",
        )
    if result["status"] != "success":
        _fail(
            "IMPORTED_RESULT_NOT_SUCCESS",
            "Only a successful imported result is canonical build content",
        )
    document = _require_object(result["document"], "importedResult.document")
    for field in ("itemSets", "items"):
        if field not in document:
            _fail(
                "NEUTRAL_RESULT_SHAPE",
                f"importedResult.document is missing consumed field {field}",
            )

    item_occurrences: set[str] = set()
    for index, value_item in enumerate(
        _require_list(document["items"], "importedResult.document.items")
    ):
        context = f"importedResult.document.items[{index}]"
        item = _require_object(value_item, context)
        for field in (
            "occurrenceId",
            "sourceOccurrenceIndex",
            "sourcePath",
            "rawId",
            "xmlCharacterValue",
            "orderedChildMaterial",
            "usage",
            "warnings",
        ):
            if field not in item:
                _fail("NEUTRAL_RESULT_SHAPE", f"{context} is missing {field}")
        occurrence = _require_nonempty_string(
            item["occurrenceId"], f"{context}.occurrenceId"
        )
        if occurrence in item_occurrences:
            _fail("NEUTRAL_RESULT_SHAPE", f"Duplicate item occurrence {occurrence}")
        item_occurrences.add(occurrence)
        _require_nonnegative_integer(
            item["sourceOccurrenceIndex"], f"{context}.sourceOccurrenceIndex"
        )
        _require_string(item["sourcePath"], f"{context}.sourcePath")
        _validate_raw_state(item["rawId"], f"{context}.rawId")
        _require_string(item["xmlCharacterValue"], f"{context}.xmlCharacterValue")
        _require_list(item["orderedChildMaterial"], f"{context}.orderedChildMaterial")
        usage = _require_object(item["usage"], f"{context}.usage")
        if "state" not in usage:
            _fail("NEUTRAL_RESULT_SHAPE", f"{context}.usage is missing state")
        usage_state = _require_string(usage["state"], f"{context}.usage.state")
        if usage_state not in {"unused", "referenced"}:
            _fail("NEUTRAL_RESULT_SHAPE", f"{context}.usage.state is not recognized")
        _require_string_list(item["warnings"], f"{context}.warnings")

    occurrences: set[str] = set()
    for index, value_set in enumerate(
        _require_list(document["itemSets"], "importedResult.document.itemSets")
    ):
        context = f"importedResult.document.itemSets[{index}]"
        item_set = _require_object(value_set, context)
        for field in (
            "occurrenceId",
            "sourceOccurrenceIndex",
            "sourcePath",
            "rawId",
            "title",
            "useSecondWeaponSet",
            "assignments",
            "warnings",
        ):
            if field not in item_set:
                _fail("NEUTRAL_RESULT_SHAPE", f"{context} is missing {field}")
        occurrence = _require_nonempty_string(
            item_set["occurrenceId"], f"{context}.occurrenceId"
        )
        if occurrence in occurrences:
            _fail("NEUTRAL_RESULT_SHAPE", f"Duplicate item-set occurrence {occurrence}")
        occurrences.add(occurrence)
        _require_nonnegative_integer(
            item_set["sourceOccurrenceIndex"], f"{context}.sourceOccurrenceIndex"
        )
        _require_string(item_set["sourcePath"], f"{context}.sourcePath")
        _validate_raw_state(item_set["rawId"], f"{context}.rawId")
        _validate_raw_state(item_set["title"], f"{context}.title")
        _validate_boolean_value(
            item_set["useSecondWeaponSet"], f"{context}.useSecondWeaponSet"
        )
        assignment_occurrences: set[str] = set()
        for assignment_index, assignment in enumerate(
            _require_list(item_set["assignments"], f"{context}.assignments")
        ):
            assignment_occurrence = _validate_assignment(
                assignment, f"{context}.assignments[{assignment_index}]"
            )
            if assignment_occurrence in assignment_occurrences:
                _fail(
                    "NEUTRAL_RESULT_SHAPE",
                    f"Duplicate assignment occurrence {assignment_occurrence} in {context}",
                )
            assignment_occurrences.add(assignment_occurrence)
        _require_string_list(item_set["warnings"], f"{context}.warnings")

    categories = {
        "recognized",
        "ignored as irrelevant",
        "unrecognized",
        "ambiguous",
        "manually required",
        "malformed",
    }
    stages = {
        "envelope",
        "decompression",
        "xml",
        "semantic",
        "resolution",
        "mapping",
        "reporting",
    }
    report_ids: set[str] = set()
    for index, value_entry in enumerate(_require_list(result["report"], "report")):
        context = f"importedResult.report[{index}]"
        entry = _require_object(value_entry, context)
        for field in (
            "reportId",
            "code",
            "category",
            "stage",
            "location",
            "occurrenceId",
            "sourcePointer",
            "retainedMaterial",
            "explanation",
            "candidateTargets",
        ):
            if field not in entry:
                _fail("NEUTRAL_RESULT_SHAPE", f"{context} is missing {field}")
        report_id = _require_nonempty_string(entry["reportId"], f"{context}.reportId")
        if report_id in report_ids:
            _fail("NEUTRAL_RESULT_SHAPE", f"Duplicate report ID {report_id}")
        report_ids.add(report_id)
        _require_string(entry["code"], f"{context}.code")
        category = _require_string(entry["category"], f"{context}.category")
        if category not in categories:
            _fail("NEUTRAL_RESULT_SHAPE", f"{context}.category is not recognized")
        stage = _require_string(entry["stage"], f"{context}.stage")
        if stage not in stages:
            _fail("NEUTRAL_RESULT_SHAPE", f"{context}.stage is not recognized")
        _require_string(entry["location"], f"{context}.location")
        _require_string(entry["occurrenceId"], f"{context}.occurrenceId", nullable=True)
        _require_string(entry["sourcePointer"], f"{context}.sourcePointer")
        _require_string(entry["explanation"], f"{context}.explanation")
        _require_string_list(entry["candidateTargets"], f"{context}.candidateTargets")
    return occurrences


def _validate_manual_entries(entries_value: Any) -> None:
    entries = _require_list(entries_value, "manualMercenaryEquipment")
    if len(entries) > MANUAL_ENTRY_LIMITS["maxEntries"]:
        _fail("MANUAL_ENTRY_LIMIT", "Too many manual Mercenary equipment entries")
    seen: set[str] = set()
    for index, value in enumerate(entries):
        context = f"manualMercenaryEquipment[{index}]"
        entry = _require_object(value, context)
        _require_exact_keys(entry, _MANUAL_ENTRY_KEYS, context)
        entry_id = _require_string(entry["entryId"], f"{context}.entryId")
        assert entry_id is not None
        if not entry_id or len(entry_id) > 80:
            _fail("MANUAL_ENTRY_ID", f"{context}.entryId is empty or too long")
        if entry_id in seen:
            _fail("MANUAL_ENTRY_ID", f"Duplicate manual entry ID {entry_id}")
        seen.add(entry_id)
        slot = _require_string(entry["slotLabel"], f"{context}.slotLabel")
        raw = _require_string(entry["rawText"], f"{context}.rawText")
        note = _require_string(entry["note"], f"{context}.note")
        assert slot is not None and raw is not None and note is not None
        if not slot or len(slot) > MANUAL_ENTRY_LIMITS["maxSlotLabelCharacters"]:
            _fail("MANUAL_SLOT_LIMIT", f"{context}.slotLabel is empty or too long")
        if not raw or len(raw) > MANUAL_ENTRY_LIMITS["maxRawTextCharacters"]:
            _fail("MANUAL_TEXT_LIMIT", f"{context}.rawText is empty or too long")
        if len(note) > MANUAL_ENTRY_LIMITS["maxNoteCharacters"]:
            _fail("MANUAL_NOTE_LIMIT", f"{context}.note is too long")
        if entry["reviewState"] != "unparsed-manual":
            _fail(
                "MANUAL_REVIEW_STATE",
                f"{context}.reviewState must be unparsed-manual",
            )


def validate_document(document_value: Any) -> None:
    """Validate the canonical shape and BUILD-001 semantic references."""

    document = _require_object(document_value, "build state")
    _require_exact_keys(document, _DOCUMENT_KEYS, "build state")
    if document["documentType"] != DOCUMENT_TYPE:
        _fail("DOCUMENT_TYPE", f"Document type must be {DOCUMENT_TYPE}")
    if document["schemaVersion"] != BUILD_STATE_SCHEMA_VERSION:
        _fail("SCHEMA_VERSION", "Build-state schema version must be 1.0.0")
    if document["applicationDataContractVersion"] != APPLICATION_DATA_CONTRACT_VERSION:
        _fail(
            "APPLICATION_CONTRACT_VERSION",
            "Application data-contract version must be 1.0.0",
        )
    if document["importerContractVersion"] != IMPORTER_CONTRACT_VERSION:
        _fail("IMPORTER_CONTRACT_VERSION", "Importer contract version must be 1.0.0")

    imported = document["importedResult"]
    digest = document["importedResultSha256"]
    if imported is None:
        if digest is not None:
            _fail("IMPORTED_RESULT_DIGEST", "Digest must be null when import is missing")
        occurrences: set[str] = set()
    else:
        occurrences = _validate_imported_result(imported)
        digest_text = _require_string(digest, "importedResultSha256")
        if digest_text != imported_result_digest(imported):
            _fail("IMPORTED_RESULT_DIGEST", "Embedded importer result digest mismatch")

    player = _require_string(
        document["playerItemSetOccurrenceId"],
        "playerItemSetOccurrenceId",
        nullable=True,
    )
    mercenary = _require_string(
        document["mercenaryItemSetOccurrenceId"],
        "mercenaryItemSetOccurrenceId",
        nullable=True,
    )
    if player is not None and player not in occurrences:
        _fail("DANGLING_PLAYER_MAPPING", "Player mapping does not reference an item set")
    if mercenary is not None and mercenary not in occurrences:
        _fail(
            "DANGLING_MERCENARY_MAPPING",
            "Mercenary mapping does not reference an item set",
        )
    if player is not None and player == mercenary:
        _fail(
            "SAME_OCCURRENCE_MAPPING",
            "Player and Mercenary must use different item-set occurrences",
        )

    mode = _require_string(document["mercenarySourceMode"], "mercenarySourceMode")
    if mode not in MERCENARY_SOURCE_MODES:
        _fail("MERCENARY_SOURCE_MODE", "Mercenary source mode is not recognized")
    if mode == "mapped-item-set" and mercenary is None:
        _fail(
            "MERCENARY_MAPPING_REQUIRED",
            "Mapped-item-set mode requires an explicit Mercenary occurrence",
        )
    if mode != "mapped-item-set" and mercenary is not None:
        _fail(
            "INACTIVE_MERCENARY_MAPPING",
            "Only mapped-item-set mode may have an active Mercenary occurrence",
        )

    _validate_manual_entries(document["manualMercenaryEquipment"])
    notes = _require_string(document["userNotes"], "userNotes")
    assert notes is not None
    if len(notes) > MAX_USER_NOTES_CHARACTERS:
        _fail("USER_NOTES_LIMIT", "User notes exceed the configured limit")


def item_set_occurrence_ids(document: Mapping[str, Any]) -> tuple[str, ...]:
    validate_document(document)
    imported = document["importedResult"]
    if imported is None:
        return ()
    return tuple(
        item_set["occurrenceId"]
        for item_set in imported["document"]["itemSets"]
    )


def _ordered_document(document: Mapping[str, Any]) -> dict[str, Any]:
    ordered = {key: document[key] for key in _DOCUMENT_KEY_ORDER}
    ordered["manualMercenaryEquipment"] = [
        {key: entry[key] for key in _MANUAL_ENTRY_KEY_ORDER}
        for entry in document["manualMercenaryEquipment"]
    ]
    return ordered


def serialize(document: Mapping[str, Any]) -> bytes:
    """Return deterministic strict UTF-8 JSON bytes with a terminal newline."""

    validate_document(document)
    try:
        ordered = _ordered_document(document)
        text = json.dumps(
            ordered,
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


def deserialize(data: bytes) -> dict[str, Any]:
    """Decode strict UTF-8 and strict JSON, then validate canonical content."""

    if not isinstance(data, bytes):
        _fail("OPEN_BYTES_REQUIRED", "Build-state input must be bytes")
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        _fail("OPEN_UTF8", f"Build-state file is not strict UTF-8: {error}")
    try:
        document = json.loads(
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
    validate_document(document)
    try:
        return copy.deepcopy(document)
    except RecursionError:
        _fail("OPEN_JSON_NESTING", "Build-state JSON exceeds copy nesting limits")


def load_file(path_value: str | os.PathLike[str]) -> tuple[dict[str, Any], bytes]:
    path = Path(path_value)
    try:
        observed_size = path.stat().st_size
    except OSError as error:
        _fail("OPEN_FILE_ACCESS", f"Could not inspect build-state file: {error}")
    if observed_size > MAX_SAVED_STATE_FILE_BYTES:
        _fail(
            "OPEN_FILE_TOO_LARGE",
            f"Build-state file is {observed_size} bytes; the supported limit is "
            f"{MAX_SAVED_STATE_FILE_BYTES} bytes",
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
    return deserialize(data), data


def atomic_save(
    path_value: str | os.PathLike[str],
    document: Mapping[str, Any],
    *,
    replace: Callable[[str | os.PathLike[str], str | os.PathLike[str]], Any] = os.replace,
) -> bytes:
    """Serialize completely, then replace the destination atomically."""

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
