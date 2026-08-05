"""Canonical BUILD-002 state, strict v1 migration, and atomic persistence."""

from __future__ import annotations

import copy
import json
import os
import tempfile
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NoReturn

from golden_glory_lab.domain import DECIMAL_DIGIT_LIMIT, DecimalInputError
from golden_glory_lab.domain import parse_decimal_text
from golden_glory_lab.item_review import COPIED_ITEM_LIMITS, ReviewSourceLocator

from . import codec as legacy_codec

DOCUMENT_TYPE = legacy_codec.DOCUMENT_TYPE
BUILD_STATE_SCHEMA_VERSION = "2.0.0"
APPLICATION_DATA_CONTRACT_VERSION = "2.0.0"
IMPORTER_CONTRACT_VERSION = legacy_codec.IMPORTER_CONTRACT_VERSION
LEGACY_BUILD_STATE_SCHEMA_VERSION = legacy_codec.BUILD_STATE_SCHEMA_VERSION
LEGACY_APPLICATION_DATA_CONTRACT_VERSION = (
    legacy_codec.APPLICATION_DATA_CONTRACT_VERSION
)
MERCENARY_SOURCE_MODES = legacy_codec.MERCENARY_SOURCE_MODES
MANUAL_ENTRY_LIMITS = legacy_codec.MANUAL_ENTRY_LIMITS
MAX_USER_NOTES_CHARACTERS = legacy_codec.MAX_USER_NOTES_CHARACTERS
BuildStateError = legacy_codec.BuildStateError

COPIED_ROLES = {"player", "mercenary", "unassigned"}
ENMITY_EQUIPPED_STATES = {"equipped", "not-equipped", "unknown"}
EQUIPMENT_INCLUSION_STATES = {"unrecorded", "included", "excluded", "unknown"}
TARGET_VERSION_ACKNOWLEDGEMENTS = {
    "confirmed-3.29.1",
    "other-version",
    "unknown",
}
MEASUREMENT_CONTEXT_FIELDS = (
    "mercenaryIdentityLevel",
    "activeStateSelection",
    "zoneOrUiContext",
    "relevantEffectsConditions",
    "equipmentStateDescription",
    "captureTimingDescription",
)
MAX_CONTEXT_FIELD_CHARACTERS = 10_000

# BUILD-001's producer-derived envelope remains intact. BUILD-002 adds every
# maximum copied-entry string and every maximum Enmity user-authored string at
# the existing conservative twelve JSON bytes per Python character. Fixed v2
# keys fit within the retained 1 MiB legacy fixed-contract allowance.
_JSON_ESCAPE_BYTES_PER_PYTHON_CHARACTER = 12
_MAX_COPIED_CANONICAL_CHARACTERS = COPIED_ITEM_LIMITS["maxEntries"] * (
    COPIED_ITEM_LIMITS["maxEntryIdCharacters"]
    + COPIED_ITEM_LIMITS["maxRawTextCharacters"]
    + len("unassigned")
    + COPIED_ITEM_LIMITS["maxSlotLabelCharacters"]
    + COPIED_ITEM_LIMITS["maxUserLabelCharacters"]
    + COPIED_ITEM_LIMITS["maxNoteCharacters"]
)
_MAX_DECIMAL_LEXEME_CHARACTERS = DECIMAL_DIGIT_LIMIT + 2  # optional sign and dot
_MAX_ENMITY_CANONICAL_CHARACTERS = (
    3 * _MAX_DECIMAL_LEXEME_CHARACTERS
    + len("not-equipped")
    + len("unrecorded")
    + len("confirmed-3.29.1")
    + len(MEASUREMENT_CONTEXT_FIELDS)
    * MAX_CONTEXT_FIELD_CHARACTERS
    + len("manual-entry")
    + COPIED_ITEM_LIMITS["maxEntryIdCharacters"]
)
MAX_SAVED_STATE_FILE_BYTES = (
    legacy_codec.MAX_SAVED_STATE_FILE_BYTES
    + _MAX_COPIED_CANONICAL_CHARACTERS
    * _JSON_ESCAPE_BYTES_PER_PYTHON_CHARACTER
    + _MAX_ENMITY_CANONICAL_CHARACTERS
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
    "userNotes",
)
_DOCUMENT_KEYS = set(_DOCUMENT_KEY_ORDER)
_MANUAL_ENTRY_KEY_ORDER = legacy_codec._MANUAL_ENTRY_KEY_ORDER
_COPIED_ENTRY_KEY_ORDER = (
    "entryId",
    "rawText",
    "role",
    "slotLabel",
    "userLabel",
    "note",
)
_COPIED_ENTRY_KEYS = set(_COPIED_ENTRY_KEY_ORDER)
_ENMITY_KEY_ORDER = (
    "finalUncappedFireResistance",
    "maximumFireResistance",
    "equippedState",
    "equipmentInclusionState",
    "measurementContext",
    "targetGameVersionAcknowledgement",
    "observedItemReference",
    "target",
)
_ENMITY_KEYS = set(_ENMITY_KEY_ORDER)
_LOCATOR_KEY_ORDER = ("provenanceKind", "sourceId")


