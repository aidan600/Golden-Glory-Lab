#!/usr/bin/env python3
"""Prove BUILD-002's packaged Enmity gate against tracked evidence bytes."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from golden_glory_lab.domain import (  # noqa: E402
    ENMITY_OUTPUT_ID,
    ENMITY_TARGET_OUTPUT_ID,
    TARGET_GAME_VERSION,
)
from golden_glory_lab.evidence_gate import (  # noqa: E402
    parse_enmity_reference_bytes,
    parse_gate_manifest_bytes,
)

MANIFEST_PATH = (
    ROOT
    / "src"
    / "golden_glory_lab"
    / "runtime_data"
    / "enmity-manual-gate-v1.json"
)
REFERENCE_PATH = (
    ROOT
    / "src"
    / "golden_glory_lab"
    / "runtime_data"
    / "enmity-reference-v1.json"
)

EXPECTED_SOURCE_PATHS = {
    "aud-002-claim-inventory": "docs/audits/AUD-002.md",
    "aud-005-claim-inventory": "docs/audits/AUD-005.md",
    "aud-002-mercenary-input-contract-v1": (
        "data/curated/aud-002-mercenary-input-contract-v1.json"
    ),
    "aud-005-enmitys-embrace-reference-v1": (
        "data/curated/aud-005-enmitys-embrace-reference-v1.json"
    ),
    "aud-005-enmitys-embrace-gates-v1": (
        "fixtures/mechanics/aud-005-enmitys-embrace-gates-v1.json"
    ),
}

EXPECTED_CLAIMS = {
    "AUD-005-C03": {
        "auditId": "AUD-005",
        "contractVersion": "1.0.0",
        "claimId": "AUD-005-C03",
        "currentClaimStatus": "supported",
        "gatePolarity": "positive-capability",
    },
    "AUD-005-C04": {
        "auditId": "AUD-005",
        "contractVersion": "1.0.0",
        "claimId": "AUD-005-C04",
        "currentClaimStatus": "supported",
        "gatePolarity": "positive-capability",
    },
    "AUD-002-C06": {
        "auditId": "AUD-002",
        "contractVersion": "1.0.0",
        "claimId": "AUD-002-C06",
        "currentClaimStatus": "supported",
        "gatePolarity": "product-policy",
        "policyMode": "requires-adopted-policy",
    },
    "AUD-005-C10": {
        "auditId": "AUD-005",
        "contractVersion": "1.0.0",
        "claimId": "AUD-005-C10",
        "currentClaimStatus": "supported",
        "gatePolarity": "product-policy",
        "policyMode": "requires-applicable-policy",
    },
}

_CAPABILITY_REQUIREMENTS = {
    "AUD-005-C03": {
        "auditId": "AUD-005",
        "contractVersion": "1.0.0",
        "claimId": "AUD-005-C03",
        "gateMode": "requires-positive-capability",
        "minimumStatus": "supported",
    },
    "AUD-005-C04": {
        "auditId": "AUD-005",
        "contractVersion": "1.0.0",
        "claimId": "AUD-005-C04",
        "gateMode": "requires-positive-capability",
        "minimumStatus": "supported",
    },
}
_POLICY_REQUIREMENTS = {
    "AUD-002-C06": {
        "auditId": "AUD-002",
        "contractVersion": "1.0.0",
        "claimId": "AUD-002-C06",
        "policyMode": "requires-adopted-policy",
        "requiredStatus": "supported",
    },
    "AUD-005-C10": {
        "auditId": "AUD-005",
        "contractVersion": "1.0.0",
        "claimId": "AUD-005-C10",
        "policyMode": "requires-applicable-policy",
        "requiredStatus": "supported",
    },
}


class ManifestValidationError(RuntimeError):
    """Stable build-time evidence-manifest validation failure."""


def _fail(message: str) -> NoReturn:
    raise ManifestValidationError(message)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git_output(root: Path, *args: str) -> bytes:
    try:
        return subprocess.check_output(
            ["git", "-C", str(root), *args],
            stderr=subprocess.STDOUT,
        )
    except FileNotFoundError as error:
        _fail(f"git is required to validate canonical evidence bytes: {error}")
    except subprocess.CalledProcessError as error:
        detail = error.output.decode("utf-8", errors="replace").strip()
        _fail(f"git {' '.join(args)} failed: {detail or error}")


def _require_tracked_path(root: Path, relative_path: str) -> None:
    try:
        subprocess.check_call(
            ["git", "-C", str(root), "ls-files", "--error-unmatch", relative_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        _fail(f"{relative_path} is not a tracked repository path")


def _canonical_tracked_bytes(root: Path, relative_path: str) -> bytes:
    """Return exact Git blob bytes for a tracked path; do not normalize them."""

    _require_tracked_path(root, relative_path)
    data = _git_output(root, "cat-file", "blob", f"HEAD:{relative_path}")
    if b"\r" in data:
        _fail(
            f"{relative_path} canonical tracked bytes contain CR; "
            "pinned evidence sources must use LF line endings"
        )
    return data


def _strict_json(data: bytes, label: str) -> dict[str, Any]:
    try:
        text = data.decode("utf-8", errors="strict")
        value = json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        _fail(f"{label} is not strict UTF-8 JSON: {error}")
    if not isinstance(value, dict):
        _fail(f"{label} must have an object root")
    return value


def _claim_inventory(data: bytes, audit_id: str) -> tuple[str, dict[str, dict[str, str]]]:
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        _fail(f"{audit_id} Markdown is not strict UTF-8: {error}")
    contract_match = re.search(
        r"^Contract version: `([^`]+)`\.\r?$", text, re.MULTILINE
    )
    if contract_match is None:
        _fail(f"{audit_id} has no exact contract-version declaration")
    marker = "## Claim inventory"
    if marker not in text:
        _fail(f"{audit_id} has no claim inventory")
    inventory = text.split(marker, 1)[1].split("\n## ", 1)[0]
    claims: dict[str, dict[str, str]] = {}
    for line in inventory.splitlines():
        if not line.startswith("| `"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 4:
            continue
        claim_id = cells[0].strip("`")
        if not claim_id.startswith(f"{audit_id}-C"):
            continue
        claims[claim_id] = {
            "currentClaimStatus": cells[2].strip("`"),
            "gatePolarity": cells[3].strip("`"),
        }
    if not claims:
        _fail(f"{audit_id} claim inventory contains no claims")
    return contract_match.group(1), claims


def _require_equal(observed: Any, expected: Any, label: str) -> None:
    if observed != expected:
        _fail(f"{label} mismatch: expected {expected!r}, observed {observed!r}")


def _validate_claims(
    manifest: Any,
    source_bytes: Mapping[str, bytes],
) -> None:
    inventories = {
        audit_id: _claim_inventory(
            source_bytes[f"docs/audits/{audit_id}.md"], audit_id
        )
        for audit_id in ("AUD-002", "AUD-005")
    }
    observed_claims = {claim.claimId: claim.to_dict() for claim in manifest.claims}
    _require_equal(set(observed_claims), set(EXPECTED_CLAIMS), "runtime claim set")
    for claim_id, expected in EXPECTED_CLAIMS.items():
        _require_equal(observed_claims[claim_id], expected, f"runtime claim {claim_id}")
        audit_id = expected["auditId"]
        contract_version, inventory = inventories[audit_id]
        _require_equal(
            contract_version,
            expected["contractVersion"],
            f"{audit_id} contract version",
        )
        if claim_id not in inventory:
            _fail(f"{claim_id} is missing from the exact Markdown claim inventory")
        _require_equal(
            inventory[claim_id]["currentClaimStatus"],
            expected["currentClaimStatus"],
            f"{claim_id} Markdown status",
        )
        _require_equal(
            inventory[claim_id]["gatePolarity"],
            expected["gatePolarity"],
            f"{claim_id} Markdown polarity",
        )

    aud002_text = source_bytes["docs/audits/AUD-002.md"].decode("utf-8")
    if (
        "| `AUD-002-C06` | `requires-adopted-policy` |"
        not in aud002_text
    ):
        _fail("AUD-002-C06 exact policy-mode declaration is missing")


def _validate_outputs(manifest: Any) -> None:
    _require_equal(manifest.targetGameVersion, TARGET_GAME_VERSION, "manifest target")
    observed_outputs = {output.outputId: output for output in manifest.outputs}
    _require_equal(
        set(observed_outputs),
        {ENMITY_OUTPUT_ID, ENMITY_TARGET_OUTPUT_ID},
        "runtime output set",
    )
    expected_by_output = {
        ENMITY_OUTPUT_ID: {
            **_CAPABILITY_REQUIREMENTS,
            "AUD-002-C06": _POLICY_REQUIREMENTS["AUD-002-C06"],
        },
        ENMITY_TARGET_OUTPUT_ID: {
            **_CAPABILITY_REQUIREMENTS,
            **_POLICY_REQUIREMENTS,
        },
    }
    for output_id, expected_requirements in expected_by_output.items():
        output = observed_outputs[output_id]
        _require_equal(output.targetGameVersion, TARGET_GAME_VERSION, f"{output_id} target")
        observed_requirements = {
            requirement.claimId: {
                key: value
                for key, value in requirement.to_dict().items()
                if key != "unmetBehavior"
            }
            for requirement in output.requirements
        }
        _require_equal(
            observed_requirements,
            expected_requirements,
            f"{output_id} exact requirements",
        )
        for requirement in output.requirements:
            if not requirement.unmetBehavior:
                _fail(f"{output_id}/{requirement.claimId} has no unmet behavior")


def _validate_machine_artifacts(source_bytes: Mapping[str, bytes]) -> None:
    aud002 = _strict_json(
        source_bytes["data/curated/aud-002-mercenary-input-contract-v1.json"],
        "AUD-002 artifact",
    )
    aud005 = _strict_json(
        source_bytes["data/curated/aud-005-enmitys-embrace-reference-v1.json"],
        "AUD-005 artifact",
    )
    fixture = _strict_json(
        source_bytes["fixtures/mechanics/aud-005-enmitys-embrace-gates-v1.json"],
        "AUD-005 fixture",
    )
    for label, artifact, audit_id in (
        ("AUD-002 artifact", aud002, "AUD-002"),
        ("AUD-005 artifact", aud005, "AUD-005"),
        ("AUD-005 fixture", fixture, "AUD-005"),
    ):
        _require_equal(artifact.get("auditId"), audit_id, f"{label} audit ID")
        _require_equal(artifact.get("contractVersion"), "1.0.0", f"{label} contract")
        _require_equal(
            artifact.get("targetGameVersion"), TARGET_GAME_VERSION, f"{label} target"
        )

    aud002_claims = {
        claim_id
        for record in aud002.get("records", [])
        for claim_id in record.get("claimIds", [])
    }
    if "AUD-002-C06" not in aud002_claims:
        _fail("AUD-002 machine artifact no longer carries AUD-002-C06")
    formula_records = [
        record
        for record in aud005.get("records", [])
        if record.get("id") == "poe1-enmitys-embrace-manual-isolated-formula"
    ]
    if len(formula_records) != 1:
        _fail("AUD-005 machine artifact has no unique isolated-formula record")
    formula_record = formula_records[0]
    _require_equal(
        set(formula_record.get("claimIds", [])),
        {"AUD-005-C03", "AUD-005-C04", "AUD-005-C10"},
        "AUD-005 formula claim set",
    )
    _require_equal(
        formula_record.get("data", {}).get("formula"),
        {
            "overcap": "max(0,U-M)",
            "enmityOwnFirePenetration": "min(200,overcap)",
        },
        "AUD-005 formula text",
    )
    fixture_claims = {
        claim_id
        for record in fixture.get("records", [])
        for claim_id in record.get("claimIds", [])
    }
    if not {"AUD-005-C03", "AUD-005-C04", "AUD-005-C10"}.issubset(
        fixture_claims
    ):
        _fail("AUD-005 fixture no longer covers every runtime mechanics/policy claim")


def _packaged_runtime_bytes(root: Path, relative_path: str) -> bytes:
    """Hash packaged runtime resources from the checkout that will be shipped.

    Source-artifact pins use canonical Git blob bytes. The runtime resources
    themselves are validated from working-tree bytes so a reviewed pin update can
    be checked before commit, then re-checked against HEAD after commit.
    """

    _require_tracked_path(root, relative_path)
    working = (root / relative_path).read_bytes()
    if b"\r" in working:
        _fail(
            f"{relative_path} working-tree bytes contain CR; "
            "runtime resources must check out as LF"
        )
    blob = _git_output(root, "cat-file", "blob", f"HEAD:{relative_path}")
    if b"\r" in blob:
        _fail(
            f"{relative_path} canonical tracked bytes contain CR; "
            "runtime resources must use LF line endings"
        )
    # When the resource is unmodified, the conforming checkout must match HEAD.
    # Dirty pin updates are allowed to differ until the repair commit lands.
    status = _git_output(
        root, "status", "--porcelain", "--", relative_path
    ).decode("utf-8", errors="replace")
    if not status.strip():
        _require_equal(working, blob, f"clean working-tree bytes for {relative_path}")
    return working


def validate_manifest(
    *,
    root: Path = ROOT,
    manifest_bytes: bytes | None = None,
    reference_bytes: bytes | None = None,
    source_overrides: Mapping[str, bytes] | None = None,
    verify_consumer_pins: bool = True,
) -> dict[str, Any]:
    """Validate exact bytes, claim fields, requirements, and consumer pins."""

    root = root.resolve()
    if manifest_bytes is None:
        manifest_data = _packaged_runtime_bytes(
            root, "src/golden_glory_lab/runtime_data/enmity-manual-gate-v1.json"
        )
    else:
        manifest_data = manifest_bytes
    if reference_bytes is None:
        reference_data = _packaged_runtime_bytes(
            root, "src/golden_glory_lab/runtime_data/enmity-reference-v1.json"
        )
    else:
        reference_data = reference_bytes
    manifest = parse_gate_manifest_bytes(
        manifest_data, verify_pinned_hash=verify_consumer_pins
    )
    reference = parse_enmity_reference_bytes(
        reference_data, verify_pinned_hash=verify_consumer_pins
    )
    observed_sources = {
        source.artifactId: source for source in manifest.sourceArtifacts
    }
    _require_equal(
        {key: value.repositoryPath for key, value in observed_sources.items()},
        EXPECTED_SOURCE_PATHS,
        "source-artifact identity/path map",
    )
    overrides = dict(source_overrides or {})
    source_bytes: dict[str, bytes] = {}
    source_hashes: dict[str, str] = {}
    for source in manifest.sourceArtifacts:
        path = source.repositoryPath
        if path in overrides:
            data = overrides[path]
        else:
            data = _canonical_tracked_bytes(root, path)
            working = (root / path).read_bytes()
            _require_equal(
                working,
                data,
                f"working-tree bytes for {path}",
            )
        source_bytes[path] = data
        digest = _sha256(data)
        source_hashes[path] = digest
        _require_equal(digest, source.sha256, f"source byte hash {path}")

    _validate_claims(manifest, source_bytes)
    _validate_outputs(manifest)
    _validate_machine_artifacts(source_bytes)
    source = reference["sourceArtifact"]
    _require_equal(
        source,
        observed_sources[source["artifactId"]].to_dict(),
        "runtime reference source binding",
    )
    _require_equal(reference["targetGameVersion"], TARGET_GAME_VERSION, "reference target")
    _require_equal(reference["itemSpecificCapPercent"], 200, "reference Enmity cap")
    return {
        "status": "PASS",
        "manifestVersion": manifest.manifestVersion,
        "manifestSha256": manifest.byteSha256,
        "referenceSha256": reference["byteSha256"],
        "sourceArtifacts": len(source_bytes),
        "sourceHashes": source_hashes,
        "claims": len(manifest.claims),
        "outputs": len(manifest.outputs),
        "targetGameVersion": manifest.targetGameVersion,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate BUILD-002's exact runtime evidence manifest."
    )
    parser.add_argument("--root", type=Path, default=ROOT)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = validate_manifest(root=args.root.resolve())
    print("RUNTIME_EVIDENCE_MANIFEST_SUMMARY=" + json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
