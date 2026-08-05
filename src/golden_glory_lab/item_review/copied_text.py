"""Deterministic copied-item recognizer with exact source preservation."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any, NoReturn

from .model import ParsedIdentity, RecognitionReport, RecognitionResult

COPIED_ITEM_LIMITS = {
    "maxEntries": 64,
    "maxRawTextCharacters": 100_000,
    "maxEntryIdCharacters": 80,
    "maxUserLabelCharacters": 80,
    "maxSlotLabelCharacters": 80,
    "maxNoteCharacters": 10_000,
}

# Ordered from the least confident/most restrictive terminal classification.
# Tests exercise every row directly so a later parser extension cannot silently
# promote ambiguous material.
STATE_AGGREGATION_TABLE = (
    {
        "condition": "any malformed report",
        "state": "malformed",
    },
    {
        "condition": "required identity decision is manually required",
        "state": "manually-required",
    },
    {
        "condition": "supported facts plus ambiguous or unrecognized material",
        "state": "partially-recognized",
    },
    {
        "condition": "no supported identity or structure recognized",
        "state": "unrecognized",
    },
    {
        "condition": "all in-scope material recognized or ignored as irrelevant",
        "state": "recognized",
    },
)

_ITEM_CLASS_RE = re.compile(r"^Item Class: ([A-Za-z][A-Za-z ]*)$")
_RARITY_RE = re.compile(r"^Rarity: (Normal|Magic|Rare|Unique)$")
_SEPARATOR = "--------"
_IRRELEVANT_EXACT = {"Requirements:", "Sockets:", "Corrupted", "Unidentified"}
_IRRELEVANT_PATTERNS = (
    re.compile(r"^Item Level: [0-9]+$"),
    re.compile(r"^Level: [0-9]+$"),
    re.compile(r"^(?:Str|Dex|Int): [0-9]+$"),
    re.compile(r"^Quality: .+$"),
    re.compile(r"^Note:.*$"),
)
_RANGE_PATTERNS = {
    "strength": re.compile(r"^\+([0-9]+) to Strength$"),
    "increasedFireDamagePercent": re.compile(
        r"^([0-9]+)% increased Fire Damage$"
    ),
    "reducedFireResistancePercentMagnitude": re.compile(
        r"^([0-9]+)% reduced Fire Resistance$"
    ),
    "fireSelfDamageWhenUsingSkill": re.compile(
        r"^([0-9]+) Fire Damage taken when you use a Skill$"
    ),
    "vermillionRingBaseImplicitMaximumLifePercent": re.compile(
        r"^([0-9]+)% increased maximum Life(?: \(implicit\))?$"
    ),
}


class CopiedItemRecognitionError(ValueError):
    """Stable rejected-input error raised before recognition begins."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _fail(code: str, message: str) -> NoReturn:
    raise CopiedItemRecognitionError(code, message)


@dataclass(frozen=True, slots=True)
class _RawLine:
    number: int
    content: str
    ending: str
    start: int
    end: int


def _split_exact_lines(raw_text: str) -> list[_RawLine]:
    if not raw_text:
        return []
    lines: list[_RawLine] = []
    start = 0
    number = 1
    while start < len(raw_text):
        cursor = start
        while cursor < len(raw_text) and raw_text[cursor] not in "\r\n":
            cursor += 1
        if cursor == len(raw_text):
            ending = ""
            next_start = cursor
        elif raw_text[cursor] == "\r" and cursor + 1 < len(raw_text) and raw_text[
            cursor + 1
        ] == "\n":
            ending = "\r\n"
            next_start = cursor + 2
        else:
            ending = raw_text[cursor]
            next_start = cursor + 1
        lines.append(_RawLine(number, raw_text[start:cursor], ending, start, cursor))
        start = next_start
        number += 1
    return lines


class _ReportBuilder:
    def __init__(self) -> None:
        self.values: list[RecognitionReport] = []

    def add(
        self,
        code: str,
        category: str,
        explanation: str,
        line: _RawLine | None = None,
        retained_material: Any = None,
    ) -> None:
        self.values.append(
            RecognitionReport(
                reportId=f"item-report-{len(self.values) + 1:04d}",
                code=code,
                category=category,
                explanation=explanation,
                lineNumber=None if line is None else line.number,
                characterStart=None if line is None else line.start,
                characterEnd=None if line is None else line.end,
                rawLine=None if line is None else line.content,
                lineEnding=None if line is None else line.ending,
                retainedMaterial=retained_material,
            )
        )