@dataclass(frozen=True, slots=True)
class DecodedBuildState:
    document: dict[str, Any]
    sourceSchemaVersion: str
    migrated: bool
    canonicalV2Bytes: bytes


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


def empty_measurement_context() -> dict[str, str]:
    return {field: "" for field in MEASUREMENT_CONTEXT_FIELDS}


def empty_enmity_manual_input() -> dict[str, Any]:
    return {
        "finalUncappedFireResistance": None,
        "maximumFireResistance": None,
        "equippedState": "unknown",
        "equipmentInclusionState": "unrecorded",
        "measurementContext": empty_measurement_context(),
        "targetGameVersionAcknowledgement": "unknown",
        "observedItemReference": None,
        "target": None,
    }


def empty_document() -> dict[str, Any]:
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
        "copiedItemEntries": [],
        "enmityManualInput": empty_enmity_manual_input(),
        "userNotes": "",
    }


def imported_result_digest(imported_result: Mapping[str, Any]) -> str:
    return legacy_codec.imported_result_digest(imported_result)


def _validate_copied_entries(entries_value: Any) -> set[str]:
    entries = _require_list(entries_value, "copiedItemEntries")
    if len(entries) > COPIED_ITEM_LIMITS["maxEntries"]:
        _fail("COPIED_ENTRY_LIMIT", "Too many copied-item entries")
    seen: set[str] = set()
    for index, raw_entry in enumerate(entries):
        context = f"copiedItemEntries[{index}]"
        entry = _require_object(raw_entry, context)
        _require_exact_keys(entry, _COPIED_ENTRY_KEYS, context)
        entry_id = _require_string(entry["entryId"], f"{context}.entryId")
        raw_text = _require_string(entry["rawText"], f"{context}.rawText")
        role = _require_string(entry["role"], f"{context}.role")
        slot = _require_string(entry["slotLabel"], f"{context}.slotLabel")
        label = _require_string(entry["userLabel"], f"{context}.userLabel")
        note = _require_string(entry["note"], f"{context}.note")
        assert None not in (entry_id, raw_text, role, slot, label, note)
        if (
            not entry_id
            or len(entry_id) > COPIED_ITEM_LIMITS["maxEntryIdCharacters"]
        ):
            _fail("COPIED_ENTRY_ID", f"{context}.entryId is empty or too long")
        if entry_id in seen:
            _fail("COPIED_ENTRY_ID", f"Duplicate copied-item entry ID {entry_id}")
        seen.add(entry_id)
        if not raw_text or len(raw_text) > COPIED_ITEM_LIMITS["maxRawTextCharacters"]:
            _fail("COPIED_TEXT_LIMIT", f"{context}.rawText is empty or too long")
        _require_utf8(raw_text, f"{context}.rawText")
        if role not in COPIED_ROLES:
            _fail("COPIED_ROLE", f"{context}.role is not recognized")
        if len(slot) > COPIED_ITEM_LIMITS["maxSlotLabelCharacters"]:
            _fail("COPIED_SLOT_LIMIT", f"{context}.slotLabel is too long")
        if len(label) > COPIED_ITEM_LIMITS["maxUserLabelCharacters"]:
            _fail("COPIED_LABEL_LIMIT", f"{context}.userLabel is too long")
        if len(note) > COPIED_ITEM_LIMITS["maxNoteCharacters"]:
            _fail("COPIED_NOTE_LIMIT", f"{context}.note is too long")
        for field, value in (("slotLabel", slot), ("userLabel", label), ("note", note)):
            _require_utf8(value, f"{context}.{field}")
    return seen


def _validate_optional_decimal(value: Any, context: str) -> None:
    if value is None:
        return
    text = _require_string(value, context)
    assert text is not None
    try:
        parse_decimal_text(text)
    except DecimalInputError as error:
        _fail(error.code, f"{context}: {error.message}")


