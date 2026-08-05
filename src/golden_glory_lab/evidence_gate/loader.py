"""Strict standard-library loader for pinned packaged runtime resources."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from importlib import resources
from typing import Any, NoReturn

from .model import (
    ClaimRecord,
    GateManifest,
    GateRequirement,
    OutputGate,
    SourceArtifact,
)

_RESOURCE_PACKAGE = "golden_glory_lab.runtime_data"
_MANIFEST_NAME = "enmity-manual-gate-v1.json"
_REFERENCE_NAME = "enmity-reference-v1.json"
_MAX_RESOURCE_BYTES = 200_000

# Filled from exact tracked resource bytes. A reviewed manifest/reference change
# must update both the package data and this production consumer pin.
PINNED_MANIFEST_SHA256 = (
    "030529551ce44b8a533b57dba98da7318e8eb638b7ee9aef417e53643b5a8ac2"
)
PINNED_REFERENCE_SHA256 = (
    "ef604dce20bdf067b83609731c0516a9423c2a722a13e7121470881e64bd141d"
)

_ROOT_KEYS = {
    "resourceType",
    "manifestVersion",
    "targetGameVersion",
    "claims",
    "outputs",
    "sourceArtifacts",
}
_CLAIM_KEYS = {
    "auditId",
    "contractVersion",
    "claimId",
    "currentClaimStatus",
    "gatePolarity",
    "policyMode",
}
_OUTPUT_KEYS = {
    "outputId",
    "targetGameVersion",
    "unmetBehavior",
    "requirements",
}
_ORDINAL_REQUIREMENT_KEYS = {
    "auditId",
    "contractVersion",
    "claimId",
    "gateMode",
    "minimumStatus",
    "unmetBehavior",
}
_POLICY_REQUIREMENT_KEYS = {
    "auditId",
    "contractVersion",
    "claimId",
    "policyMode",
    "requiredStatus",
    "unmetBehavior",
}
_SOURCE_KEYS = {"artifactId", "repositoryPath", "sha256"}


class RuntimeResourceError(ValueError):
    """Stable fail-closed resource error that does not disable intake/review."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message

    def as_reason(self, output_id: str) -> dict[str, str]:
        return {
            "code": self.code,
            "message": self.message,
            "outputId": output_id,
        }


def _fail(code: str, message: str) -> NoReturn:
    raise RuntimeResourceError(code, message)


def _reject_constant(value: str) -> NoReturn:
    _fail("RUNTIME_RESOURCE_NONFINITE", f"JSON constant {value} is forbidden")


