"""Generate deterministic BUILD-001 canonical build-state fixtures.

Inputs are permanent synthetic PoB proof fixtures in this repository. The
script performs no network access and emits a review report for every target.
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

from golden_glory_lab.build_state import (  # noqa: E402
    empty_document,
    imported_result_digest,
    serialize,
)
from golden_glory_lab.pob_import import importPobRawXml  # noqa: E402

SOURCE = ROOT / "fixtures" / "pob" / "proof"
OUTPUT = ROOT / "fixtures" / "build_state"


def _import(name: str) -> dict[str, Any]:
    text = (SOURCE / name).read_text(encoding="utf-8")
    result = importPobRawXml(text)
    if result["status"] != "success":
        raise AssertionError(f"fixture import failed: {name}: {result['failure']}")
    return result


def _with_import(name: str) -> dict[str, Any]:
    document = empty_document()
    result = _import(name)
    document["importedResult"] = result
    document["importedResultSha256"] = imported_result_digest(result)
    return document


def _documents() -> dict[str, dict[str, Any]]:
    imported = _with_import("equivalent.xml")
    mapped = _with_import("reimport-before.xml")
    mapped["playerItemSetOccurrenceId"] = "item-set-0001"
    mapped["mercenarySourceMode"] = "mapped-item-set"
    mapped["mercenaryItemSetOccurrenceId"] = "item-set-0002"
    manual = _with_import("equivalent.xml")
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
        "empty.build-state-v1.json": empty_document(),
        "imported.build-state-v1.json": imported,
        "mapped.build-state-v1.json": mapped,
        "manual.build-state-v1.json": manual,
    }


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
    expected = {name: serialize(value) for name, value in _documents().items()}
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
