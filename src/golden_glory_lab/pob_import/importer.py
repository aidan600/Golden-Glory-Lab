"""Production-intent Path of Building neutral importer.

The public entry points accept raw XML or a PoB share code and converge on one
bounded XML loader and semantic projection. Expected malformed input returns a
versioned failure result; it is not surfaced only as an exception.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import re
import zlib
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from .limits import DEFAULT_IMPORT_LIMITS, ImportLimits
from .xml_tree import (
    XmlLoadFailure,
    attribute_state,
    attribute_value,
    character_value,
    element_children,
    load_xml_tree,
)

CONTRACT_VERSION = "1.0.0"
IMPLEMENTATION_VERSION = "pob-importer-python/0.1.0"
EVIDENCE_PROFILE = [
    {
        "sourceId": "pob-release-2-66-2",
        "revision": "b23da8f841e4b0bc167b0b4401ea002d7d45f807",
    },
    {
        "sourceId": "pob-dev-format-ef4c584",
        "revision": "ef4c5848fad33190f730cebaedff4b5831d0c88d",
    },
    {
        "sourceId": "pob-simplegraphic-codec-3b1a346",
        "revision": "3b1a3468223d0ebd4042d6ce76fc6144718ef79b",
    },
    {
        "sourceId": "pob-pre-itemsets-1-4-36",
        "revision": "69d4e4d4e4cfb82ccca0ebf609d6673e347a98dc",
    },
    {
        "sourceId": "pob-itemsets-1-4-37",
        "revision": "9f981583f7c721917124d604cddf0e8102e62714",
    },
]

_BASE64_RE = re.compile(r"^[A-Za-z0-9_-]*={0,2}$")
_DECIMAL_RE = re.compile(r"^[0-9]+$")
_ABYSSAL_RE = re.compile(r"^(?P<parent>.+) Abyssal Socket (?P<index>[1-6])$")
_KNOWN_SLOT_RE = re.compile(
    r"^(?:Weapon [12](?: Swap)?|Helmet|Body Armour|Gloves|Boots|Amulet|"
    r"Ring [12]|Belt|Flask [1-5]|Charm [1-3]|Graft [1-9][0-9]*)(?: Abyssal Socket [1-6])?$"
)
_UNIQUE_ID_RE = re.compile(r"^Unique ID:[ \t]*(.*)$", re.MULTILINE)


@dataclass(slots=True)
class ImportFailure(Exception):
    code: str
    stage: str
    message: str
    location: dict[str, int] | None = None


class Reporter:
    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.entries: list[dict[str, Any]] = []
        self.dropped = 0

    def add(
        self,
        code: str,
        category: str,
        stage: str,
        location: str,
        explanation: str,
        *,
        occurrence_id: str | None = None,
        retained_material: Any = None,
        candidate_targets: Iterable[str] = (),
    ) -> str:
        report_id = f"report-{len(self.entries) + 1:04d}"
        entry = {
            "reportId": report_id,
            "code": code,
            "category": category,
            "stage": stage,
            "location": location,
            "occurrenceId": occurrence_id,
            "sourcePointer": location,
            "retainedMaterial": retained_material,
            "explanation": explanation,
            "candidateTargets": list(candidate_targets),
        }
        if len(self.entries) < self.limit:
            self.entries.append(entry)
            return report_id
        self.dropped += 1
        sentinel = self.entries[-1]
        if sentinel["code"] != "REPORT_LIMIT_REACHED":
            self.dropped += 1
            self.entries[-1] = {
                "reportId": sentinel["reportId"],
                "code": "REPORT_LIMIT_REACHED",
                "category": "malformed",
                "stage": "reporting",
                "location": "/",
                "occurrenceId": None,
                "sourcePointer": "envelope.limits.maxReportEntries",
                "retainedMaterial": {"droppedEntryCount": self.dropped},
                "explanation": "Additional recognition entries were omitted at the configured report limit.",
                "candidateTargets": [],
            }
        else:
            sentinel["retainedMaterial"]["droppedEntryCount"] = self.dropped
        return self.entries[-1]["reportId"]


def importPobRawXml(input: str, options: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Import a raw PoB XML string into neutral contract v1."""

    original, limits, producing_version = _prepare_input(input, options)
    original_bytes = original.encode("utf-8")
    envelope = _envelope(
        "raw-xml",
        original,
        limits,
        producing_version,
        decoded_xml=None,
        normalized_share_code=None,
        decoded_compressed=None,
        normalizations=[],
        codec_steps=["caller string encoded as UTF-8 for byte limits and hashes"],
    )
    if len(original_bytes) > limits.maxRawXmlBytes:
        return _failure_result(
            envelope,
            "RAW_XML_LIMIT",
            "xml",
            "Raw XML exceeds maxRawXmlBytes",
        )
    return _load_neutral(original, original_bytes, envelope, limits, producing_version)