def _strict_object(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail("RUNTIME_RESOURCE_DUPLICATE_KEY", f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _parse_json(data: bytes, name: str) -> dict[str, Any]:
    if not isinstance(data, bytes):
        _fail("RUNTIME_RESOURCE_BYTES", f"{name} must be supplied as bytes")
    if len(data) > _MAX_RESOURCE_BYTES:
        _fail("RUNTIME_RESOURCE_LIMIT", f"{name} exceeds the resource byte limit")
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        _fail("RUNTIME_RESOURCE_UTF8", f"{name} is not strict UTF-8: {error}")
    try:
        value = json.loads(
            text,
            parse_constant=_reject_constant,
            object_pairs_hook=_strict_object,
        )
    except RuntimeResourceError:
        raise
    except (json.JSONDecodeError, RecursionError, ValueError) as error:
        _fail("RUNTIME_RESOURCE_JSON", f"{name} is not valid bounded JSON: {error}")
    if not isinstance(value, dict):
        _fail("RUNTIME_RESOURCE_SHAPE", f"{name} root must be an object")
    return value


def _exact_keys(
    value: Mapping[str, Any], expected: set[str], context: str, *, optional: set[str] = set()
) -> None:
    actual = set(value)
    missing = expected - optional - actual
    unknown = actual - expected
    if missing or unknown:
        _fail(
            "RUNTIME_RESOURCE_SHAPE",
            f"{context} fields differ: missing={sorted(missing)} unknown={sorted(unknown)}",
        )


def _string(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value:
        _fail("RUNTIME_RESOURCE_SHAPE", f"{context} must be a nonempty string")
    return value


def _array(value: Any, context: str) -> list[Any]:
    if not isinstance(value, list):
        _fail("RUNTIME_RESOURCE_SHAPE", f"{context} must be an array")
    return value


def _object(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail("RUNTIME_RESOURCE_SHAPE", f"{context} must be an object")
    return value


def _sha256(value: Any, context: str) -> str:
    digest = _string(value, context)
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        _fail("RUNTIME_RESOURCE_SHAPE", f"{context} must be a lowercase SHA-256")
    return digest


def parse_gate_manifest_bytes(
    data: bytes, *, verify_pinned_hash: bool = True
) -> GateManifest:
    digest = hashlib.sha256(data).hexdigest()
    if verify_pinned_hash and digest != PINNED_MANIFEST_SHA256:
        _fail(
            "RUNTIME_MANIFEST_HASH_MISMATCH",
            "The packaged evidence manifest does not match the reviewed consumer pin",
        )
    root = _parse_json(data, _MANIFEST_NAME)
    _exact_keys(root, _ROOT_KEYS, "gate manifest")
    resource_type = _string(root["resourceType"], "resourceType")
    if resource_type != "golden-glory-lab-runtime-evidence-gate":
        _fail("RUNTIME_MANIFEST_TYPE", "Unexpected runtime evidence resource type")
    manifest_version = _string(root["manifestVersion"], "manifestVersion")
    if manifest_version != "1.0.0":
        _fail("RUNTIME_MANIFEST_VERSION", "Unsupported evidence manifest version")
    target_version = _string(root["targetGameVersion"], "targetGameVersion")

    claims: list[ClaimRecord] = []
    claim_ids: set[str] = set()
    for index, raw_value in enumerate(_array(root["claims"], "claims")):
        value = _object(raw_value, f"claims[{index}]")
        _exact_keys(value, _CLAIM_KEYS, f"claims[{index}]", optional={"policyMode"})
        claim = ClaimRecord(
            auditId=_string(value["auditId"], f"claims[{index}].auditId"),
            contractVersion=_string(
                value["contractVersion"], f"claims[{index}].contractVersion"
            ),
            claimId=_string(value["claimId"], f"claims[{index}].claimId"),
            currentClaimStatus=_string(
                value["currentClaimStatus"],
                f"claims[{index}].currentClaimStatus",
            ),
            gatePolarity=_string(
                value["gatePolarity"], f"claims[{index}].gatePolarity"
            ),
            policyMode=(
                _string(value["policyMode"], f"claims[{index}].policyMode")
                if "policyMode" in value
                else None
            ),
        )
        if claim.claimId in claim_ids:
            _fail("RUNTIME_MANIFEST_DUPLICATE_CLAIM", f"Duplicate {claim.claimId}")
        claim_ids.add(claim.claimId)
        claims.append(claim)

    outputs: list[OutputGate] = []
    output_ids: set[str] = set()
    for output_index, raw_output in enumerate(_array(root["outputs"], "outputs")):
        value = _object(raw_output, f"outputs[{output_index}]")
        _exact_keys(value, _OUTPUT_KEYS, f"outputs[{output_index}]")
        requirements: list[GateRequirement] = []
        for requirement_index, raw_requirement in enumerate(
            _array(value["requirements"], f"outputs[{output_index}].requirements")
        ):
            context = f"outputs[{output_index}].requirements[{requirement_index}]"
            requirement = _object(raw_requirement, context)
            ordinal = "gateMode" in requirement or "minimumStatus" in requirement
            policy = "policyMode" in requirement or "requiredStatus" in requirement
            if ordinal == policy:
                _fail(
                    "RUNTIME_MANIFEST_REQUIREMENT_MODE",
                    f"{context} must be exactly one ordinal or policy requirement",
                )
            expected = (
                _ORDINAL_REQUIREMENT_KEYS if ordinal else _POLICY_REQUIREMENT_KEYS
            )
            _exact_keys(requirement, expected, context)
            requirements.append(
                GateRequirement(
                    auditId=_string(requirement["auditId"], f"{context}.auditId"),
                    contractVersion=_string(
                        requirement["contractVersion"],
                        f"{context}.contractVersion",
                    ),
                    claimId=_string(requirement["claimId"], f"{context}.claimId"),
                    unmetBehavior=_string(
                        requirement["unmetBehavior"], f"{context}.unmetBehavior"
                    ),
                    gateMode=(
                        _string(requirement["gateMode"], f"{context}.gateMode")
                        if ordinal
                        else None
                    ),
                    minimumStatus=(
                        _string(
                            requirement["minimumStatus"],
                            f"{context}.minimumStatus",
                        )
                        if ordinal
                        else None
                    ),
                    policyMode=(
                        _string(requirement["policyMode"], f"{context}.policyMode")
                        if policy
                        else None
                    ),
                    requiredStatus=(
                        _string(
                            requirement["requiredStatus"],
                            f"{context}.requiredStatus",
                        )
                        if policy
                        else None
                    ),
                )
            )
        output = OutputGate(
            outputId=_string(value["outputId"], f"outputs[{output_index}].outputId"),
            targetGameVersion=_string(
                value["targetGameVersion"],
                f"outputs[{output_index}].targetGameVersion",
            ),
            unmetBehavior=_string(
                value["unmetBehavior"], f"outputs[{output_index}].unmetBehavior"
            ),
            requirements=tuple(requirements),
        )
        if output.outputId in output_ids:
            _fail(
                "RUNTIME_MANIFEST_DUPLICATE_OUTPUT",
                f"Duplicate output {output.outputId}",
            )
        output_ids.add(output.outputId)
        outputs.append(output)

    source_artifacts: list[SourceArtifact] = []
    artifact_ids: set[str] = set()
    for index, raw_source in enumerate(
        _array(root["sourceArtifacts"], "sourceArtifacts")
    ):
        value = _object(raw_source, f"sourceArtifacts[{index}]")
        _exact_keys(value, _SOURCE_KEYS, f"sourceArtifacts[{index}]")
        artifact = SourceArtifact(
            artifactId=_string(
                value["artifactId"], f"sourceArtifacts[{index}].artifactId"
            ),
            repositoryPath=_string(
                value["repositoryPath"],
                f"sourceArtifacts[{index}].repositoryPath",
            ),
            sha256=_sha256(value["sha256"], f"sourceArtifacts[{index}].sha256"),
        )
        if artifact.artifactId in artifact_ids:
            _fail(
                "RUNTIME_MANIFEST_DUPLICATE_SOURCE",
                f"Duplicate source artifact {artifact.artifactId}",
            )
        artifact_ids.add(artifact.artifactId)
        source_artifacts.append(artifact)
    return GateManifest(
        resourceType=resource_type,
        manifestVersion=manifest_version,
        targetGameVersion=target_version,
        claims=tuple(claims),
        outputs=tuple(outputs),
        sourceArtifacts=tuple(source_artifacts),
        byteSha256=digest,
    )


def parse_enmity_reference_bytes(
    data: bytes, *, verify_pinned_hash: bool = True
) -> dict[str, Any]:
    digest = hashlib.sha256(data).hexdigest()
    if verify_pinned_hash and digest != PINNED_REFERENCE_SHA256:
        _fail(
            "RUNTIME_REFERENCE_HASH_MISMATCH",
            "The packaged Enmity reference does not match the reviewed consumer pin",
        )
    value = _parse_json(data, _REFERENCE_NAME)
    expected = {
        "resourceType",
        "resourceVersion",
        "stableReferenceId",
        "auditId",
        "contractVersion",
        "targetGameVersion",
        "claimReferences",
        "identity",
        "reviewedNaturalRanges",
        "itemSpecificCapPercent",
        "observedValuePolicy",
        "sourceArtifact",
    }
    _exact_keys(value, expected, "Enmity reference")
    if value["resourceType"] != "golden-glory-lab-enmity-reference":
        _fail("RUNTIME_REFERENCE_TYPE", "Unexpected Enmity reference type")
    if value["resourceVersion"] != "1.0.0":
        _fail("RUNTIME_REFERENCE_VERSION", "Unsupported Enmity reference version")
    for field in (
        "stableReferenceId",
        "auditId",
        "contractVersion",
        "targetGameVersion",
    ):
        _string(value[field], field)
    if value["auditId"] != "AUD-005" or value["contractVersion"] != "1.0.0":
        _fail(
            "RUNTIME_REFERENCE_CONTRACT",
            "Enmity reference must target exact AUD-005 contract 1.0.0",
        )
    claim_references = _array(value["claimReferences"], "claimReferences")
    if not claim_references:
        _fail("RUNTIME_REFERENCE_SHAPE", "claimReferences must not be empty")
    observed_claims = [
        _string(claim, f"claimReferences[{index}]")
        for index, claim in enumerate(claim_references)
    ]
    if len(set(observed_claims)) != len(observed_claims):
        _fail("RUNTIME_REFERENCE_SHAPE", "claimReferences must be unique")
    identity = _object(value["identity"], "identity")
    _exact_keys(identity, {"rarity", "itemName", "baseType"}, "identity")
    for field in ("rarity", "itemName", "baseType"):
        _string(identity[field], f"identity.{field}")
    ranges = _object(value["reviewedNaturalRanges"], "reviewedNaturalRanges")
    for name, raw_range in ranges.items():
        range_value = _object(raw_range, f"reviewedNaturalRanges.{name}")
        _exact_keys(range_value, {"minimum", "maximum"}, f"range {name}")
        minimum = range_value["minimum"]
        maximum = range_value["maximum"]
        if (
            isinstance(minimum, bool)
            or not isinstance(minimum, int)
            or isinstance(maximum, bool)
            or not isinstance(maximum, int)
            or minimum > maximum
        ):
            _fail("RUNTIME_REFERENCE_SHAPE", f"Invalid reviewed range {name}")
    source = _object(value["sourceArtifact"], "sourceArtifact")
    _exact_keys(source, _SOURCE_KEYS, "sourceArtifact")
    _string(source["artifactId"], "sourceArtifact.artifactId")
    _string(source["repositoryPath"], "sourceArtifact.repositoryPath")
    _sha256(source["sha256"], "sourceArtifact.sha256")
    cap = value["itemSpecificCapPercent"]
    if isinstance(cap, bool) or not isinstance(cap, int) or cap != 200:
        _fail(
            "RUNTIME_REFERENCE_CAP",
            "Enmity reference item-specific cap must be the reviewed integer 200",
        )
    policy = _object(value["observedValuePolicy"], "observedValuePolicy")
    expected_policy = {
        "preserveRawText": True,
        "clamp": False,
        "outsideNaturalRange": "informational-review-only",
        "provesOwnership": False,
        "provesEquippedState": False,
        "provesAvailability": False,
        "provesMechanics": False,
    }
    _exact_keys(policy, set(expected_policy), "observedValuePolicy")
    if policy != expected_policy:
        _fail(
            "RUNTIME_REFERENCE_POLICY",
            "Enmity observed-value policy differs from the reviewed runtime contract",
        )
    value["byteSha256"] = digest
    return value


def _resource_bytes(name: str) -> bytes:
    try:
        return resources.files(_RESOURCE_PACKAGE).joinpath(name).read_bytes()
    except (FileNotFoundError, ModuleNotFoundError, OSError) as error:
        _fail("RUNTIME_RESOURCE_MISSING", f"Could not load packaged {name}: {error}")


def load_gate_manifest() -> GateManifest:
    return parse_gate_manifest_bytes(_resource_bytes(_MANIFEST_NAME))


def load_enmity_reference() -> dict[str, Any]:
    return parse_enmity_reference_bytes(_resource_bytes(_REFERENCE_NAME))


def load_runtime_bundle() -> tuple[GateManifest, dict[str, Any]]:
    manifest = load_gate_manifest()
    reference = load_enmity_reference()
    reference_source = reference["sourceArtifact"]
    manifest_source = next(
        (
            source
            for source in manifest.sourceArtifacts
            if source.artifactId == reference_source["artifactId"]
        ),
        None,
    )
    if manifest_source is None or manifest_source.sha256 != reference_source["sha256"]:
        _fail(
            "RUNTIME_RESOURCE_SOURCE_HASH_MISMATCH",
            "The Enmity reference and evidence manifest disagree on their source artifact",
        )
    if (
        reference["targetGameVersion"] != manifest.targetGameVersion
        or reference["auditId"] != "AUD-005"
        or reference["contractVersion"] != "1.0.0"
    ):
        _fail(
            "RUNTIME_RESOURCE_CONTRACT_MISMATCH",
            "The Enmity reference and evidence manifest disagree on target or contract",
        )
    return manifest, reference
