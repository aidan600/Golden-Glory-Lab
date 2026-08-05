"""Exact claim/version/polarity/policy evaluation without formula execution."""

from __future__ import annotations

from .model import (
    ClaimRecord,
    GateDecision,
    GateManifest,
    GateReason,
    GateRequirement,
    OutputGate,
)

_ORDINAL_RANK = {"supported": 1, "confirmed": 2}
_FAILED_STATUSES = {"provisional", "unknown", "superseded"}


def _reason(
    code: str,
    message: str,
    output: OutputGate,
    requirement: GateRequirement | None = None,
) -> GateReason:
    return GateReason(
        code=code,
        message=message,
        outputId=output.outputId,
        auditId=None if requirement is None else requirement.auditId,
        contractVersion=(
            None if requirement is None else requirement.contractVersion
        ),
        claimId=None if requirement is None else requirement.claimId,
        unmetBehavior=(
            output.unmetBehavior
            if requirement is None
            else requirement.unmetBehavior
        ),
    )


def _find_claim(
    manifest: GateManifest,
    output: OutputGate,
    requirement: GateRequirement,
) -> tuple[ClaimRecord | None, GateReason | None]:
    by_claim = [
        claim for claim in manifest.claims if claim.claimId == requirement.claimId
    ]
    if not by_claim:
        return None, _reason(
            "MISSING_CLAIM",
            f"Required claim {requirement.claimId} is missing",
            output,
            requirement,
        )
    by_audit = [claim for claim in by_claim if claim.auditId == requirement.auditId]
    if not by_audit:
        return None, _reason(
            "AUDIT_ID_MISMATCH",
            f"Claim {requirement.claimId} is not recorded under {requirement.auditId}",
            output,
            requirement,
        )
    by_version = [
        claim
        for claim in by_audit
        if claim.contractVersion == requirement.contractVersion
    ]
    if not by_version:
        return None, _reason(
            "CONTRACT_VERSION_MISMATCH",
            (
                f"Claim {requirement.claimId} does not match contract "
                f"{requirement.contractVersion}"
            ),
            output,
            requirement,
        )
    if len(by_version) != 1:
        return None, _reason(
            "AMBIGUOUS_CLAIM",
            f"Claim {requirement.claimId} has duplicate exact records",
            output,
            requirement,
        )
    return by_version[0], None


def _evaluate_requirement(
    claim: ClaimRecord,
    output: OutputGate,
    requirement: GateRequirement,
) -> GateReason | None:
    if requirement.kind == "ordinal":
        if requirement.gateMode != "requires-positive-capability":
            return _reason(
                "INCORRECT_GATE_MODE",
                f"Unsupported ordinal gate mode {requirement.gateMode}",
                output,
                requirement,
            )
        if claim.gatePolarity != "positive-capability":
            return _reason(
                "GATE_POLARITY_MISMATCH",
                (
                    f"Ordinal gate {requirement.claimId} requires a "
                    "positive-capability claim"
                ),
                output,
                requirement,
            )
        minimum_rank = _ORDINAL_RANK.get(requirement.minimumStatus or "")
        if minimum_rank is None:
            return _reason(
                "INVALID_MINIMUM_STATUS",
                f"Unsupported minimum status {requirement.minimumStatus}",
                output,
                requirement,
            )
        current_rank = _ORDINAL_RANK.get(claim.currentClaimStatus)
        if current_rank is None or current_rank < minimum_rank:
            code = (
                "CLAIM_STATUS_UNAVAILABLE"
                if claim.currentClaimStatus in _FAILED_STATUSES
                else "CLAIM_STATUS_BELOW_MINIMUM"
            )
            return _reason(
                code,
                (
                    f"Claim {claim.claimId} status {claim.currentClaimStatus} "
                    f"does not satisfy {requirement.minimumStatus}"
                ),
                output,
                requirement,
            )
        return None

    if claim.gatePolarity != "product-policy":
        return _reason(
            "GATE_POLARITY_MISMATCH",
            f"Policy gate {requirement.claimId} requires a product-policy claim",
            output,
            requirement,
        )
    if claim.policyMode != requirement.policyMode:
        return _reason(
            "POLICY_MODE_MISMATCH",
            (
                f"Claim {claim.claimId} policy mode {claim.policyMode} does not "
                f"match {requirement.policyMode}"
            ),
            output,
            requirement,
        )
    if claim.currentClaimStatus != requirement.requiredStatus:
        return _reason(
            "POLICY_STATUS_MISMATCH",
            (
                f"Policy {claim.claimId} status {claim.currentClaimStatus} does not "
                f"exactly match {requirement.requiredStatus}"
            ),
            output,
            requirement,
        )
    return None


def evaluate_output(
    manifest: GateManifest,
    output_id: str,
    *,
    target_game_version: str | None = None,
) -> GateDecision:
    output = manifest.output(output_id)
    if output is None:
        missing = GateReason(
            code="MISSING_OUTPUT_GATE",
            message=f"Runtime manifest has no output gate {output_id}",
            outputId=output_id,
            unmetBehavior="withhold-requested-output",
        )
        return GateDecision(
            output_id,
            False,
            "unavailable",
            None,
            (missing,),
            (),
        )
    reasons: list[GateReason] = []
    expected_version = target_game_version or manifest.targetGameVersion
    if manifest.targetGameVersion != expected_version or output.targetGameVersion != expected_version:
        reasons.append(
            _reason(
                "TARGET_GAME_VERSION_MISMATCH",
                (
                    f"Manifest/output target does not exactly match {expected_version}"
                ),
                output,
            )
        )
    for requirement in output.requirements:
        claim, lookup_reason = _find_claim(manifest, output, requirement)
        if lookup_reason is not None:
            reasons.append(lookup_reason)
            continue
        assert claim is not None
        gate_reason = _evaluate_requirement(claim, output, requirement)
        if gate_reason is not None:
            reasons.append(gate_reason)
    state = (
        "version-mismatched"
        if any(reason.code == "TARGET_GAME_VERSION_MISMATCH" for reason in reasons)
        else "unavailable"
        if reasons
        else "available"
    )
    return GateDecision(
        outputId=output.outputId,
        available=not reasons,
        state=state,
        value=None,
        reasons=tuple(reasons),
        claimReferences=tuple(
            requirement.claimId for requirement in output.requirements
        ),
    )


def evaluate_all_outputs(
    manifest: GateManifest,
    *,
    target_game_version: str | None = None,
) -> dict[str, GateDecision]:
    return {
        output.outputId: evaluate_output(
            manifest,
            output.outputId,
            target_game_version=target_game_version,
        )
        for output in manifest.outputs
    }
