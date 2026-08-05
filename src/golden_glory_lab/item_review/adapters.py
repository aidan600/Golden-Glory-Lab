"""Adapters from canonical PoB, copied, and manual sources to one review model."""

from __future__ import annotations

import hashlib
from typing import Any, Mapping

from .copied_text import recognize_copied_item
from .model import (
    AssignmentBinding,
    ItemReview,
    RecognitionReport,
    ReviewSourceLocator,
)


def _review_id(locator: ReviewSourceLocator) -> str:
    digest = hashlib.sha256(locator.key.encode("utf-8")).hexdigest()[:24]
    return f"review-{digest}"


def _raw_digest(raw_text: str) -> str:
    return hashlib.sha256(raw_text.encode("utf-8", errors="strict")).hexdigest()


def _recognition(
    raw_text: str, enmity_reference: dict[str, Any] | None
):
    return recognize_copied_item(raw_text, enmity_reference=enmity_reference)


def _pob_bindings(
    document: Mapping[str, Any], item_occurrence_id: str
) -> tuple[AssignmentBinding, ...]:
    imported = document.get("importedResult")
    if imported is None:
        return ()
    player = document.get("playerItemSetOccurrenceId")
    mercenary = document.get("mercenaryItemSetOccurrenceId")
    mercenary_mode = document.get("mercenarySourceMode")
    bindings: list[AssignmentBinding] = []
    for item_set in imported["document"]["itemSets"]:
        item_set_id = item_set["occurrenceId"]
        if item_set_id == player:
            mapped_role = "player"
            mapped_basis = "explicit-player-item-set-mapping"
        elif mercenary_mode == "mapped-item-set" and item_set_id == mercenary:
            mapped_role = "mercenary"
            mapped_basis = "explicit-mercenary-item-set-mapping"
        else:
            mapped_role = "unassigned"
            mapped_basis = "unmapped"
        for assignment in item_set["assignments"]:
            resolution = assignment["resolution"]
            if item_occurrence_id not in resolution["candidateOccurrences"]:
                continue
            safely_resolved = (
                resolution["state"] == "resolved"
                and resolution["candidateOccurrences"] == [item_occurrence_id]
            )
            raw_slot = assignment["originalSlotName"]
            slot = raw_slot["value"] if raw_slot["state"] == "present" else None
            bindings.append(
                AssignmentBinding(
                    role=mapped_role if safely_resolved else "unassigned",
                    basis=mapped_basis if safely_resolved else "unmapped",
                    slotLabel=slot,
                    assignmentLabel=assignment["sourcePath"],
                    sourceItemSetOccurrenceId=item_set_id,
                    sourceAssignmentId=assignment["occurrenceId"],
                    resolutionState=resolution["state"],
                )
            )
    if not bindings:
        bindings.append(
            AssignmentBinding(
                role="unassigned",
                basis="unmapped",
                slotLabel=None,
                assignmentLabel="item-pool occurrence",
                sourceItemSetOccurrenceId=None,
                sourceAssignmentId=None,
                resolutionState="unmapped",
            )
        )
    return tuple(bindings)


def _manual_report() -> RecognitionReport:
    return RecognitionReport(
        reportId="item-report-0001",
        code="OPAQUE_MANUAL_ENTRY_REQUIRES_REVIEW",
        category="manually required",
        explanation=(
            "Opaque manual equipment is preserved without copied-item parsing or "
            "modifier semantics."
        ),
        lineNumber=None,
        characterStart=None,
        characterEnd=None,
        rawLine=None,
        lineEnding=None,
        retainedMaterial={"reviewState": "unparsed-manual"},
    )