def _aggregate_state(
    reports: list[RecognitionReport],
    *,
    recognized_facts: int,
    identity_decision_required: bool,
) -> str:
    categories = {report.category for report in reports}
    if "malformed" in categories:
        return "malformed"
    if identity_decision_required or "manually required" in categories:
        return "manually-required"
    if recognized_facts and categories.intersection({"ambiguous", "unrecognized"}):
        return "partially-recognized"
    if not recognized_facts:
        return "unrecognized"
    return "recognized"


def _identity_line(line: _RawLine) -> bool:
    return bool(line.content) and line.content != _SEPARATOR and ":" not in line.content


def _range_rule(
    line: _RawLine, reference: dict[str, Any]
) -> tuple[str, int, dict[str, int]] | None:
    ranges = reference.get("reviewedNaturalRanges")
    if not isinstance(ranges, dict):
        return None
    for name, pattern in _RANGE_PATTERNS.items():
        match = pattern.fullmatch(line.content)
        range_value = ranges.get(name)
        if not match or not isinstance(range_value, dict):
            continue
        minimum = range_value.get("minimum")
        maximum = range_value.get("maximum")
        if isinstance(minimum, int) and isinstance(maximum, int):
            return name, int(match.group(1)), {
                "minimum": minimum,
                "maximum": maximum,
            }
    return None


def _report_unparsed_remainder(
    reports: _ReportBuilder,
    lines: list[_RawLine],
    used: set[int],
) -> None:
    """Retain one ordered report for every line after an early boundary failure."""

    for index, line in enumerate(lines):
        if index in used:
            continue
        if line.content:
            reports.add(
                "UNRECOGNIZED_ORDERED_ITEM_MATERIAL",
                "unrecognized",
                "The line is retained in order after the structural boundary failure.",
                line,
            )
        else:
            reports.add(
                "BLANK_MATERIAL_RETAINED",
                "ignored as irrelevant",
                "Blank material is retained in its original position.",
                line,
            )


