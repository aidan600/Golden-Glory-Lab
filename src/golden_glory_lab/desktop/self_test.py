"""Noninteractive packaged BUILD-003 self-test."""

from __future__ import annotations

import hashlib
import json
import platform
import sys
import tempfile
import tkinter as tk
import zlib
from pathlib import Path
from typing import Any
from xml.parsers import expat

from golden_glory_lab.build_state import imported_result_digest, serialize
from golden_glory_lab.domain import ENMITY_OUTPUT_LABEL, FLAME_LINK_OUTPUT_LABEL
from golden_glory_lab.item_review import ReviewSourceLocator

from .service import ApplicationService

SELF_TEST_VERSION = "3.0.0"


def _fixture_path(*parts: str) -> Path:
    bundle_root = getattr(sys, "_MEIPASS", None)
    if isinstance(bundle_root, str):
        return Path(bundle_root).joinpath("ggl_app_resources", *parts)
    return Path(__file__).resolve().parents[3].joinpath("fixtures", *parts)


def _copied_enmity_fixture() -> str:
    path = _fixture_path("item_review", "copied-items-v1.json")
    value = json.loads(path.read_text(encoding="utf-8"))
    return next(
        case["rawText"]
        for case in value["cases"]
        if case["id"] == "recognizable-enmity-crlf"
    )