def derive_item_reviews(
    document: Mapping[str, Any],
    *,
    enmity_reference: dict[str, Any] | None = None,
) -> list[ItemReview]:
    """Derive one stable logical review item per canonical source item."""

    reviews: list[ItemReview] = []
    imported = document.get("importedResult")
    if imported is not None:
        for item in imported["document"]["items"]:
            locator = ReviewSourceLocator("pob-import", item["occurrenceId"])
            raw_text = item["xmlCharacterValue"]
            recognition = _recognition(raw_text, enmity_reference)
            bindings = _pob_bindings(document, item["occurrenceId"])
            labels = tuple(
                dict.fromkeys(
                    binding.slotLabel
                    for binding in bindings
                    if binding.slotLabel is not None
                )
            )
            review_warnings = list(item.get("warnings", []))
            review_warnings.extend(
                report.code
                for report in recognition.reports
                if report.category in {"unrecognized", "ambiguous", "malformed"}
            )
            reviews.append(
                ItemReview(
                    reviewInstanceId=_review_id(locator),
                    sourceLocator=locator,
                    exactRawText=raw_text,
                    rawTextSha256=recognition.rawTextSha256,
                    sourceReference=item["sourcePath"],
                    bindings=bindings,
                    slotOrAssignmentLabels=labels,
                    recognitionState=recognition.state,
                    parsedIdentity=recognition.parsedIdentity,
                    referenceMatch=recognition.referenceMatch,
                    recognitionReports=recognition.reports,
                    normalizations=recognition.normalizations,
                    warnings=tuple(dict.fromkeys(review_warnings)),
                    userNote="",
                )
            )

    for entry in document.get("copiedItemEntries", []):
        locator = ReviewSourceLocator("copied-text", entry["entryId"])
        raw_text = entry["rawText"]
        recognition = _recognition(raw_text, enmity_reference)
        binding = AssignmentBinding(
            role=entry["role"],
            basis="explicit-copied-role",
            slotLabel=entry["slotLabel"] or None,
            assignmentLabel=entry["userLabel"] or None,
            sourceItemSetOccurrenceId=None,
            sourceAssignmentId=None,
            resolutionState="explicit",
        )
        reviews.append(
            ItemReview(
                reviewInstanceId=_review_id(locator),
                sourceLocator=locator,
                exactRawText=raw_text,
                rawTextSha256=recognition.rawTextSha256,
                sourceReference=f"application.copiedItemEntries[{entry['entryId']}]",
                bindings=(binding,),
                slotOrAssignmentLabels=tuple(
                    value
                    for value in (entry["slotLabel"], entry["userLabel"])
                    if value
                ),
                recognitionState=recognition.state,
                parsedIdentity=recognition.parsedIdentity,
                referenceMatch=recognition.referenceMatch,
                recognitionReports=recognition.reports,
                normalizations=recognition.normalizations,
                warnings=tuple(
                    report.code
                    for report in recognition.reports
                    if report.category in {"unrecognized", "ambiguous", "malformed"}
                ),
                userNote=entry["note"],
            )
        )

    for entry in document.get("manualMercenaryEquipment", []):
        locator = ReviewSourceLocator("manual-entry", entry["entryId"])
        raw_text = entry["rawText"]
        binding = AssignmentBinding(
            role="mercenary",
            basis="manual-mercenary-entry",
            slotLabel=entry["slotLabel"],
            assignmentLabel=entry["slotLabel"],
            sourceItemSetOccurrenceId=None,
            sourceAssignmentId=None,
            resolutionState="explicit",
        )
        reviews.append(
            ItemReview(
                reviewInstanceId=_review_id(locator),
                sourceLocator=locator,
                exactRawText=raw_text,
                rawTextSha256=_raw_digest(raw_text),
                sourceReference=(
                    f"application.manualMercenaryEquipment[{entry['entryId']}]"
                ),
                bindings=(binding,),
                slotOrAssignmentLabels=(entry["slotLabel"],),
                recognitionState="manually-required",
                parsedIdentity=None,
                referenceMatch=None,
                recognitionReports=(_manual_report(),),
                normalizations=(),
                warnings=("OPAQUE_MANUAL_ENTRY_REQUIRES_REVIEW",),
                userNote=entry["note"],
            )
        )
    return reviews


def review_source_locators(document: Mapping[str, Any]) -> set[ReviewSourceLocator]:
    locators: set[ReviewSourceLocator] = set()
    imported = document.get("importedResult")
    if imported is not None:
        locators.update(
            ReviewSourceLocator("pob-import", item["occurrenceId"])
            for item in imported["document"]["items"]
        )
    locators.update(
        ReviewSourceLocator("copied-text", entry["entryId"])
        for entry in document.get("copiedItemEntries", [])
    )
    locators.update(
        ReviewSourceLocator("manual-entry", entry["entryId"])
        for entry in document.get("manualMercenaryEquipment", [])
    )
    return locators
