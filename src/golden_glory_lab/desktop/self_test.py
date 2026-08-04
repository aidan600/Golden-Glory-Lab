"""Noninteractive packaged BUILD-001 self-test."""

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

from .service import ApplicationService

SELF_TEST_VERSION = "1.0.0"


def _fixture_path() -> Path:
    bundle_root = getattr(sys, "_MEIPASS", None)
    if isinstance(bundle_root, str):
        return (
            Path(bundle_root)
            / "ggl_app_resources"
            / "pob"
            / "proof"
            / "comprehensive.xml"
        )
    return (
        Path(__file__).resolve().parents[3]
        / "fixtures"
        / "pob"
        / "proof"
        / "comprehensive.xml"
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


def build_self_test_result() -> dict[str, Any]:
    tkinter_runtime = _tk_runtime()
    fixture = _fixture_path()
    service = ApplicationService()
    outcome = service.attempt_raw_xml(fixture)
    if outcome != "imported":
        raise AssertionError(f"permanent fixture import failed: {outcome}")
    item_sets = service.item_sets()
    occurrences = [entry["occurrenceId"] for entry in item_sets]
    if occurrences != ["item-set-0001", "item-set-0002", "item-set-0003"]:
        raise AssertionError(f"unexpected item-set occurrences: {occurrences}")
    service.set_player_mapping("item-set-0001")
    service.set_mercenary_source("manual-equipment")
    service.add_manual_entry(
        "Ring 1",
        "Synthetic opaque +999% observed text",
        "Self-test material; deliberately unparsed.",
        entry_id="manual-0001",
    )

    with tempfile.TemporaryDirectory(prefix="ggl-build-self-test-") as temporary:
        state_path = Path(temporary) / "state.ggl.json"
        first_bytes = service.save(state_path)
        reopened = ApplicationService()
        reopened.open(state_path)
        second_bytes = reopened.save()
        if first_bytes != second_bytes or second_bytes != serialize(reopened.state):
            raise AssertionError("saved and reopened canonical bytes differ")

    state = reopened.state
    imported = state["importedResult"]
    if imported_result_digest(imported) != state["importedResultSha256"]:
        raise AssertionError("imported-result digest verification failed")
    if state["playerItemSetOccurrenceId"] != "item-set-0001":
        raise AssertionError("explicit player mapping did not survive")
    if state["mercenaryItemSetOccurrenceId"] is not None:
        raise AssertionError("manual Mercenary mode invented an occurrence mapping")
    if state["manualMercenaryEquipment"][0]["reviewState"] != "unparsed-manual":
        raise AssertionError("manual entry review state did not survive")

    mechanics = reopened.mechanics_status()
    if not mechanics or any(entry["value"] is not None for entry in mechanics):
        raise AssertionError("evidence-gated mechanics became numeric")
    if any(entry["status"] != "unavailable-pending-evidence" for entry in mechanics):
        raise AssertionError("mechanics availability state changed")

    keys = _all_keys(state)
    invented_owner_keys = [key for key in keys if "owner" in key.lower()]
    prohibited = {
        "combinedscore",
        "damagepersecond",
        "dps",
        "enmitycalculation",
        "firepenetration",
        "flamelinkdamage",
        "goldenglorycontribution",
        "lightradiuscalculation",
        "resistancecalculation",
    }
    invented_mechanics_keys = [key for key in keys if key.lower() in prohibited]
    if invented_owner_keys or invented_mechanics_keys:
        raise AssertionError(
            f"invented fields: owner={invented_owner_keys}, mechanics={invented_mechanics_keys}"
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
            "mercenarySourceMode": "manual-equipment",
            "manualEntryCount": 1,
            "stateSha256": hashlib.sha256(second_bytes).hexdigest(),
            "deterministicSaveReopen": True,
            "importedResultDigestVerified": True,
            "mechanicsUnavailableCount": len(mechanics),
            "noOwnershipFieldInvented": True,
            "noMechanicsFieldInvented": True,
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