def _all_keys(value: Any) -> list[str]:
    keys: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            keys.append(key)
            keys.extend(_all_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.extend(_all_keys(child))
    return keys


def _tk_runtime() -> dict[str, str]:
    root = tk.Tk()
    root.withdraw()
    root.update_idletasks()
    tcl_version = str(root.tk.call("info", "patchlevel"))
    tk_version = str(root.tk.call("package", "require", "Tk"))
    root.destroy()
    return {"tclVersion": tcl_version, "tkVersion": tk_version}


def _canonical_json_bytes(value: dict[str, Any]) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            allow_nan=False,
            indent=2,
            separators=(",", ": "),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _complete_context() -> dict[str, str]:
    return {
        "mercenaryIdentityLevel": "Synthetic permanent Mercenary, level 90",
        "activeStateSelection": "Active combat state recorded",
        "zoneOrUiContext": "Hideout character UI",
        "relevantEffectsConditions": "No temporary resistance effects",
        "equipmentStateDescription": "Enmity equipped in Ring 1",
        "captureTimingDescription": "Captured after UI refresh",
    }


def build_self_test_result() -> dict[str, Any]:
    tkinter_runtime = _tk_runtime()
    pob_fixture = _fixture_path("pob", "proof", "comprehensive.xml")
    copied_raw = _copied_enmity_fixture()
    service = ApplicationService()
    outcome = service.attempt_raw_xml(pob_fixture)
    if outcome != "imported":
        raise AssertionError(f"permanent fixture import failed: {outcome}")
    item_sets = service.item_sets()
    occurrences = [entry["occurrenceId"] for entry in item_sets]
    if occurrences != ["item-set-0001", "item-set-0002", "item-set-0003"]:
        raise AssertionError(f"unexpected item-set occurrences: {occurrences}")
    service.set_player_mapping("item-set-0001")
    service.set_mercenary_source("manual-equipment")
    service.add_manual_entry(
        "Ring 2",
        "Synthetic opaque +999% observed text",
        "Self-test material; deliberately unparsed.",
        entry_id="manual-0001",
    )
    service.set_mercenary_source("mapped-item-set", "item-set-0002")
    copied_id = service.add_copied_entry(
        copied_raw,
        role="unassigned",
        slot_label="Ring 1",
        user_label="Synthetic observed Enmity",
        note="Identity recognition does not establish ownership or equipped state.",
        entry_id="copied-0001",
    )

    reviews = service.item_reviews()
    provenance_counts = {
        kind: len([review for review in reviews if review.provenanceKind == kind])
        for kind in ("pob-import", "copied-text", "manual-entry")
    }
    copied_review = next(
        review
        for review in reviews
        if review.sourceLocator == ReviewSourceLocator("copied-text", copied_id)
    )
    if copied_review.exactRawText != copied_raw:
        raise AssertionError("copied-item exact raw text changed during review")
    if copied_review.referenceMatch is None or copied_review.referenceMatch.get(
        "stableReferenceId"
    ) != "poe1-enmitys-embrace":
        raise AssertionError("copied Enmity identity was not recognized")
    if [binding.role for binding in copied_review.bindings] != ["unassigned"]:
        raise AssertionError("copied Enmity identity inferred an owner")
    if service.state["enmityManualInput"]["equippedState"] != "unknown":
        raise AssertionError("copied Enmity identity inferred equipped state")

    evidence = service.runtime_evidence_status()
    if evidence["state"] != "available":
        raise AssertionError(f"runtime evidence resource failed: {evidence}")
    if not all(value["available"] for value in evidence["outputs"].values()):
        raise AssertionError(f"reviewed runtime evidence gates did not pass: {evidence}")

    service.set_enmity_input(
        final_uncapped_fire_resistance="300",
        maximum_fire_resistance="75",
        equipped_state="equipped",
        equipment_inclusion_state="unknown",
        measurement_context=_complete_context(),
        target_game_version_acknowledgement="confirmed-3.29.1",
        observed_item_reference=ReviewSourceLocator("copied-text", copied_id),
        target="200",
    )
    result = service.enmity_result()
    if (
        not result.available
        or result.label != ENMITY_OUTPUT_LABEL
        or result.overcap != 225
        or result.value != 200
        or result.inputBeyondCap != 25
    ):
        raise AssertionError(f"unexpected isolated Enmity result: {result.to_dict()}")
    if (
        result.target.state != "available"
        or result.target.gap != 0
        or result.target.surplus != 0
        or result.target.capHeadroom != 0
    ):
        raise AssertionError(f"unexpected Enmity-only target result: {result.target}")

    if service.flame_link_table_status()["state"] != "available":
        raise AssertionError("Flame Link level table failed to load")
    chain = service.state["flameLinkPlayerChain"]
    for entry in chain["conditionalContributions"]:
        entry["conditionState"] = "inactive"
    chain["flameLinkLevel"]["additionalLinkGemLevels"][0]["activeState"] = "active"
    service.set_flame_link_input(
        golden_glory={
            "allocatedState": "allocated",
            "mercenaryTargetState": "yes",
            "reviewedLightRadiusPct": "40",
            "provenanceKind": "manual-reviewed",
            "reviewState": "reviewed",
            "rawSourceText": "40% increased Light Radius",
            "recognitionSource": {"kind": "none", "digest": None},
        },
        direct_link_buff_effect={
            "reviewedDirectPct": "0",
            "provenanceKind": "manual-reviewed",
            "reviewState": "reviewed",
            "rawSourceText": "",
            "recognitionSource": {"kind": "none", "digest": None},
        },
        conditional_contributions=chain["conditionalContributions"],
        flame_link_level=chain["flameLinkLevel"],
        luminary_maximum_life={
            "reviewedLife": "5000",
            "provenanceKind": "manual-reviewed",
            "reviewState": "reviewed",
            "rawSourceText": "",
            "recognitionSource": {"kind": "none", "digest": None},
        },
    )
    flame = service.flame_link_result()
    if (
        not flame.available
        or flame.label != FLAME_LINK_OUTPUT_LABEL
        or flame.effectiveFlameLinkLevel != 23
        or "DPS" in flame.label
        or "dps" in flame.label.lower()
    ):
        raise AssertionError(f"unexpected Flame Link result: {flame.to_dict()}")

    with tempfile.TemporaryDirectory(prefix="ggl-build-self-test-") as temporary:
        state_path = Path(temporary) / "state.ggl.json"
        first_bytes = service.save(state_path)
        reopened = ApplicationService()
        reopened.open(state_path)
        second_bytes = reopened.save()
        if first_bytes != second_bytes or second_bytes != serialize(reopened.state):
            raise AssertionError("saved and reopened canonical v3 bytes differ")

    state = reopened.state
    imported = state["importedResult"]
    if imported_result_digest(imported) != state["importedResultSha256"]:
        raise AssertionError("imported-result digest verification failed")
    if state["playerItemSetOccurrenceId"] != "item-set-0001":
        raise AssertionError("explicit player mapping did not survive")
    if state["mercenaryItemSetOccurrenceId"] != "item-set-0002":
        raise AssertionError("explicit Mercenary mapping did not survive")
    if state["manualMercenaryEquipment"][0]["reviewState"] != "unparsed-manual":
        raise AssertionError("manual entry review state did not survive")
    if state["schemaVersion"] != "3.0.0":
        raise AssertionError("canonical schema version is not 3.0.0")
    reopened_copied = reopened.review_for_locator(
        ReviewSourceLocator("copied-text", copied_id)
    )
    if reopened_copied is None or reopened_copied.exactRawText != copied_raw:
        raise AssertionError("recomputed copied-item review lost exact raw text")
    reopened_result = reopened.enmity_result()
    if reopened_result.to_dict() != result.to_dict():
        raise AssertionError("recomputed Enmity result changed after reopen")
    reopened_flame = reopened.flame_link_result()
    if reopened_flame.to_dict() != flame.to_dict():
        raise AssertionError("recomputed Flame Link result changed after reopen")

    mechanics = reopened.mechanics_status()
    expected_blocked = {
        "derived-permanent-mercenary-sheet-values",
        "live-game-flame-link-rounding",
        "powerful-bond-auto-activation",
        "exhaustive-player-chain-recognition",
        "sheet-derived-or-aggregate-enmity",
        "total-penetration",
        "damage-and-dps",
    }
    if {entry["id"] for entry in mechanics} != expected_blocked:
        raise AssertionError("blocked output inventory changed")
    if any(entry["value"] is not None for entry in mechanics):
        raise AssertionError("a prohibited output became numeric")
    if any(entry["status"] != "unavailable-pending-evidence" for entry in mechanics):
        raise AssertionError("blocked mechanics availability state changed")

    keys = _all_keys(state)
    invented_owner_keys = [key for key in keys if "owner" in key.lower()]
    derived_output_keys = {
        "capHeadroom",
        "gateDecision",
        "inputBeyondCap",
        "overcap",
        "recognitionReports",
        "recognitionState",
        "reviewInstanceId",
        "targetComparison",
        "modelledIntegerMin",
        "exactPreRoundMin",
    }
    persisted_derived_keys = sorted(derived_output_keys.intersection(keys))
    prohibited_names = {
        "combinedscore",
        "damagepersecond",
        "dps",
        "flamelinkdamage",
        "goldenglorycontribution",
        "lightradiuscalculation",
        "resistancecalculation",
        "totalfirepenetration",
    }
    invented_mechanics_keys = [key for key in keys if key.lower() in prohibited_names]
    if invented_owner_keys or persisted_derived_keys or invented_mechanics_keys:
        raise AssertionError(
            "invented/persisted fields: "
            f"owner={invented_owner_keys}, derived={persisted_derived_keys}, "
            f"mechanics={invented_mechanics_keys}"
        )

    return {
        "selfTestVersion": SELF_TEST_VERSION,
        "state": "PASS",
        "runtime": {
            "pythonVersion": platform.python_version(),
            "expatVersion": str(expat.EXPAT_VERSION),
            "zlibVersion": zlib.ZLIB_RUNTIME_VERSION,
            **tkinter_runtime,
        },
        "workflow": {
            "importedItemSetOccurrences": occurrences,
            "playerMapping": "item-set-0001",
            "mercenaryMapping": "item-set-0002",
            "manualEntryCount": 1,
            "copiedEntryCount": 1,
            "commonReviewCount": len(reviews),
            "commonReviewProvenanceCounts": provenance_counts,
            "copiedRawTextSha256": copied_review.rawTextSha256,
            "copiedRawTextPreserved": True,
            "enmityReferenceRecognized": True,
            "ownerInferred": False,
            "equippedStateInferredByRecognition": False,
            "runtimeManifestSha256": evidence["manifest"]["byteSha256"],
            "runtimeEvidenceGatesVerified": True,
            "enmityOvercap": reopened_result.overcap,
            "enmityOwnContribution": reopened_result.value,
            "enmityInputBeyondCap": reopened_result.inputBeyondCap,
            "enmityTargetState": reopened_result.target.state,
            "flameLinkEffectiveLevel": reopened_flame.effectiveFlameLinkLevel,
            "flameLinkModelledMin": reopened_flame.modelledIntegerMin,
            "flameLinkModelledMax": reopened_flame.modelledIntegerMax,
            "stateSha256": hashlib.sha256(second_bytes).hexdigest(),
            "deterministicV3SaveReopen": True,
            "importedResultDigestVerified": True,
            "prohibitedOutputsUnavailable": sorted(expected_blocked),
            "noOwnershipFieldInvented": True,
            "noDerivedOutputPersisted": True,
        },
    }


def run_self_test(output_path: Path) -> int:
    try:
        result = build_self_test_result()
    except Exception as error:
        result = {
            "selfTestVersion": SELF_TEST_VERSION,
            "state": "FAIL",
            "failureCode": f"SELF_TEST_FAILURE:{type(error).__name__}",
            "message": str(error),
        }
    output_path.write_bytes(_canonical_json_bytes(result))
    return 0 if result["state"] == "PASS" else 1
