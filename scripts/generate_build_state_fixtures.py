"""Generate deterministic BUILD-001/002/003 state fixtures.

Inputs are permanent synthetic PoB proof and copied-item fixtures in this
repository. The script performs no network access and reports every target.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from golden_glory_lab.build_state.codec import (  # noqa: E402
    empty_document as empty_v1_document,
    imported_result_digest,
    serialize as serialize_v1,
)
from golden_glory_lab.build_state.codec_v2 import (  # noqa: E402
    empty_document as empty_v2_document,
    migrate_v1_document as migrate_v1_to_v2,
    serialize as serialize_v2,
)
from golden_glory_lab.build_state.codec_v3 import (  # noqa: E402
    empty_document as empty_v3_document,
    empty_flame_link_player_chain,
    migrate_v2_document as migrate_v2_to_v3,
    serialize as serialize_v3,
)
from golden_glory_lab.pob_import import importPobRawXml  # noqa: E402

SOURCE = ROOT / "fixtures" / "pob" / "proof"
COPIED_SOURCE = ROOT / "fixtures" / "item_review" / "copied-items-v1.json"
OUTPUT = ROOT / "fixtures" / "build_state"


def _import(name: str) -> dict[str, Any]:
    text = (SOURCE / name).read_text(encoding="utf-8")
    result = importPobRawXml(text)
    if result["status"] != "success":
        raise AssertionError(f"fixture import failed: {name}: {result['failure']}")
    return result


def _with_v1_import(name: str) -> dict[str, Any]:
    document = empty_v1_document()
    result = _import(name)
    document["importedResult"] = result
    document["importedResultSha256"] = imported_result_digest(result)
    return document


def _v1_documents() -> dict[str, dict[str, Any]]:
    imported = _with_v1_import("equivalent.xml")
    mapped = _with_v1_import("reimport-before.xml")
    mapped["playerItemSetOccurrenceId"] = "item-set-0001"
    mapped["mercenarySourceMode"] = "mapped-item-set"
    mapped["mercenaryItemSetOccurrenceId"] = "item-set-0002"
    manual = _with_v1_import("equivalent.xml")
    manual["playerItemSetOccurrenceId"] = "item-set-0001"
    manual["mercenarySourceMode"] = "manual-equipment"
    manual["manualMercenaryEquipment"] = [
        {
            "entryId": "manual-0001",
            "slotLabel": "Ring 1",
            "rawText": "Synthetic opaque +999% observed equipment text",
            "reviewState": "unparsed-manual",
            "note": "Fixture material only; no modifier interpretation.",
        }
    ]
    return {
        "empty.build-state-v1.json": empty_v1_document(),
        "imported.build-state-v1.json": imported,
        "mapped.build-state-v1.json": mapped,
        "manual.build-state-v1.json": manual,
    }


def _copied_enmity_v2() -> dict[str, Any]:
    copied = json.loads(COPIED_SOURCE.read_text(encoding="utf-8"))
    raw_text = next(
        case["rawText"]
        for case in copied["cases"]
        if case["id"] == "recognizable-enmity-crlf"
    )
    document = empty_v2_document()
    document["copiedItemEntries"] = [
        {
            "entryId": "copied-0001",
            "rawText": raw_text,
            "role": "mercenary",
            "slotLabel": "Ring 1",
            "userLabel": "Synthetic observed Enmity",
            "note": "Fixture material only; explicit role is user metadata.",
        }
    ]
    document["enmityManualInput"] = {
        "finalUncappedFireResistance": "0300.00",
        "maximumFireResistance": "075.0",
        "equippedState": "equipped",
        "equipmentInclusionState": "unknown",
        "measurementContext": {
            "mercenaryIdentityLevel": "Synthetic permanent Mercenary, level 90",
            "activeStateSelection": "Active combat state recorded",
            "zoneOrUiContext": "Hideout character UI",
            "relevantEffectsConditions": "No temporary resistance effects",
            "equipmentStateDescription": "Enmity equipped in Ring 1",
            "captureTimingDescription": "Captured after UI refresh",
        },
        "targetGameVersionAcknowledgement": "confirmed-3.29.1",
        "observedItemReference": {
            "provenanceKind": "copied-text",
            "sourceId": "copied-0001",
        },
        "target": "200.0",
    }
    document["userNotes"] = "Synthetic BUILD-002 v2 fixture."
    return document


def _flame_link_v3() -> dict[str, Any]:
    document = empty_v3_document()
    chain = empty_flame_link_player_chain()
    chain["goldenGlory"].update(
        {
            "allocatedState": "allocated",
            "mercenaryTargetState": "yes",
            "reviewedLightRadiusPct": "40",
            "provenanceKind": "manual-reviewed",
            "reviewState": "reviewed",
            "rawSourceText": "40% increased Light Radius",
        }
    )
    chain["directLinkBuffEffect"].update(
        {
            "reviewedDirectPct": "15",
            "provenanceKind": "manual-reviewed",
            "reviewState": "reviewed",
            "rawSourceText": "15% increased Effect of your Link Skills",
        }
    )
    for entry in chain["conditionalContributions"]:
        if entry["contributionId"] in {"powerful-bond", "inspiring-bond"}:
            entry["conditionState"] = "inactive"
    chain["flameLinkLevel"]["additionalLinkGemLevels"][0]["activeState"] = "active"
    chain["luminaryMaximumLife"].update(
        {
            "reviewedLife": "5000",
            "provenanceKind": "manual-reviewed",
            "reviewState": "reviewed",
            "rawSourceText": "Maximum Life 5000",
        }
    )
    document["flameLinkPlayerChain"] = chain
    document["userNotes"] = "Synthetic BUILD-003 Flame Link player-chain fixture."
    return document


def _documents() -> dict[str, tuple[dict[str, Any], Any]]:
    v1 = _v1_documents()
    expected: dict[str, tuple[dict[str, Any], Any]] = {
        name: (document, serialize_v1) for name, document in v1.items()
    }
    expected["empty-migrated.build-state-v2.json"] = (
        migrate_v1_to_v2(v1["empty.build-state-v1.json"]),
        serialize_v2,
    )
    expected["copied-enmity.build-state-v2.json"] = (
        _copied_enmity_v2(),
        serialize_v2,
    )
    expected["empty-migrated.build-state-v3.json"] = (
        migrate_v2_to_v3(migrate_v1_to_v2(v1["empty.build-state-v1.json"])),
        serialize_v3,
    )
    expected["flame-link.build-state-v3.json"] = (
        _flame_link_v3(),
        serialize_v3,
    )
    return expected


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write changed fixture bytes. Without this flag, differences fail.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    expected = {
        name: serializer(document)
        for name, (document, serializer) in _documents().items()
    }
    report: dict[str, Any] = {
        "addedRecords": [],
        "removedRecords": [],
        "changedValues": [],
        "changedAvailability": [],
        "unchangedRecords": [],
        "recordsRequiringHumanReview": [],
        "artifacts": {},
    }
    for name, data in expected.items():
        path = OUTPUT / name
        prior = path.read_bytes() if path.is_file() else None
        if prior is None:
            report["addedRecords"].append(name)
            report["recordsRequiringHumanReview"].append(name)
        elif prior != data:
            report["changedValues"].append(name)
            report["recordsRequiringHumanReview"].append(name)
        else:
            report["unchangedRecords"].append(name)
        if args.write and prior != data:
            path.write_bytes(data)
        report["artifacts"][name] = {
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
    unexpected = sorted(
        path.name for path in OUTPUT.glob("*.json") if path.name not in expected
    )
    report["removedRecords"] = unexpected
    report["recordsRequiringHumanReview"].extend(unexpected)
    print(json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True))
    changed = bool(
        report["addedRecords"]
        or report["changedValues"]
        or report["removedRecords"]
    )
    if changed and not args.write:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
