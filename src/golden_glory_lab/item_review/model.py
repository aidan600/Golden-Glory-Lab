"""Typed, derived item-review values shared by every BUILD item source."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

PROVENANCE_KINDS = {"pob-import", "copied-text", "manual-entry"}
ROLES = {"player", "mercenary", "unassigned"}
BINDING_BASES = {
    "explicit-player-item-set-mapping",
    "explicit-mercenary-item-set-mapping",
    "explicit-copied-role",
    "manual-mercenary-entry",
    "unmapped",
}
RECOGNITION_STATES = {
    "recognized",
    "partially-recognized",
    "unrecognized",
    "malformed",
    "manually-required",
}


@dataclass(frozen=True, slots=True)
class ReviewSourceLocator:
    """Canonical persisted locator; presentation row IDs are deliberately absent."""

    provenanceKind: str
    sourceId: str

    def __post_init__(self) -> None:
        if self.provenanceKind not in PROVENANCE_KINDS:
            raise ValueError(f"unsupported provenance kind: {self.provenanceKind}")
        if not isinstance(self.sourceId, str) or not self.sourceId:
            raise ValueError("sourceId must be a nonempty string")

    @property
    def key(self) -> str:
        return f"{self.provenanceKind}:{self.sourceId}"

    def to_dict(self) -> dict[str, str]:
        return {
            "provenanceKind": self.provenanceKind,
            "sourceId": self.sourceId,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ReviewSourceLocator":
        if not isinstance(value, dict) or set(value) != {
            "provenanceKind",
            "sourceId",
        }:
            raise ValueError("source locator must contain provenanceKind and sourceId")
        return cls(value["provenanceKind"], value["sourceId"])


@dataclass(frozen=True, slots=True)
class ParsedIdentity:
    itemClass: str | None
    rarity: str | None
    itemName: str | None
    baseType: str | None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "itemClass": self.itemClass,
            "rarity": self.rarity,
            "itemName": self.itemName,
            "baseType": self.baseType,
        }


@dataclass(frozen=True, slots=True)
class RecognitionReport:
    reportId: str
    code: str
    category: str
    explanation: str
    lineNumber: int | None
    characterStart: int | None
    characterEnd: int | None
    rawLine: str | None
    lineEnding: str | None
    retainedMaterial: Any

    def to_dict(self) -> dict[str, Any]:
        location = (
            "copied-item"
            if self.lineNumber is None
            else (
                f"copied-item:line-{self.lineNumber}:"
                f"characters-{self.characterStart}-{self.characterEnd}"
            )
        )
        return {
            "reportId": self.reportId,
            "code": self.code,
            "category": self.category,
            "location": location,
            "lineNumber": self.lineNumber,
            "characterStart": self.characterStart,
            "characterEnd": self.characterEnd,
            "rawLine": self.rawLine,
            "lineEnding": self.lineEnding,
            "retainedMaterial": self.retainedMaterial,
            "explanation": self.explanation,
        }


@dataclass(frozen=True, slots=True)
class RecognitionResult:
    state: str
    rawText: str
    rawTextSha256: str
    parsedIdentity: ParsedIdentity | None
    referenceMatch: dict[str, Any] | None
    normalizations: tuple[dict[str, Any], ...]
    reports: tuple[RecognitionReport, ...]

    def __post_init__(self) -> None:
        if self.state not in RECOGNITION_STATES:
            raise ValueError(f"unsupported recognition state: {self.state}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "rawText": self.rawText,
            "rawTextSha256": self.rawTextSha256,
            "parsedIdentity": (
                None if self.parsedIdentity is None else self.parsedIdentity.to_dict()
            ),
            "referenceMatch": self.referenceMatch,
            "normalizations": [dict(value) for value in self.normalizations],
            "reports": [report.to_dict() for report in self.reports],
        }


@dataclass(frozen=True, slots=True)
class AssignmentBinding:
    role: str
    basis: str
    slotLabel: str | None
    assignmentLabel: str | None
    sourceItemSetOccurrenceId: str | None
    sourceAssignmentId: str | None
    resolutionState: str

    def __post_init__(self) -> None:
        if self.role not in ROLES:
            raise ValueError(f"unsupported role: {self.role}")
        if self.basis not in BINDING_BASES:
            raise ValueError(f"unsupported binding basis: {self.basis}")

    def to_dict(self) -> dict[str, str | None]:
        return {
            "role": self.role,
            "basis": self.basis,
            "slotLabel": self.slotLabel,
            "assignmentLabel": self.assignmentLabel,
            "sourceItemSetOccurrenceId": self.sourceItemSetOccurrenceId,
            "sourceAssignmentId": self.sourceAssignmentId,
            "resolutionState": self.resolutionState,
        }


@dataclass(frozen=True, slots=True)
class ItemReview:
    reviewInstanceId: str
    sourceLocator: ReviewSourceLocator
    exactRawText: str
    rawTextSha256: str
    sourceReference: str
    bindings: tuple[AssignmentBinding, ...]
    slotOrAssignmentLabels: tuple[str, ...]
    recognitionState: str
    parsedIdentity: ParsedIdentity | None
    referenceMatch: dict[str, Any] | None
    recognitionReports: tuple[RecognitionReport, ...]
    normalizations: tuple[dict[str, Any], ...]
    warnings: tuple[str, ...]
    userNote: str

    @property
    def provenanceKind(self) -> str:
        return self.sourceLocator.provenanceKind

    def to_dict(self) -> dict[str, Any]:
        return {
            "reviewInstanceId": self.reviewInstanceId,
            "sourceItemId": self.sourceLocator.sourceId,
            "provenanceKind": self.sourceLocator.provenanceKind,
            "sourceLocator": self.sourceLocator.to_dict(),
            "exactRawText": self.exactRawText,
            "rawTextSha256": self.rawTextSha256,
            "sourceReference": self.sourceReference,
            "bindings": [binding.to_dict() for binding in self.bindings],
            "slotOrAssignmentLabels": list(self.slotOrAssignmentLabels),
            "recognitionState": self.recognitionState,
            "parsedIdentity": (
                None if self.parsedIdentity is None else self.parsedIdentity.to_dict()
            ),
            "referenceMatch": self.referenceMatch,
            "recognitionReports": [
                report.to_dict() for report in self.recognitionReports
            ],
            "normalizations": [dict(value) for value in self.normalizations],
            "warnings": list(self.warnings),
            "userNote": self.userNote,
        }