def _validate_enmity_input(value: Any) -> ReviewSourceLocator | None:
    enmity = _require_object(value, "enmityManualInput")
    _require_exact_keys(enmity, _ENMITY_KEYS, "enmityManualInput")
    _validate_optional_decimal(
        enmity["finalUncappedFireResistance"],
        "enmityManualInput.finalUncappedFireResistance",
    )
    _validate_optional_decimal(
        enmity["maximumFireResistance"],
        "enmityManualInput.maximumFireResistance",
    )
    _validate_optional_decimal(enmity["target"], "enmityManualInput.target")
    equipped = _require_string(enmity["equippedState"], "enmityManualInput.equippedState")
    if equipped not in ENMITY_EQUIPPED_STATES:
        _fail("ENMITY_EQUIPPED_STATE", "Enmity equipped state is not recognized")
    inclusion = _require_string(
        enmity["equipmentInclusionState"],
        "enmityManualInput.equipmentInclusionState",
    )
    if inclusion not in EQUIPMENT_INCLUSION_STATES:
        _fail("EQUIPMENT_INCLUSION_STATE", "Equipment inclusion state is not recognized")
    acknowledgement = _require_string(
        enmity["targetGameVersionAcknowledgement"],
        "enmityManualInput.targetGameVersionAcknowledgement",
    )
    if acknowledgement not in TARGET_VERSION_ACKNOWLEDGEMENTS:
        _fail("TARGET_VERSION_ACKNOWLEDGEMENT", "Target version acknowledgement is not recognized")
    context = _require_object(
        enmity["measurementContext"], "enmityManualInput.measurementContext"
    )
    _require_exact_keys(
        context,
        set(MEASUREMENT_CONTEXT_FIELDS),
        "enmityManualInput.measurementContext",
    )
    for field in MEASUREMENT_CONTEXT_FIELDS:
        observed = _require_string(
            context[field], f"enmityManualInput.measurementContext.{field}"
        )
        assert observed is not None
        if len(observed) > MAX_CONTEXT_FIELD_CHARACTERS:
            _fail("MEASUREMENT_CONTEXT_LIMIT", f"Measurement context field {field} is too long")
        _require_utf8(observed, f"measurementContext.{field}")
    locator_value = enmity["observedItemReference"]
    if locator_value is None:
        return None
    locator_object = _require_object(locator_value, "enmityManualInput.observedItemReference")
    try:
        return ReviewSourceLocator.from_dict(locator_object)
    except ValueError as error:
        _fail("OBSERVED_ITEM_REFERENCE", str(error))


def validate_document(document_value: Any) -> None:
    document = _require_object(document_value, "build state")
    _require_exact_keys(document, _DOCUMENT_KEYS, "build state")
    if document["documentType"] != DOCUMENT_TYPE:
        _fail("DOCUMENT_TYPE", f"Document type must be {DOCUMENT_TYPE}")
    if document["schemaVersion"] != BUILD_STATE_SCHEMA_VERSION:
        _fail("SCHEMA_VERSION", "Build-state schema version must be 2.0.0")
    if document["applicationDataContractVersion"] != APPLICATION_DATA_CONTRACT_VERSION:
        _fail("APPLICATION_CONTRACT_VERSION", "Application data-contract version must be 2.0.0")
    if document["importerContractVersion"] != IMPORTER_CONTRACT_VERSION:
        _fail("IMPORTER_CONTRACT_VERSION", "Importer contract version must be 1.0.0")

    # The unchanged BUILD-001 structures retain their exact runtime semantics.
    legacy_projection = {
        key: document[key]
        for key in legacy_codec._DOCUMENT_KEY_ORDER
    }
    legacy_projection["schemaVersion"] = LEGACY_BUILD_STATE_SCHEMA_VERSION
    legacy_projection["applicationDataContractVersion"] = (
        LEGACY_APPLICATION_DATA_CONTRACT_VERSION
    )
    legacy_codec.validate_document(legacy_projection)

    copied_ids = _validate_copied_entries(document["copiedItemEntries"])
    locator = _validate_enmity_input(document["enmityManualInput"])
    if locator is None:
        return
    if locator.provenanceKind == "copied-text":
        valid = locator.sourceId in copied_ids
    elif locator.provenanceKind == "manual-entry":
        valid = locator.sourceId in {
            entry["entryId"] for entry in document["manualMercenaryEquipment"]
        }
    else:
        imported = document["importedResult"]
        valid = imported is not None and locator.sourceId in {
            item["occurrenceId"] for item in imported["document"]["items"]
        }
    if not valid:
        _fail(
            "DANGLING_OBSERVED_ITEM_REFERENCE",
            "Observed Enmity material does not resolve to a current canonical item source",
        )


def item_set_occurrence_ids(document: Mapping[str, Any]) -> tuple[str, ...]:
    validate_document(document)
    imported = document["importedResult"]
    if imported is None:
        return ()
    return tuple(value["occurrenceId"] for value in imported["document"]["itemSets"])


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


def migrate_v1_document(document_value: Any) -> dict[str, Any]:
    legacy_codec.validate_document(document_value)
    document = copy.deepcopy(document_value)
    document["schemaVersion"] = BUILD_STATE_SCHEMA_VERSION
    document["applicationDataContractVersion"] = APPLICATION_DATA_CONTRACT_VERSION
    # Insertions are re-ordered by the v2 serializer; the source document is
    # never modified or written during migration.
    document["copiedItemEntries"] = []
    document["enmityManualInput"] = empty_enmity_manual_input()
    validate_document(document)
    serialize(document)
    return document


def decode(data: bytes) -> DecodedBuildState:
    parsed = _decode_json(data)
    schema_version = parsed.get("schemaVersion")
    if schema_version == BUILD_STATE_SCHEMA_VERSION:
        validate_document(parsed)
        document = copy.deepcopy(parsed)
        return DecodedBuildState(document, schema_version, False, serialize(document))
    if schema_version == LEGACY_BUILD_STATE_SCHEMA_VERSION:
        legacy_codec.validate_document(parsed)
        migrated = migrate_v1_document(parsed)
        return DecodedBuildState(
            copy.deepcopy(migrated),
            schema_version,
            True,
            serialize(migrated),
        )
    _fail(
        "SCHEMA_VERSION",
        "Build-state schema version must be 1.0.0 or 2.0.0; future versions are rejected",
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
