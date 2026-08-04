"""Testable BUILD-001 application service and derived session state."""

from __future__ import annotations

import copy
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from golden_glory_lab.build_state import (
    BuildStateError,
    atomic_save,
    empty_document,
    imported_result_digest,
    load_file,
    serialize,
    validate_document,
)

from .evidence import MECHANICS_STATUS, mechanics_availability
from .intake import DesktopIntakeError, import_raw_xml_file, import_share_code_text

_MANUAL_ID_RE = re.compile(r"^manual-(\d{4,})$")


class ApplicationService:
    """Own canonical content and transient session state, never widgets."""

    def __init__(self) -> None:
        self._state = empty_document()
        self.current_path: Path | None = None
        self._saved_canonical_bytes = serialize(self._state)
        self.last_failed_import: dict[str, Any] | None = None
        self.pending_import_result: dict[str, Any] | None = None

    @property
    def state(self) -> dict[str, Any]:
        return copy.deepcopy(self._state)

    @property
    def canonical_bytes(self) -> bytes:
        return serialize(self._state)

    @property
    def dirty(self) -> bool:
        return self.canonical_bytes != self._saved_canonical_bytes

    @property
    def file_state(self) -> str:
        if self.current_path is None:
            return "unsaved"
        return "modified" if self.dirty else "saved"

    def _commit(self, candidate: dict[str, Any]) -> None:
        validate_document(candidate)
        self._state = copy.deepcopy(candidate)

    def new_document(self) -> None:
        state = empty_document()
        self._state = state
        self.current_path = None
        self._saved_canonical_bytes = serialize(state)
        self.last_failed_import = None
        self.pending_import_result = None

    def _record_import_failure(self, result: dict[str, Any]) -> str:
        failure = result.get("failure") or {}
        self.last_failed_import = {
            "kind": "importer-failure",
            "code": failure.get("code", "IMPORT_FAILED"),
            "stage": failure.get("stage", "unknown"),
            "message": failure.get("message", "The importer rejected the input"),
            "report": copy.deepcopy(result.get("report", [])),
        }
        self.pending_import_result = None
        return "failed"

    def _stage_success(self, result: dict[str, Any]) -> str:
        if result.get("status") != "success":
            return self._record_import_failure(result)
        self.last_failed_import = None
        if self._state["importedResult"] is not None:
            self.pending_import_result = copy.deepcopy(result)
            return "confirmation-required"
        self.pending_import_result = copy.deepcopy(result)
        return self.confirm_pending_import(True)

    def attempt_raw_xml(
        self,
        path_value: str | Path,
        *,
        importer: Callable[[str], dict[str, Any]] | None = None,
    ) -> str:
        try:
            result = (
                import_raw_xml_file(path_value)
                if importer is None
                else import_raw_xml_file(path_value, importer=importer)
            )
        except DesktopIntakeError as error:
            self.last_failed_import = error.as_attempt()
            self.pending_import_result = None
            return "failed"
        return self._stage_success(result)

    def attempt_share_code(
        self,
        value: str,
        *,
        importer: Callable[[str], dict[str, Any]] | None = None,
    ) -> str:
        try:
            result = (
                import_share_code_text(value)
                if importer is None
                else import_share_code_text(value, importer=importer)
            )
        except DesktopIntakeError as error:
            self.last_failed_import = error.as_attempt()
            self.pending_import_result = None
            return "failed"
        return self._stage_success(result)

    def confirm_pending_import(self, confirmed: bool) -> str:
        if self.pending_import_result is None:
            raise BuildStateError("NO_PENDING_IMPORT", "No staged import is available")
        if not confirmed:
            self.pending_import_result = None
            return "canceled"
        result = self.pending_import_result
        candidate = self.state
        replacing = candidate["importedResult"] is not None
        candidate["importedResult"] = result
        candidate["importedResultSha256"] = imported_result_digest(result)
        candidate["playerItemSetOccurrenceId"] = None
        candidate["mercenarySourceMode"] = "not-yet-selected"
        candidate["mercenaryItemSetOccurrenceId"] = None
        self._commit(candidate)
        self.pending_import_result = None
        return "replaced" if replacing else "imported"

    def set_player_mapping(self, occurrence_id: str | None) -> None:
        candidate = self.state
        candidate["playerItemSetOccurrenceId"] = occurrence_id
        self._commit(candidate)

    def set_mercenary_source(
        self, mode: str, occurrence_id: str | None = None
    ) -> None:
        candidate = self.state
        candidate["mercenarySourceMode"] = mode
        candidate["mercenaryItemSetOccurrenceId"] = (
            occurrence_id if mode == "mapped-item-set" else None
        )
        self._commit(candidate)

    def _next_manual_entry_id(self) -> str:
        maximum = 0
        for entry in self._state["manualMercenaryEquipment"]:
            match = _MANUAL_ID_RE.fullmatch(entry["entryId"])
            if match:
                maximum = max(maximum, int(match.group(1)))
        return f"manual-{maximum + 1:04d}"

    def add_manual_entry(
        self,
        slot_label: str,
        raw_text: str,
        note: str = "",
        *,
        entry_id: str | None = None,
    ) -> str:
        if self._state["mercenarySourceMode"] != "manual-equipment":
            raise BuildStateError(
                "MANUAL_MODE_REQUIRED",
                "Select manual-equipment mode before adding an entry",
            )
        identifier = entry_id or self._next_manual_entry_id()
        candidate = self.state
        candidate["manualMercenaryEquipment"].append(
            {
                "entryId": identifier,
                "slotLabel": slot_label,
                "rawText": raw_text,
                "reviewState": "unparsed-manual",
                "note": note,
            }
        )
        self._commit(candidate)
        return identifier

    def edit_manual_entry(
        self, entry_id: str, slot_label: str, raw_text: str, note: str = ""
    ) -> None:
        if self._state["mercenarySourceMode"] != "manual-equipment":
            raise BuildStateError(
                "MANUAL_MODE_REQUIRED",
                "Select manual-equipment mode before editing an entry",
            )
        candidate = self.state
        for entry in candidate["manualMercenaryEquipment"]:
            if entry["entryId"] == entry_id:
                entry["slotLabel"] = slot_label
                entry["rawText"] = raw_text
                entry["note"] = note
                self._commit(candidate)
                return
        raise BuildStateError("MANUAL_ENTRY_MISSING", f"Unknown manual entry {entry_id}")

    def delete_manual_entry(self, entry_id: str, *, confirmed: bool) -> bool:
        if not confirmed:
            return False
        candidate = self.state
        retained = [
            entry
            for entry in candidate["manualMercenaryEquipment"]
            if entry["entryId"] != entry_id
        ]
        if len(retained) == len(candidate["manualMercenaryEquipment"]):
            raise BuildStateError("MANUAL_ENTRY_MISSING", f"Unknown manual entry {entry_id}")
        candidate["manualMercenaryEquipment"] = retained
        self._commit(candidate)
        return True

    def set_user_notes(self, notes: str) -> None:
        candidate = self.state
        candidate["userNotes"] = notes
        self._commit(candidate)

    def save(self, path_value: str | Path | None = None) -> bytes:
        destination = Path(path_value) if path_value is not None else self.current_path
        if destination is None:
            raise BuildStateError("SAVE_PATH_REQUIRED", "Save As is required")
        saved = atomic_save(destination, self._state)
        self.current_path = destination.resolve()
        self._saved_canonical_bytes = saved
        return saved

    def open(self, path_value: str | Path) -> None:
        path = Path(path_value)
        loaded, _raw_bytes = load_file(path)
        canonical = serialize(loaded)
        self._state = loaded
        self.current_path = path.resolve()
        self._saved_canonical_bytes = canonical
        self.last_failed_import = None
        self.pending_import_result = None

    def item_sets(self) -> list[dict[str, Any]]:
        imported = self._state["importedResult"]
        if imported is None:
            return []
        return copy.deepcopy(imported["document"]["itemSets"])

    def imported_items(self) -> list[dict[str, Any]]:
        imported = self._state["importedResult"]
        if imported is None:
            return []
        return copy.deepcopy(imported["document"]["items"])

    def importer_report(self) -> list[dict[str, Any]]:
        imported = self._state["importedResult"]
        if imported is None:
            return []
        return copy.deepcopy(imported["report"])

    def readiness(self) -> dict[str, Any]:
        imported = self._state["importedResult"] is not None
        player = self._state["playerItemSetOccurrenceId"] is not None
        mode = self._state["mercenarySourceMode"]
        mercenary_ready = mode == "manual-equipment" or (
            mode == "mapped-item-set"
            and self._state["mercenaryItemSetOccurrenceId"] is not None
        )
        return {
            "import": "imported" if imported else "missing",
            "playerMapping": "explicit" if player else "missing",
            "mercenarySourceMode": mode,
            "intakeReady": bool(imported and player and mercenary_ready),
        }

    def importer_warning_state(self) -> str:
        review_categories = {"unrecognized", "ambiguous", "malformed"}
        return (
            "review-required"
            if any(
                entry.get("category") in review_categories
                for entry in self.importer_report()
            )
            else "none"
        )

    def status_summary(self) -> dict[str, Any]:
        readiness = self.readiness()
        return {
            **readiness,
            "localFileState": self.file_state,
            "importerWarnings": self.importer_warning_state(),
            "mechanics": MECHANICS_STATUS,
        }

    def mechanics_status(self) -> list[dict[str, Any]]:
        return mechanics_availability()