def importPobShareCode(input: str, options: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Import strict PoB URL-safe Base64/zlib input into neutral contract v1."""

    original, limits, producing_version = _prepare_input(input, options)
    try:
        normalized, compressed, xml_bytes, normalizations = _decode_share_code(original, limits)
        try:
            xml_text = xml_bytes.decode("utf-8", errors="strict")
        except UnicodeDecodeError as error:
            raise ImportFailure(
                "DECOMPRESSED_UTF8_INVALID",
                "decompression",
                "Decompressed XML is not valid UTF-8",
                {"byteOffset": error.start},
            ) from error
        envelope = _envelope(
            "share-code",
            original,
            limits,
            producing_version,
            decoded_xml=xml_text,
            normalized_share_code=normalized,
            decoded_compressed=compressed,
            normalizations=normalizations,
            codec_steps=[
                "trim permitted outer ASCII whitespace when present",
                "restore omitted Base64 padding when present",
                "reverse PoB URL-safe substitutions '-' to '+' and '_' to '/'",
                "strict standard Base64 decode",
                "incremental zlib-wrapped DEFLATE decode",
                "strict UTF-8 decode",
            ],
        )
        return _load_neutral(xml_text, xml_bytes, envelope, limits, producing_version)
    except ImportFailure as failure:
        envelope = _envelope(
            "share-code",
            original,
            limits,
            producing_version,
            decoded_xml=None,
            normalized_share_code=None,
            decoded_compressed=None,
            normalizations=[],
            codec_steps=[
                "PoB URL-safe Base64 envelope",
                "zlib-wrapped DEFLATE stream",
                "UTF-8 XML",
            ],
        )
        return _failure_result(
            envelope,
            failure.code,
            failure.stage,
            failure.message,
            failure.location,
        )


def _prepare_input(
    input: str, options: Mapping[str, Any] | None
) -> tuple[str, ImportLimits, str | None]:
    if not isinstance(input, str):
        raise TypeError("PoB importer input must be a string")
    options = options or {}
    unknown = sorted(set(options) - {"limits", "producingPobVersion"})
    if unknown:
        raise ValueError(f"unknown importer option(s): {', '.join(unknown)}")
    limits = DEFAULT_IMPORT_LIMITS.with_overrides(options.get("limits"))
    producing = options.get("producingPobVersion")
    if producing is not None and not isinstance(producing, str):
        raise ValueError("producingPobVersion must be a string or null")
    return input, limits, producing


def _decode_share_code(
    original: str, limits: ImportLimits
) -> tuple[str, bytes, bytes, list[dict[str, Any]]]:
    if len(original) > limits.maxShareCodeCharacters:
        raise ImportFailure(
            "SHARE_CODE_INPUT_LIMIT",
            "envelope",
            "Share-code input exceeds maxShareCodeCharacters",
        )
    try:
        original.encode("ascii")
    except UnicodeEncodeError as error:
        raise ImportFailure(
            "SHARE_CODE_NON_ASCII",
            "envelope",
            "Share code must contain only the ASCII PoB Base64 alphabet",
            {"characterOffset": error.start},
        ) from error

    normalizations: list[dict[str, Any]] = []
    normalized = original.strip(" \t\r\n")
    if normalized != original:
        normalizations.append(
            {
                "code": "TRIM_OUTER_ASCII_WHITESPACE",
                "beforeCharacters": len(original),
                "afterCharacters": len(normalized),
            }
        )
    if not normalized or not _BASE64_RE.fullmatch(normalized):
        raise ImportFailure(
            "INVALID_BASE64_ALPHABET",
            "envelope",
            "Share code contains invalid Base64 characters or padding placement",
        )
    if "=" in normalized:
        if len(normalized) % 4 != 0:
            raise ImportFailure(
                "INVALID_BASE64_LENGTH",
                "envelope",
                "Padded Base64 length must be a multiple of four",
            )
    else:
        remainder = len(normalized) % 4
        if remainder == 1:
            raise ImportFailure(
                "INVALID_BASE64_LENGTH",
                "envelope",
                "Unpadded Base64 has an impossible length",
            )
        if remainder:
            added = 4 - remainder
            normalized += "=" * added
            normalizations.append(
                {"code": "RESTORE_BASE64_PADDING", "paddingCharactersAdded": added}
            )

    padding = len(normalized) - len(normalized.rstrip("="))
    expected_decoded = (len(normalized) // 4) * 3 - padding
    if expected_decoded > limits.maxDecodedCompressedBytes:
        raise ImportFailure(
            "DECODED_COMPRESSED_LIMIT",
            "envelope",
            "Decoded Base64 payload exceeds maxDecodedCompressedBytes",
        )
    standard = normalized.translate(str.maketrans("-_", "+/"))
    try:
        compressed = base64.b64decode(standard, validate=True)
    except (binascii.Error, ValueError) as error:
        raise ImportFailure(
            "INVALID_BASE64",
            "envelope",
            "Share code is not valid strict Base64",
        ) from error
    if len(compressed) > limits.maxDecodedCompressedBytes:
        raise ImportFailure(
            "DECODED_COMPRESSED_LIMIT",
            "envelope",
            "Decoded Base64 payload exceeds maxDecodedCompressedBytes",
        )
    xml_bytes = _decompress_zlib(compressed, limits)
    return normalized, compressed, xml_bytes, normalizations


def _decompress_zlib(compressed: bytes, limits: ImportLimits) -> bytes:
    decompressor = zlib.decompressobj(wbits=zlib.MAX_WBITS)
    output = bytearray()
    position = 0
    try:
        while position < len(compressed):
            chunk = compressed[position : position + limits.decompressionChunkBytes]
            position += len(chunk)
            pending = chunk
            while pending:
                remaining = limits.maxDecompressedXmlBytes - len(output)
                produced = decompressor.decompress(pending, max_length=remaining + 1)
                output.extend(produced)
                if len(output) > limits.maxDecompressedXmlBytes:
                    raise ImportFailure(
                        "DECOMPRESSED_XML_LIMIT",
                        "decompression",
                        "Decompressed XML exceeds maxDecompressedXmlBytes",
                    )
                if decompressor.unused_data:
                    raise ImportFailure(
                        "ZLIB_TRAILING_DATA",
                        "decompression",
                        "Compressed payload contains data after the zlib stream",
                    )
                if decompressor.eof:
                    if position < len(compressed):
                        raise ImportFailure(
                            "ZLIB_TRAILING_DATA",
                            "decompression",
                            "Compressed payload contains data after the zlib stream",
                        )
                    pending = b""
                    break
                pending = decompressor.unconsumed_tail
        if not decompressor.eof:
            raise ImportFailure(
                "ZLIB_TRUNCATED",
                "decompression",
                "Compressed payload ended before the zlib stream reached EOF",
            )
    except ImportFailure:
        raise
    except zlib.error as error:
        raise ImportFailure(
            "ZLIB_INVALID_STREAM",
            "decompression",
            f"Payload is not a valid zlib-wrapped DEFLATE stream: {error}",
        ) from error
    return bytes(output)


def _envelope(
    input_kind: str,
    original: str,
    limits: ImportLimits,
    producing_version: str | None,
    *,
    decoded_xml: str | None,
    normalized_share_code: str | None,
    decoded_compressed: bytes | None,
    normalizations: list[dict[str, Any]],
    codec_steps: list[str],
) -> dict[str, Any]:
    original_bytes = original.encode("utf-8")
    xml_text = original if input_kind == "raw-xml" else decoded_xml
    xml_bytes = xml_text.encode("utf-8") if xml_text is not None else None
    hashes = [
        {
            "name": "original-input-sha256",
            "algorithm": "SHA-256",
            "byteDomain": "exact original input encoded as UTF-8",
            "digestHex": hashlib.sha256(original_bytes).hexdigest(),
        }
    ]
    if decoded_compressed is not None:
        hashes.append(
            {
                "name": "decoded-compressed-sha256",
                "algorithm": "SHA-256",
                "byteDomain": "strict Base64-decoded compressed bytes",
                "digestHex": hashlib.sha256(decoded_compressed).hexdigest(),
            }
        )
    if xml_bytes is not None:
        hashes.append(
            {
                "name": "xml-utf8-sha256",
                "algorithm": "SHA-256",
                "byteDomain": "exact accepted XML string encoded as UTF-8",
                "digestHex": hashlib.sha256(xml_bytes).hexdigest(),
            }
        )
    return {
        "inputKind": input_kind,
        "originalInput": original,
        "decodedXml": decoded_xml,
        "normalizedShareCode": normalized_share_code,
        "hashes": hashes,
        "sizes": {
            "originalInputCharacters": len(original),
            "originalInputUtf8Bytes": len(original_bytes),
            "normalizedShareCodeCharacters": (
                len(normalized_share_code) if normalized_share_code is not None else None
            ),
            "decodedCompressedBytes": (
                len(decoded_compressed) if decoded_compressed is not None else None
            ),
            "xmlUtf8Bytes": len(xml_bytes) if xml_bytes is not None else None,
        },
        "codecSteps": codec_steps,
        "normalizations": normalizations,
        "limits": limits.to_dict(),
        "implementationVersion": IMPLEMENTATION_VERSION,
        "evidenceProfile": EVIDENCE_PROFILE,
        "suppliedProducingPobVersion": producing_version,
    }


def _failure_result(
    envelope: dict[str, Any],
    code: str,
    stage: str,
    message: str,
    location: dict[str, int] | None = None,
) -> dict[str, Any]:
    source_pointer = "envelope.originalInput"
    return {
        "contractVersion": CONTRACT_VERSION,
        "status": "failure",
        "failure": {
            "code": code,
            "stage": stage,
            "message": message,
            "location": location,
            "sourcePointer": source_pointer,
        },
        "envelope": envelope,
        "sourceMetadata": None,
        "document": None,
        "report": [
            {
                "reportId": "report-0001",
                "code": code,
                "category": "malformed",
                "stage": stage,
                "location": source_pointer,
                "occurrenceId": None,
                "sourcePointer": source_pointer,
                "retainedMaterial": None,
                "explanation": message,
                "candidateTargets": [],
            }
        ],
    }


def _load_neutral(
    xml_text: str,
    xml_bytes: bytes,
    envelope: dict[str, Any],
    limits: ImportLimits,
    producing_version: str | None,
) -> dict[str, Any]:
    try:
        root = load_xml_tree(xml_bytes, limits)
        if root["name"] != "PathOfBuilding":
            raise XmlLoadFailure(
                "XML_ROOT_UNSUPPORTED",
                "Root element must be PathOfBuilding",
                1,
                0,
                0,
            )
    except XmlLoadFailure as failure:
        return _failure_result(
            envelope,
            failure.code,
            "xml",
            failure.message,
            {
                "line": failure.line,
                "column": failure.column,
                "byteOffset": failure.byteIndex,
            },
        )

    reporter = Reporter(limits.maxReportEntries)
    reporter.add(
        "POB_ROOT_RECOGNIZED",
        "recognized",
        "xml",
        "/PathOfBuilding[1]",
        "Recognized the pinned PoB root element.",
    )
    document, source_metadata = _project_document(root, reporter, producing_version)
    return {
        "contractVersion": CONTRACT_VERSION,
        "status": "success",
        "failure": None,
        "envelope": envelope,
        "sourceMetadata": source_metadata,
        "document": document,
        "report": reporter.entries,
    }


def _project_document(
    root: dict[str, Any], reporter: Reporter, producing_version: str | None
) -> tuple[dict[str, Any], dict[str, Any]]:
    root_path = "/PathOfBuilding[1]"
    for attribute in root["attributes"]:
        reporter.add(
            "UNKNOWN_ROOT_ATTRIBUTE",
            "unrecognized",
            "semantic",
            f"{root_path}/@{attribute['name']}",
            "Root attribute is not defined by the pinned profile and is retained.",
            retained_material=attribute,
        )

    top_elements = element_children(root)
    top_inventory: list[dict[str, Any]] = []
    items: list[dict[str, Any]] = []
    item_sets: list[dict[str, Any]] = []
    items_sections: list[dict[str, Any]] = []
    build_targets: list[dict[str, Any]] = []
    passive_refs: list[dict[str, Any]] = []
    cross_refs: list[dict[str, Any]] = []

    name_counts: dict[str, int] = {}
    for source_index, element in enumerate(top_elements):
        name = element["name"]
        name_counts[name] = name_counts.get(name, 0) + 1
        path = f"{root_path}/{name}[{name_counts[name]}]"
        if name in {"Build", "Items", "Tree", "Skills"}:
            classification = "recognized"
        else:
            classification = "unrecognized"
        top_inventory.append(
            {
                "sourceOccurrenceIndex": source_index,
                "name": name,
                "attributes": element["attributes"],
                "classification": classification,
                "sourcePointer": path,
            }
        )
        if name == "Build":
            target = attribute_state(element, "targetVersion")
            build_targets.append({"sourcePointer": f"{path}/@targetVersion", "raw": target})
            reporter.add(
                "BUILD_METADATA_RETAINED",
                "ignored as irrelevant",
                "semantic",
                path,
                "Build content is retained; only targetVersion is named as source metadata.",
                retained_material={"sourcePointer": path},
            )
        elif name == "Items":
            section = _parse_items_section(
                element,
                path,
                len(items_sections),
                items,
                item_sets,
                reporter,
            )
            items_sections.append(section)
        elif name == "Tree":
            _parse_passive_references(element, path, passive_refs, reporter)
            reporter.add(
                "TREE_RELEVANT_REFERENCES_SCANNED",
                "ignored as irrelevant",
                "semantic",
                path,
                "Tree content is retained structurally; only passive jewel references are projected.",
                retained_material={"sourcePointer": path},
            )
        elif name == "Skills":
            _parse_item_set_cross_references(element, path, cross_refs, reporter)
            reporter.add(
                "SKILLS_RELEVANT_REFERENCES_SCANNED",
                "ignored as irrelevant",
                "semantic",
                path,
                "Skills content is retained structurally; only item-set cross-references are projected.",
                retained_material={"sourcePointer": path},
            )
        else:
            reporter.add(
                "UNKNOWN_TOP_LEVEL_ELEMENT",
                "unrecognized",
                "semantic",
                path,
                "Top-level element is unknown to the pinned profile and is retained in sourceTree.",
                retained_material=element,
            )

    _resolve_all(items, item_sets, items_sections, passive_refs, cross_refs, reporter)
    other_versions = _find_version_like_values(root, root_path)
    game_target: dict[str, Any]
    if not build_targets:
        game_target = {"state": "missing", "value": None, "sourcePointers": []}
    elif len(build_targets) == 1:
        game_target = {
            "state": build_targets[0]["raw"]["state"],
            "value": build_targets[0]["raw"]["value"],
            "sourcePointers": [build_targets[0]["sourcePointer"]],
        }
    else:
        game_target = {
            "state": "ambiguous",
            "value": None,
            "sourcePointers": [entry["sourcePointer"] for entry in build_targets],
            "candidates": [entry["raw"] for entry in build_targets],
        }
        reporter.add(
            "MULTIPLE_BUILD_TARGETS",
            "ambiguous",
            "semantic",
            root_path,
            "Multiple Build elements expose more than one game target location.",
            candidate_targets=game_target["sourcePointers"],
        )

    source_metadata = {
        "producingPobVersion": producing_version,
        "producingPobVersionSource": "caller-supplied" if producing_version is not None else "unknown",
        "gameTargetVersion": game_target,
        "otherVersionLikeValues": other_versions,
    }
    document = {
        "rootName": root["name"],
        "rootAttributes": root["attributes"],
        "topLevelNodeInventory": top_inventory,
        "sourceTree": root,
        "itemsSections": items_sections,
        "items": items,
        "itemSets": item_sets,
        "passiveJewelReferences": passive_refs,
        "itemSetCrossReferences": cross_refs,
        "ownershipMapping": None,
        "documentWarnings": [
            entry["code"]
            for entry in reporter.entries
            if entry["category"] in {"unrecognized", "ambiguous", "malformed"}
        ],
    }
    reporter.add(
        "OWNERSHIP_MAPPING_REQUIRED",
        "manually required",
        "mapping",
        "/application/item-set-mapping",
        "Player and optional Mercenary item-set mappings require explicit user confirmation outside imported facts.",
        retained_material={"ownershipMapping": None},
        candidate_targets=[item_set["occurrenceId"] for item_set in item_sets],
    )
    return document, source_metadata


def _parse_items_section(
    element: dict[str, Any],
    path: str,
    section_index: int,
    all_items: list[dict[str, Any]],
    all_sets: list[dict[str, Any]],
    reporter: Reporter,
) -> dict[str, Any]:
    section_id = f"items-section-{section_index + 1:04d}"
    _report_unknown_attributes(
        element,
        {"activeItemSet", "useSecondWeaponSet"},
        path,
        section_id,
        reporter,
    )
    source_children = element_children(element)
    direct_slots: list[tuple[dict[str, Any], str]] = []
    local_set_count = 0
    child_counts: dict[str, int] = {}
    section_item_ids: list[str] = []
    section_set_ids: list[str] = []
    for child in source_children:
        child_counts[child["name"]] = child_counts.get(child["name"], 0) + 1
        child_path = f"{path}/{child['name']}[{child_counts[child['name']]}]"
        if child["name"] == "Item":
            item = _parse_item(child, child_path, len(all_items), reporter)
            all_items.append(item)
            section_item_ids.append(item["occurrenceId"])
        elif child["name"] == "ItemSet":
            item_set = _parse_item_set(child, child_path, len(all_sets), reporter)
            all_sets.append(item_set)
            section_set_ids.append(item_set["occurrenceId"])
            local_set_count += 1
        elif child["name"] == "Slot":
            direct_slots.append((child, child_path))
        else:
            reporter.add(
                "UNKNOWN_ITEMS_CHILD",
                "unrecognized",
                "semantic",
                child_path,
                "Items child is unknown to the pinned neutral profile and is retained.",
                occurrence_id=section_id,
                retained_material=child,
            )

    legacy_assignments: list[dict[str, Any]] = []
    if direct_slots:
        if local_set_count == 0:
            synthesized_id = f"item-set-{len(all_sets) + 1:04d}"
            for slot_index, (slot, slot_path) in enumerate(direct_slots):
                legacy_assignments.append(
                    _parse_assignment(slot, slot_path, synthesized_id, slot_index, reporter)
                )
            synthesized_set = {
                "occurrenceId": synthesized_id,
                "sourceOccurrenceIndex": 0,
                "sourcePath": path,
                "rawId": {"state": "missing", "value": None},
                "parsedId": None,
                "title": {"state": "missing", "value": None},
                "useSecondWeaponSet": _boolean_value(attribute_state(element, "useSecondWeaponSet")),
                "attributes": [],
                "assignments": legacy_assignments,
                "socketIdUrls": [],
                "unknownChildren": [],
                "provenance": {
                    "kind": "legacy-top-level-slots",
                    "synthesized": True,
                    "sourcePointer": path,
                    "synthesizedLegacyIdHint": 1,
                },
                "warnings": ["LEGACY_ITEM_SET_SYNTHESIZED"],
            }
            all_sets.append(synthesized_set)
            section_set_ids.append(synthesized_id)
            reporter.add(
                "LEGACY_ITEM_SET_SYNTHESIZED",
                "recognized",
                "semantic",
                path,
                "Synthesized one neutral legacy item-set occurrence from top-level Slot elements.",
                occurrence_id=synthesized_id,
                retained_material={"slotSourcePointers": [slot_path for _, slot_path in direct_slots]},
            )
        else:
            for slot_index, (slot, slot_path) in enumerate(direct_slots):
                legacy_assignments.append(
                    _parse_assignment(slot, slot_path, section_id, slot_index, reporter)
                )
            reporter.add(
                "TRANSITIONAL_TOP_LEVEL_SLOTS_RETAINED",
                "ignored as irrelevant",
                "semantic",
                path,
                "Top-level transitional slots coexist with nested sets; they are retained but not counted as another set.",
                occurrence_id=section_id,
                retained_material={"slotSourcePointers": [slot_path for _, slot_path in direct_slots]},
            )

    return {
        "occurrenceId": section_id,
        "sourceOccurrenceIndex": section_index,
        "sourcePath": path,
        "attributes": element["attributes"],
        "activeItemSetReference": {
            "raw": attribute_state(element, "activeItemSet"),
            "parsedId": _parse_decimal(attribute_state(element, "activeItemSet")),
            "resolution": None,
        },
        "legacyUseSecondWeaponSet": _boolean_value(attribute_state(element, "useSecondWeaponSet")),
        "itemOccurrences": section_item_ids,
        "itemSetOccurrences": section_set_ids,
        "legacyTopLevelAssignments": legacy_assignments,
        "transitionalTopLevelRepresentation": bool(direct_slots and local_set_count),
    }


def _parse_item(
    element: dict[str, Any], path: str, source_index: int, reporter: Reporter
) -> dict[str, Any]:
    occurrence_id = f"item-{source_index + 1:04d}"
    raw_id = attribute_state(element, "id")
    parsed_id = _parse_decimal(raw_id)
    warnings: list[str] = []
    if parsed_id is None:
        warnings.append("MALFORMED_ITEM_ID")
        reporter.add(
            "MALFORMED_ITEM_ID",
            "malformed",
            "semantic",
            f"{path}/@id",
            "Item ID is missing, empty, or nonnumeric; the occurrence remains retained.",
            occurrence_id=occurrence_id,
            retained_material=raw_id,
        )
    known_attrs = {"id", "variant", "variantAlt", "variantAlt2", "variantAlt3", "variantAlt4", "variantAlt5"}
    _report_unknown_attributes(element, known_attrs, path, occurrence_id, reporter)
    text = character_value(element)
    unique_match = _UNIQUE_ID_RE.search(text)
    mod_ranges: list[dict[str, Any]] = []
    unknown_children: list[dict[str, Any]] = []
    child_counts: dict[str, int] = {}
    for child in element_children(element):
        child_counts[child["name"]] = child_counts.get(child["name"], 0) + 1
        child_path = f"{path}/{child['name']}[{child_counts[child['name']]}]"
        if child["name"] == "ModRange":
            mod_ranges.append(
                {
                    "sourcePointer": child_path,
                    "attributes": child["attributes"],
                    "rawId": attribute_state(child, "id"),
                    "rawRange": attribute_state(child, "range"),
                }
            )
            _report_unknown_attributes(child, {"id", "range"}, child_path, occurrence_id, reporter)
        else:
            unknown_children.append(child)
            reporter.add(
                "UNKNOWN_ITEM_CHILD",
                "unrecognized",
                "semantic",
                child_path,
                "Item child is unknown and retained without modifier interpretation.",
                occurrence_id=occurrence_id,
                retained_material=child,
            )
    reporter.add(
        "ITEM_OCCURRENCE_RECOGNIZED",
        "recognized",
        "semantic",
        path,
        "Retained an item-pool occurrence and its complete XML character value.",
        occurrence_id=occurrence_id,
    )
    return {
        "occurrenceId": occurrence_id,
        "sourceOccurrenceIndex": source_index,
        "sourcePath": path,
        "rawId": raw_id,
        "parsedId": parsed_id,
        "attributes": element["attributes"],
        "xmlCharacterValue": text,
        "orderedChildMaterial": element["children"],
        "modRanges": mod_ranges,
        "unknownChildren": unknown_children,
        "recognizedMetadata": {
            "variantLexemes": [
                {"name": name, "raw": attribute_state(element, name)}
                for name in ["variant", "variantAlt", "variantAlt2", "variantAlt3", "variantAlt4", "variantAlt5"]
                if attribute_state(element, name)["state"] != "missing"
            ]
        },
        "comparisonEvidence": {
            "exactXmlCharacterValueSha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "uniqueIdLine": {
                "state": "present" if unique_match else "missing",
                "value": unique_match.group(1) if unique_match else None,
            },
        },
        "usage": None,
        "warnings": warnings,
    }


def _parse_item_set(
    element: dict[str, Any], path: str, source_index: int, reporter: Reporter
) -> dict[str, Any]:
    occurrence_id = f"item-set-{source_index + 1:04d}"
    raw_id = attribute_state(element, "id")
    parsed_id = _parse_decimal(raw_id)
    warnings: list[str] = []
    if parsed_id is None:
        warnings.append("MALFORMED_ITEM_SET_ID")
        reporter.add(
            "MALFORMED_ITEM_SET_ID",
            "malformed",
            "semantic",
            f"{path}/@id",
            "Item-set ID is missing, empty, or nonnumeric; the occurrence remains selectable by occurrence ID.",
            occurrence_id=occurrence_id,
            retained_material=raw_id,
        )
    title = attribute_state(element, "title")
    weapon_state = _boolean_value(attribute_state(element, "useSecondWeaponSet"))
    if weapon_state["raw"]["state"] != "missing" and weapon_state["parsed"] is None:
        warnings.append("MALFORMED_WEAPON_SET_STATE")
        reporter.add(
            "MALFORMED_WEAPON_SET_STATE",
            "malformed",
            "semantic",
            f"{path}/@useSecondWeaponSet",
            "Alternate-weapon state is not the exact true/false vocabulary.",
            occurrence_id=occurrence_id,
            retained_material=weapon_state["raw"],
        )
    _report_unknown_attributes(element, {"id", "title", "useSecondWeaponSet"}, path, occurrence_id, reporter)
    assignments: list[dict[str, Any]] = []
    socket_urls: list[dict[str, Any]] = []
    unknown_children: list[dict[str, Any]] = []
    child_counts: dict[str, int] = {}
    for child in element_children(element):
        child_counts[child["name"]] = child_counts.get(child["name"], 0) + 1
        child_path = f"{path}/{child['name']}[{child_counts[child['name']]}]"
        if child["name"] == "Slot":
            assignments.append(
                _parse_assignment(child, child_path, occurrence_id, len(assignments), reporter)
            )
        elif child["name"] == "SocketIdURL":
            record = {
                "occurrenceId": f"socket-id-url-{source_index + 1:04d}-{len(socket_urls) + 1:04d}",
                "sourceOccurrenceIndex": len(socket_urls),
                "sourcePath": child_path,
                "attributes": child["attributes"],
                "rawNodeId": attribute_state(child, "nodeId"),
                "parsedNodeId": _parse_decimal(attribute_state(child, "nodeId")),
                "rawName": attribute_state(child, "name"),
                "rawItemPbUrl": attribute_state(child, "itemPbURL"),
            }
            socket_urls.append(record)
            _report_unknown_attributes(child, {"nodeId", "name", "itemPbURL"}, child_path, record["occurrenceId"], reporter)
            if record["parsedNodeId"] is None:
                reporter.add(
                    "MALFORMED_SOCKET_ID_URL_NODE",
                    "malformed",
                    "semantic",
                    f"{child_path}/@nodeId",
                    "SocketIdURL nodeId is missing, empty, or nonnumeric.",
                    occurrence_id=record["occurrenceId"],
                    retained_material=record["rawNodeId"],
                )
        else:
            unknown_children.append(child)
            reporter.add(
                "UNKNOWN_ITEM_SET_CHILD",
                "unrecognized",
                "semantic",
                child_path,
                "Item-set child is unknown and retained.",
                occurrence_id=occurrence_id,
                retained_material=child,
            )
    _mark_duplicate_assignments(assignments, reporter)
    _derive_abyssal_parents(assignments)
    reporter.add(
        "ITEM_SET_OCCURRENCE_RECOGNIZED",
        "recognized",
        "semantic",
        path,
        "Retained one nested item-set occurrence without inferring ownership.",
        occurrence_id=occurrence_id,
    )
    return {
        "occurrenceId": occurrence_id,
        "sourceOccurrenceIndex": source_index,
        "sourcePath": path,
        "rawId": raw_id,
        "parsedId": parsed_id,
        "title": title,
        "useSecondWeaponSet": weapon_state,
        "attributes": element["attributes"],
        "assignments": assignments,
        "socketIdUrls": socket_urls,
        "unknownChildren": unknown_children,
        "provenance": {
            "kind": "nested-item-set",
            "synthesized": False,
            "sourcePointer": path,
            "synthesizedLegacyIdHint": None,
        },
        "warnings": warnings,
    }


def _parse_assignment(
    element: dict[str, Any],
    path: str,
    parent_id: str,
    source_index: int,
    reporter: Reporter,
) -> dict[str, Any]:
    occurrence_id = f"assignment-{parent_id}-{source_index + 1:04d}"
    name = attribute_state(element, "name")
    raw_ref = attribute_state(element, "itemId")
    active = _boolean_value(attribute_state(element, "active"))
    item_url = attribute_state(element, "itemPbURL")
    warnings: list[str] = []
    _report_unknown_attributes(element, {"name", "itemId", "active", "itemPbURL"}, path, occurrence_id, reporter)
    if name["state"] != "present" or not _KNOWN_SLOT_RE.fullmatch(name["value"] or ""):
        warnings.append("UNKNOWN_SLOT_NAME")
        reporter.add(
            "UNKNOWN_SLOT_NAME",
            "unrecognized",
            "semantic",
            f"{path}/@name",
            "Slot name is missing, empty, or outside the pinned vocabulary; the assignment is retained.",
            occurrence_id=occurrence_id,
            retained_material=name,
        )
    return {
        "occurrenceId": occurrence_id,
        "sourceOccurrenceIndex": source_index,
        "sourcePath": path,
        "originalSlotName": name,
        "rawItemReference": raw_ref,
        "parsedItemId": _parse_decimal(raw_ref),
        "active": active,
        "itemPbUrl": item_url,
        "attributes": element["attributes"],
        "resolution": None,
        "derivedAbyssalParent": None,
        "warnings": warnings,
    }


def _parse_passive_references(
    element: dict[str, Any],
    path: str,
    output: list[dict[str, Any]],
    reporter: Reporter,
) -> None:
    for child, child_path in _walk_elements(element, path):
        if child["name"] != "Socket":
            continue
        raw_item = attribute_state(child, "itemId")
        raw_node = attribute_state(child, "nodeId")
        occurrence_id = f"passive-jewel-{len(output) + 1:04d}"
        record = {
            "occurrenceId": occurrence_id,
            "sourceOccurrenceIndex": len(output),
            "sourcePath": child_path,
            "attributes": child["attributes"],
            "rawNodeId": raw_node,
            "parsedNodeId": _parse_decimal(raw_node),
            "rawItemReference": raw_item,
            "parsedItemId": _parse_decimal(raw_item),
            "resolution": None,
            "warnings": [],
        }
        output.append(record)
        reporter.add(
            "PASSIVE_JEWEL_REFERENCE_RECOGNIZED",
            "recognized",
            "semantic",
            child_path,
            "Retained a passive-spec jewel reference separately from equipment assignments.",
            occurrence_id=occurrence_id,
        )


def _parse_item_set_cross_references(
    element: dict[str, Any],
    path: str,
    output: list[dict[str, Any]],
    reporter: Reporter,
) -> None:
    for child, child_path in _walk_elements(element, path):
        if child["name"] != "Gem":
            continue
        for attribute_name in ("skillMinionItemSet", "skillMinionItemSetCalcs"):
            raw = attribute_state(child, attribute_name)
            if raw["state"] == "missing":
                continue
            occurrence_id = f"item-set-reference-{len(output) + 1:04d}"
            record = {
                "occurrenceId": occurrence_id,
                "sourceOccurrenceIndex": len(output),
                "sourcePath": f"{child_path}/@{attribute_name}",
                "referenceKind": attribute_name,
                "rawItemSetReference": raw,
                "parsedItemSetId": _parse_decimal(raw),
                "resolution": None,
                "warnings": [],
            }
            output.append(record)
            reporter.add(
                "ITEM_SET_CROSS_REFERENCE_RECOGNIZED",
                "recognized",
                "semantic",
                record["sourcePath"],
                "Retained an explicit item-set cross-reference without interpreting minion ownership.",
                occurrence_id=occurrence_id,
            )


def _resolve_all(
    items: list[dict[str, Any]],
    item_sets: list[dict[str, Any]],
    sections: list[dict[str, Any]],
    passive_refs: list[dict[str, Any]],
    cross_refs: list[dict[str, Any]],
    reporter: Reporter,
) -> None:
    item_map = _declaration_map(items)
    set_map = _declaration_map(item_sets)
    _report_duplicate_declarations(items, item_map, "ITEM", reporter)
    _report_duplicate_declarations(item_sets, set_map, "ITEM_SET", reporter)

    equipment_counts = {item["occurrenceId"]: 0 for item in items}
    passive_counts = {item["occurrenceId"]: 0 for item in items}
    for item_set in item_sets:
        for assignment in item_set["assignments"]:
            assignment["resolution"] = _resolve_reference(
                assignment["rawItemReference"],
                assignment["parsedItemId"],
                item_map,
                assignment["sourcePath"],
                assignment["occurrenceId"],
                "item",
                reporter,
            )
            for candidate in assignment["resolution"]["candidateOccurrences"]:
                equipment_counts[candidate] += 1
    for section in sections:
        section["activeItemSetReference"]["resolution"] = _resolve_reference(
            section["activeItemSetReference"]["raw"],
            section["activeItemSetReference"]["parsedId"],
            set_map,
            f"{section['sourcePath']}/@activeItemSet",
            section["occurrenceId"],
            "item-set",
            reporter,
        )
        if section["transitionalTopLevelRepresentation"]:
            for assignment in section["legacyTopLevelAssignments"]:
                assignment["resolution"] = _resolve_reference(
                    assignment["rawItemReference"],
                    assignment["parsedItemId"],
                    item_map,
                    assignment["sourcePath"],
                    assignment["occurrenceId"],
                    "item",
                    reporter,
                )
    for reference in passive_refs:
        reference["resolution"] = _resolve_reference(
            reference["rawItemReference"],
            reference["parsedItemId"],
            item_map,
            reference["sourcePath"],
            reference["occurrenceId"],
            "item",
            reporter,
        )
        for candidate in reference["resolution"]["candidateOccurrences"]:
            passive_counts[candidate] += 1
    for reference in cross_refs:
        reference["resolution"] = _resolve_reference(
            reference["rawItemSetReference"],
            reference["parsedItemSetId"],
            set_map,
            reference["sourcePath"],
            reference["occurrenceId"],
            "item-set",
            reporter,
        )
    for item in items:
        equipment = equipment_counts[item["occurrenceId"]]
        passive = passive_counts[item["occurrenceId"]]
        item["usage"] = {
            "state": "unused" if equipment + passive == 0 else "referenced",
            "equipmentCandidateReferenceCount": equipment,
            "passiveCandidateReferenceCount": passive,
        }
        if equipment + passive == 0:
            reporter.add(
                "UNUSED_POOL_ITEM_RETAINED",
                "recognized",
                "semantic",
                item["sourcePath"],
                "Item-pool occurrence has no reference but remains retained as unused.",
                occurrence_id=item["occurrenceId"],
            )


def _resolve_reference(
    raw: dict[str, Any],
    parsed: int | None,
    declarations: dict[int, list[str]],
    location: str,
    occurrence_id: str,
    target_kind: str,
    reporter: Reporter,
) -> dict[str, Any]:
    if raw["state"] in {"missing", "empty"} or parsed is None:
        resolution = {"state": "malformed", "candidateOccurrences": []}
        reporter.add(
            f"MALFORMED_{target_kind.upper().replace('-', '_')}_REFERENCE",
            "malformed",
            "resolution",
            location,
            f"{target_kind.title()} reference is missing, empty, or nonnumeric.",
            occurrence_id=occurrence_id,
            retained_material=raw,
        )
        return resolution
    if parsed == 0:
        return {"state": "empty-reference", "candidateOccurrences": []}
    candidates = declarations.get(parsed, [])
    if len(candidates) == 1:
        return {"state": "resolved", "candidateOccurrences": candidates}
    if len(candidates) > 1:
        reporter.add(
            f"AMBIGUOUS_{target_kind.upper().replace('-', '_')}_REFERENCE",
            "ambiguous",
            "resolution",
            location,
            f"{target_kind.title()} reference matches duplicate declarations; no target was chosen.",
            occurrence_id=occurrence_id,
            retained_material=raw,
            candidate_targets=candidates,
        )
        return {"state": "ambiguous", "candidateOccurrences": candidates}
    reporter.add(
        f"UNRESOLVED_{target_kind.upper().replace('-', '_')}_REFERENCE",
        "malformed",
        "resolution",
        location,
        f"{target_kind.title()} reference has no matching declaration.",
        occurrence_id=occurrence_id,
        retained_material=raw,
    )
    return {"state": "unresolved", "candidateOccurrences": []}


def _declaration_map(records: list[dict[str, Any]]) -> dict[int, list[str]]:
    result: dict[int, list[str]] = {}
    for record in records:
        if record["parsedId"] is not None:
            result.setdefault(record["parsedId"], []).append(record["occurrenceId"])
    return result


def _report_duplicate_declarations(
    records: list[dict[str, Any]],
    declaration_map: dict[int, list[str]],
    prefix: str,
    reporter: Reporter,
) -> None:
    duplicate_occurrences = {
        occurrence
        for candidates in declaration_map.values()
        if len(candidates) > 1
        for occurrence in candidates
    }
    for record in records:
        if record["occurrenceId"] in duplicate_occurrences:
            candidates = declaration_map[record["parsedId"]]
            record["warnings"].append(f"DUPLICATE_{prefix}_ID_DECLARATION")
            reporter.add(
                f"DUPLICATE_{prefix}_ID_DECLARATION",
                "ambiguous",
                "resolution",
                f"{record['sourcePath']}/@id",
                "Duplicate numeric declarations remain separate occurrences.",
                occurrence_id=record["occurrenceId"],
                retained_material=record["rawId"],
                candidate_targets=candidates,
            )


def _mark_duplicate_assignments(assignments: list[dict[str, Any]], reporter: Reporter) -> None:
    by_name: dict[str, list[dict[str, Any]]] = {}
    for assignment in assignments:
        name = assignment["originalSlotName"]["value"]
        if name is not None:
            by_name.setdefault(name, []).append(assignment)
    for candidates in by_name.values():
        if len(candidates) <= 1:
            continue
        ids = [candidate["occurrenceId"] for candidate in candidates]
        for candidate in candidates:
            candidate["warnings"].append("DUPLICATE_SLOT_ASSIGNMENT")
            reporter.add(
                "DUPLICATE_SLOT_ASSIGNMENT",
                "ambiguous",
                "semantic",
                candidate["sourcePath"],
                "Several assignments use the same original slot name; all are retained.",
                occurrence_id=candidate["occurrenceId"],
                candidate_targets=ids,
            )


def _derive_abyssal_parents(assignments: list[dict[str, Any]]) -> None:
    by_name: dict[str, list[dict[str, Any]]] = {}
    for assignment in assignments:
        name = assignment["originalSlotName"]["value"]
        if name is not None:
            by_name.setdefault(name, []).append(assignment)
    for assignment in assignments:
        name = assignment["originalSlotName"]["value"] or ""
        match = _ABYSSAL_RE.fullmatch(name)
        if not match:
            continue
        parent_name = match.group("parent")
        parents = by_name.get(parent_name, [])
        if not parents:
            state = "missing-parent-assignment"
        elif all(parent["parsedItemId"] == 0 for parent in parents):
            state = "empty-parent-assignment"
        else:
            state = "parent-assignment-present"
        assignment["derivedAbyssalParent"] = {
            "originalChildSlotName": name,
            "derivedParentSlotName": parent_name,
            "socketIndex": int(match.group("index")),
            "state": state,
            "candidateParentAssignments": [parent["occurrenceId"] for parent in parents],
        }


def _report_unknown_attributes(
    element: dict[str, Any],
    known: set[str],
    path: str,
    occurrence_id: str,
    reporter: Reporter,
) -> None:
    for attribute in element["attributes"]:
        if attribute["name"] not in known:
            reporter.add(
                "UNKNOWN_ATTRIBUTE",
                "unrecognized",
                "semantic",
                f"{path}/@{attribute['name']}",
                "Attribute is unknown in this pinned context and is retained.",
                occurrence_id=occurrence_id,
                retained_material=attribute,
            )


def _parse_decimal(raw: dict[str, Any]) -> int | None:
    value = raw["value"]
    if raw["state"] != "present" or value is None or not _DECIMAL_RE.fullmatch(value):
        return None
    return int(value)


def _boolean_value(raw: dict[str, Any]) -> dict[str, Any]:
    if raw["state"] == "present" and raw["value"] in {"true", "false"}:
        parsed: bool | None = raw["value"] == "true"
    else:
        parsed = None
    return {"raw": raw, "parsed": parsed}


def _walk_elements(
    element: dict[str, Any], path: str
) -> Iterable[tuple[dict[str, Any], str]]:
    counts: dict[str, int] = {}
    for child in element_children(element):
        counts[child["name"]] = counts.get(child["name"], 0) + 1
        child_path = f"{path}/{child['name']}[{counts[child['name']]}]"
        yield child, child_path
        yield from _walk_elements(child, child_path)


def _find_version_like_values(root: dict[str, Any], root_path: str) -> list[dict[str, str]]:
    values: list[dict[str, str]] = []
    for element, path in [(root, root_path), *_walk_elements(root, root_path)]:
        for attribute in element["attributes"]:
            if "version" not in attribute["name"].lower():
                continue
            if element["name"] == "Build" and attribute["name"] == "targetVersion":
                continue
            values.append(
                {
                    "sourcePointer": f"{path}/@{attribute['name']}",
                    "attributeName": attribute["name"],
                    "rawValue": attribute["value"],
                }
            )
    return values
