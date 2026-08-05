"""Typed values shared by the runtime gate loader and evaluator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class SourceArtifact:
    artifactId: str
    repositoryPath: str
    sha256: str

    def to_dict(self) -> dict[str, str]:
        return {
            "artifactId": self.artifactId,
            "repositoryPath": self.repositoryPath,
            "sha256": self.sha256,
        }


@dataclass(frozen=True, slots=True)
class ClaimRecord:
    auditId: str
    contractVersion: str
    claimId: str
    currentClaimStatus: str
    gatePolarity: str
    policyMode: str | None = None

    def to_dict(self) -> dict[str, str]:
        result = {
            "auditId": self.auditId,
            "contractVersion": self.contractVersion,
            "claimId": self.claimId,
            "currentClaimStatus": self.currentClaimStatus,
            "gatePolarity": self.gatePolarity,
        }
        if self.policyMode is not None:
            result["policyMode"] = self.policyMode
        return result


@dataclass(frozen=True, slots=True)
class GateRequirement:
    auditId: str
    contractVersion: str
    claimId: str
    unmetBehavior: str
    gateMode: str | None = None
    minimumStatus: str | None = None
    policyMode: str | None = None
    requiredStatus: str | None = None

    @property
    def kind(self) -> str:
        return "ordinal" if self.gateMode is not None else "policy"

    def to_dict(self) -> dict[str, str]:
        result = {
            "auditId": self.auditId,
            "contractVersion": self.contractVersion,
            "claimId": self.claimId,
            "unmetBehavior": self.unmetBehavior,
        }
        if self.gateMode is not None:
            result["gateMode"] = self.gateMode
        if self.minimumStatus is not None:
            result["minimumStatus"] = self.minimumStatus
        if self.policyMode is not None:
            result["policyMode"] = self.policyMode
        if self.requiredStatus is not None:
            result["requiredStatus"] = self.requiredStatus
        return result


@dataclass(frozen=True, slots=True)
class OutputGate:
    outputId: str
    targetGameVersion: str
    unmetBehavior: str
    requirements: tuple[GateRequirement, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "outputId": self.outputId,
            "targetGameVersion": self.targetGameVersion,
            "unmetBehavior": self.unmetBehavior,
            "requirements": [value.to_dict() for value in self.requirements],
        }


@dataclass(frozen=True, slots=True)
class GateManifest:
    resourceType: str
    manifestVersion: str
    targetGameVersion: str
    claims: tuple[ClaimRecord, ...]
    outputs: tuple[OutputGate, ...]
    sourceArtifacts: tuple[SourceArtifact, ...]
    byteSha256: str

    def output(self, output_id: str) -> OutputGate | None:
        return next(
            (value for value in self.outputs if value.outputId == output_id), None
        )


@dataclass(frozen=True, slots=True)
class GateReason:
    code: str
    message: str
    outputId: str
    auditId: str | None = None
    contractVersion: str | None = None
    claimId: str | None = None
    unmetBehavior: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "code": self.code,
            "message": self.message,
            "outputId": self.outputId,
            "auditId": self.auditId,
            "contractVersion": self.contractVersion,
            "claimId": self.claimId,
            "unmetBehavior": self.unmetBehavior,
        }


@dataclass(frozen=True, slots=True)
class GateDecision:
    outputId: str
    available: bool
    state: str
    value: None
    reasons: tuple[GateReason, ...]
    claimReferences: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "outputId": self.outputId,
            "available": self.available,
            "state": self.state,
            "value": None,
            "reasons": [reason.to_dict() for reason in self.reasons],
            "claimReferences": list(self.claimReferences),
        }