def recognize_copied_item(
    raw_text: str,
    *,
    enmity_reference: dict[str, Any] | None = None,
) -> RecognitionResult:
    """Recognize only the reviewed English envelope and Enmity range patterns.

    The returned ``rawText`` is the caller's exact object value. A transient
    line view excludes line terminators for exact comparisons; every such use
    is disclosed in ``normalizations`` and all report offsets address the
    retained original string.
    """

    if not isinstance(raw_text, str):
        _fail("COPIED_TEXT_TYPE", "Copied-item input must be a string")
    limit = COPIED_ITEM_LIMITS["maxRawTextCharacters"]
    if len(raw_text) > limit:
        _fail(
            "COPIED_TEXT_LIMIT",
            f"Copied-item input is {len(raw_text)} characters; the limit is {limit}",
        )
    if not raw_text:
        _fail("COPIED_TEXT_EMPTY", "Copied-item input must not be empty")
    try:
        encoded = raw_text.encode("utf-8", errors="strict")
    except UnicodeEncodeError as error:
        _fail(
            "COPIED_TEXT_UTF8",
            f"Copied-item input is not strict UTF-8 encodable at character {error.start}",
        )

    lines = _split_exact_lines(raw_text)
    reports = _ReportBuilder()
    endings = sorted({line.ending for line in lines if line.ending})
    normalizations: list[dict[str, Any]] = []
    if endings:
        normalizations.append(
            {
                "code": "EXCLUDE_LINE_ENDINGS_FROM_TRANSIENT_VIEW",
                "observedLineEndings": endings,
                "retainedRawTextChanged": False,
            }
        )

    content_by_index = [line.content for line in lines]
    nonblank = [index for index, content in enumerate(content_by_index) if content]
    if not nonblank:
        reports.add(
            "NO_SUPPORTED_ITEM_STRUCTURE",
            "unrecognized",
            "No supported copied-item structure was recognized.",
            lines[0] if lines else None,
        )
        return RecognitionResult(
            "unrecognized",
            raw_text,
            hashlib.sha256(encoded).hexdigest(),
            None,
            None,
            tuple(normalizations),
            tuple(reports.values),
        )

    used: set[int] = set()
    for index in range(nonblank[0]):
        reports.add(
            "OUTER_BLANK_MATERIAL_RETAINED",
            "ignored as irrelevant",
            "Leading blank material is retained and has no identity meaning.",
            lines[index],
        )
        used.add(index)

    first_index = nonblank[0]
    first_line = lines[first_index]
    first_content = first_line.content
    if first_content.startswith("\ufeff"):
        first_content = first_content[1:]
        normalizations.append(
            {
                "code": "REMOVE_LEADING_BOM_FROM_TRANSIENT_VIEW",
                "lineNumber": first_line.number,
                "retainedRawTextChanged": False,
            }
        )
    item_class_match = _ITEM_CLASS_RE.fullmatch(first_content)
    if not item_class_match:
        reports.add(
            "UNSUPPORTED_COPIED_ITEM_ENVELOPE",
            "unrecognized",
            "The first material line is not the supported English Item Class envelope.",
            first_line,
        )
        used.add(first_index)
        _report_unparsed_remainder(reports, lines, used)
        return RecognitionResult(
            "unrecognized",
            raw_text,
            hashlib.sha256(encoded).hexdigest(),
            None,
            None,
            tuple(normalizations),
            tuple(reports.values),
        )
    item_class = item_class_match.group(1)
    reports.add(
        "ITEM_CLASS_RECOGNIZED",
        "recognized",
        "Recognized the supported English Item Class field.",
        first_line,
        {"itemClass": item_class},
    )
    used.add(first_index)
    recognized_facts = 1

    remaining_nonblank = [index for index in nonblank if index > first_index]
    if not remaining_nonblank:
        reports.add(
            "MALFORMED_REQUIRED_RARITY_BOUNDARY",
            "malformed",
            "A supported Item Class envelope must be followed by a Rarity field.",
            first_line,
        )
        _report_unparsed_remainder(reports, lines, used)
        parsed = ParsedIdentity(item_class, None, None, None)
        return RecognitionResult(
            "malformed",
            raw_text,
            hashlib.sha256(encoded).hexdigest(),
            parsed,
            None,
            tuple(normalizations),
            tuple(reports.values),
        )

    rarity_index = remaining_nonblank[0]
    rarity_line = lines[rarity_index]
    rarity_match = _RARITY_RE.fullmatch(rarity_line.content)
    if not rarity_match:
        reports.add(
            "MALFORMED_REQUIRED_RARITY_BOUNDARY",
            "malformed",
            "The line following Item Class is not a supported Rarity field.",
            rarity_line,
        )
        used.add(rarity_index)
        _report_unparsed_remainder(reports, lines, used)
        parsed = ParsedIdentity(item_class, None, None, None)
        return RecognitionResult(
            "malformed",
            raw_text,
            hashlib.sha256(encoded).hexdigest(),
            parsed,
            None,
            tuple(normalizations),
            tuple(reports.values),
        )
    rarity = rarity_match.group(1)
    reports.add(
        "RARITY_RECOGNIZED",
        "recognized",
        "Recognized the supported English Rarity field.",
        rarity_line,
        {"rarity": rarity},
    )
    used.add(rarity_index)
    recognized_facts += 1

    next_separator = next(
        (
            index
            for index in range(rarity_index + 1, len(lines))
            if lines[index].content == _SEPARATOR
        ),
        len(lines),
    )
    identity_candidates = [
        index
        for index in range(rarity_index + 1, next_separator)
        if lines[index].content
    ]
    required_count = 2 if rarity in {"Rare", "Unique"} else 1
    identity_decision_required = False
    item_name: str | None = None
    base_type: str | None = None
    if len(identity_candidates) < required_count or any(
        not _identity_line(lines[index])
        for index in identity_candidates[:required_count]
    ):
        line = (
            lines[identity_candidates[0]]
            if identity_candidates
            else rarity_line
        )
        reports.add(
            "ITEM_IDENTITY_MANUALLY_REQUIRED",
            "manually required",
            "The supported envelope does not contain an unambiguous required identity.",
            line,
        )
        identity_decision_required = True
    else:
        if required_count == 2:
            item_name = lines[identity_candidates[0]].content
            base_type = lines[identity_candidates[1]].content
            reports.add(
                "ITEM_NAME_RECOGNIZED",
                "recognized",
                "Recognized the item-name identity line.",
                lines[identity_candidates[0]],
                {"itemName": item_name},
            )
            used.add(identity_candidates[0])
            recognized_facts += 1
        else:
            base_type = lines[identity_candidates[0]].content
        base_index = identity_candidates[required_count - 1]
        reports.add(
            "BASE_TYPE_RECOGNIZED",
            "recognized",
            "Recognized the base-type identity line.",
            lines[base_index],
            {"baseType": base_type},
        )
        used.add(base_index)
        recognized_facts += 1

    if len(identity_candidates) > required_count:
        identity_decision_required = True
        for index in identity_candidates[required_count:]:
            reports.add(
                "AMBIGUOUS_DUPLICATE_IDENTITY_FIELD",
                "manually required",
                "Additional material in the identity section prevents a safe identity decision.",
                lines[index],
            )
            used.add(index)

    header_duplicates = [
        index
        for index, content in enumerate(content_by_index)
        if index not in {first_index, rarity_index}
        and (content.startswith("Item Class:") or content.startswith("Rarity:"))
    ]
    if header_duplicates:
        identity_decision_required = True
        for index in header_duplicates:
            reports.add(
                "AMBIGUOUS_DUPLICATE_IDENTITY_FIELD",
                "manually required",
                "A duplicate Item Class or Rarity field requires user review.",
                lines[index],
            )
            used.add(index)

    parsed_identity = ParsedIdentity(item_class, rarity, item_name, base_type)
    reference_match: dict[str, Any] | None = None
    if enmity_reference is not None:
        identity = enmity_reference.get("identity", {})
        if (
            rarity == "Unique"
            and item_name == identity.get("itemName")
            and base_type == identity.get("baseType")
        ):
            reference_match = {
                "stableReferenceId": enmity_reference.get("stableReferenceId"),
                "auditId": enmity_reference.get("auditId"),
                "contractVersion": enmity_reference.get("contractVersion"),
                "claimReferences": list(
                    enmity_reference.get("claimReferences", [])
                ),
                "itemName": item_name,
                "baseType": base_type,
                "reviewedNaturalRanges": enmity_reference.get(
                    "reviewedNaturalRanges", {}
                ),
                "establishesOwnership": False,
                "establishesEquippedState": False,
                "establishesAvailability": False,
            }
            reports.add(
                "ENMITY_REFERENCE_IDENTITY_MATCH",
                "recognized",
                "The parsed identity matches the reviewed Enmity reference; ownership, equipped state, and availability remain unestablished.",
                lines[identity_candidates[0]] if identity_candidates else rarity_line,
                {
                    "stableReferenceId": enmity_reference.get(
                        "stableReferenceId"
                    )
                },
            )
            recognized_facts += 1

    for index, line in enumerate(lines):
        if index in used:
            continue
        if not line.content:
            reports.add(
                "BLANK_MATERIAL_RETAINED",
                "ignored as irrelevant",
                "Blank material is retained in its original position.",
                line,
            )
            continue
        if line.content == _SEPARATOR:
            reports.add(
                "SECTION_SEPARATOR_RECOGNIZED",
                "recognized",
                "Recognized an ordered copied-item section separator.",
                line,
            )
            recognized_facts += 1
            continue
        if line.content in _IRRELEVANT_EXACT or any(
            pattern.fullmatch(line.content) for pattern in _IRRELEVANT_PATTERNS
        ):
            reports.add(
                "ENVELOPE_PROPERTY_IGNORED",
                "ignored as irrelevant",
                "The structural property is retained but has no BUILD-002 semantic effect.",
                line,
            )
            continue
        if reference_match is not None and enmity_reference is not None:
            range_rule = _range_rule(line, enmity_reference)
            if range_rule is not None:
                name, observed, reviewed_range = range_rule
                outside = not (
                    reviewed_range["minimum"]
                    <= observed
                    <= reviewed_range["maximum"]
                )
                reports.add(
                    (
                        "OBSERVED_VALUE_OUTSIDE_REVIEWED_NATURAL_RANGE"
                        if outside
                        else "ENMITY_REVIEWED_RANGE_LINE_RECOGNIZED"
                    ),
                    "recognized",
                    (
                        "The exact observed value is outside the reviewed natural range and remains unchanged; the difference is informational only."
                        if outside
                        else "Recognized a bounded exact Enmity range line for informational review only."
                    ),
                    line,
                    {
                        "field": name,
                        "observed": observed,
                        "reviewedNaturalRange": reviewed_range,
                        "outsideReviewedNaturalRange": outside,
                        "clamped": False,
                    },
                )
                recognized_facts += 1
                continue
        reports.add(
            "UNRECOGNIZED_ORDERED_ITEM_MATERIAL",
            "unrecognized",
            "The line is retained in order; BUILD-002 does not apply general modifier semantics.",
            line,
        )

    state = _aggregate_state(
        reports.values,
        recognized_facts=recognized_facts,
        identity_decision_required=identity_decision_required,
    )
    return RecognitionResult(
        state,
        raw_text,
        hashlib.sha256(encoded).hexdigest(),
        parsed_identity,
        reference_match,
        tuple(normalizations),
        tuple(reports.values),
    )
