"""Testable BUILD-003 application service and derived session state."""

from __future__ import annotations

import copy
import re
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from golden_glory_lab.build_state import (
    BuildStateError,
    atomic_save,
    empty_document,
    imported_result_digest,
    load_file_result,
    serialize,
    validate_document,
)
from golden_glory_lab.domain import (
    ENMITY_OUTPUT_ID,
    ENMITY_TARGET_OUTPUT_ID,
    EnmityResult,
    FlameLinkLevelTable,
    FlameLinkResult,
    FlameLinkTableError,
    RecognizedPlayerChainLine,
    evaluate_enmity,
    evaluate_flame_link,
    load_flame_link_level_table,
    recognize_player_chain_text,
)
from golden_glory_lab.evidence_gate import (
    GateDecision,
    GateReason,
    RuntimeResourceError,
    evaluate_output,
    load_runtime_bundle,
)
from golden_glory_lab.item_review import (
    ItemReview,
    ReviewSourceLocator,
    derive_item_reviews,
)

from .evidence import MECHANICS_STATUS, mechanics_availability
from .intake import DesktopIntakeError, import_raw_xml_file, import_share_code_text

_MANUAL_ID_RE = re.compile(r"^manual-(\d{4,})$")
_COPIED_ID_RE = re.compile(r"^copied-(\d{4,})$")
_UNSET = object()


class ApplicationService:
    """Own canonical content and transient session state, never widgets."""

    def __init__(self) -> None:
        self._state = empty_document()
        self.current_path: Path | None = None
        self._saved_canonical_bytes = serialize(self._state)
        self._migration_pending = False
        self.last_failed_import: dict[str, Any] | None = None
        self.pending_import_result: dict[str, Any] | None = None
        self._gate_manifest = None
        self._enmity_reference: dict[str, Any] | None = None
        self._runtime_resource_error: dict[str, str] | None = None
        self._flame_link_table: FlameLinkLevelTable | None = None
        self._flame_link_table_error: dict[str, str] | None = None
        self._load_runtime_resources()

    def _load_runtime_resources(self) -> None:
        """Load only packaged resources and fail closed at dependent outputs."""

        try:
            manifest, reference = load_runtime_bundle()
        except RuntimeResourceError as error:
            self._gate_manifest = None
            self._enmity_reference = None
            self._runtime_resource_error = {
                "code": error.code,
                "message": error.message,
            }
        else:
            self._gate_manifest = manifest
            self._enmity_reference = reference
            self._runtime_resource_error = None
        try:
            self._flame_link_table = load_flame_link_level_table()
            self._flame_link_table_error = None
        except FlameLinkTableError as error:
            self._flame_link_table = None
            self._flame_link_table_error = {
                "code": error.code,
                "message": error.message,
            }

    @property
    def state(self) -> dict[str, Any]:
        return copy.deepcopy(self._state)

    @property
    def canonical_bytes(self) -> bytes:
        return serialize(self._state)

    @property
    def migration_pending(self) -> bool:
        return self._migration_pending

    @property
    def dirty(self) -> bool:
        return (
            self._migration_pending
            or self.canonical_bytes != self._saved_canonical_bytes
        )

    @property
    def file_state(self) -> str:
        if self._migration_pending:
            return "upgrade-pending"
        if self.current_path is None:
            return "unsaved"
        return "modified" if self.dirty else "saved"

    def _commit(self, candidate: dict[str, Any]) -> None:
        validate_document(candidate)
        try:
            self._state = copy.deepcopy(candidate)
        except RecursionError as error:
            raise BuildStateError(
                "COMMIT_STATE_NESTING",
                "Canonical build-state commit exceeds safe copy nesting limits",
            ) from error

    def new_document(self) -> None:
        state = empty_document()
        self._state = state
        self.current_path = None
        self._saved_canonical_bytes = serialize(state)
        self._migration_pending = False
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

    def _observed_locator(self) -> ReviewSourceLocator | None:
        value = self._state["enmityManualInput"]["observedItemReference"]
        if value is None:
            return None
        return ReviewSourceLocator.from_dict(value)

    def _reference_matches(self, provenance_kind: str, source_id: str) -> bool:
        locator = self._observed_locator()
        return locator == ReviewSourceLocator(provenance_kind, source_id)

    def confirm_pending_import(
        self,
        confirmed: bool,
        *,
        clear_observed_reference: bool = False,
    ) -> str:
        if self.pending_import_result is None:
            raise BuildStateError("NO_PENDING_IMPORT", "No staged import is available")
        if not confirmed:
            self.pending_import_result = None
            return "canceled"
        result = self.pending_import_result
        candidate = self.state
        replacing = candidate["importedResult"] is not None
        locator = self._observed_locator()
        if replacing and locator is not None and locator.provenanceKind == "pob-import":
            if not clear_observed_reference:
                raise BuildStateError(
                    "OBSERVED_REFERENCE_CLEAR_CONFIRMATION_REQUIRED",
                    "Replacing the PoB source requires confirmation to clear its observed-item reference",
                )
            candidate["enmityManualInput"]["observedItemReference"] = None
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

    @staticmethod
    def _next_identifier(
        entries: list[dict[str, Any]], pattern: re.Pattern[str], prefix: str
    ) -> str:
        maximum = 0
        for entry in entries:
            match = pattern.fullmatch(entry["entryId"])
            if match:
                maximum = max(maximum, int(match.group(1)))
        return f"{prefix}-{maximum + 1:04d}"

    def _next_manual_entry_id(self) -> str:
        return self._next_identifier(
            self._state["manualMercenaryEquipment"], _MANUAL_ID_RE, "manual"
        )

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

    def delete_manual_entry(
        self,
        entry_id: str,
        *,
        confirmed: bool,
        clear_observed_reference: bool = False,
    ) -> bool:
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
        if self._reference_matches("manual-entry", entry_id):
            if not clear_observed_reference:
                raise BuildStateError(
                    "OBSERVED_REFERENCE_CLEAR_CONFIRMATION_REQUIRED",
                    "Deleting this manual source requires confirmation to clear its observed-item reference",
                )
            candidate["enmityManualInput"]["observedItemReference"] = None
        candidate["manualMercenaryEquipment"] = retained
        self._commit(candidate)
        return True

    def _next_copied_entry_id(self) -> str:
        return self._next_identifier(
            self._state["copiedItemEntries"], _COPIED_ID_RE, "copied"
        )

    def add_copied_entry(
        self,
        raw_text: str,
        *,
        role: str = "unassigned",
        slot_label: str = "",
        user_label: str = "",
        note: str = "",
        entry_id: str | None = None,
    ) -> str:
        identifier = entry_id or self._next_copied_entry_id()
        candidate = self.state
        candidate["copiedItemEntries"].append(
            {
                "entryId": identifier,
                "rawText": raw_text,
                "role": role,
                "slotLabel": slot_label,
                "userLabel": user_label,
                "note": note,
            }
        )
        self._commit(candidate)
        return identifier

    def edit_copied_entry(
        self,
        entry_id: str,
        *,
        role: str,
        slot_label: str = "",
        user_label: str = "",
        note: str = "",
    ) -> None:
        """Edit only explicit metadata; exact copied source text remains unchanged."""

        candidate = self.state
        for entry in candidate["copiedItemEntries"]:
            if entry["entryId"] == entry_id:
                entry["role"] = role
                entry["slotLabel"] = slot_label
                entry["userLabel"] = user_label
                entry["note"] = note
                self._commit(candidate)
                return
        raise BuildStateError("COPIED_ENTRY_MISSING", f"Unknown copied entry {entry_id}")

    def delete_copied_entry(
        self,
        entry_id: str,
        *,
        confirmed: bool,
        clear_observed_reference: bool = False,
    ) -> bool:
        if not confirmed:
            return False
        candidate = self.state
        retained = [
            entry
            for entry in candidate["copiedItemEntries"]
            if entry["entryId"] != entry_id
        ]
        if len(retained) == len(candidate["copiedItemEntries"]):
            raise BuildStateError("COPIED_ENTRY_MISSING", f"Unknown copied entry {entry_id}")
        if self._reference_matches("copied-text", entry_id):
            if not clear_observed_reference:
                raise BuildStateError(
                    "OBSERVED_REFERENCE_CLEAR_CONFIRMATION_REQUIRED",
                    "Deleting this copied source requires confirmation to clear its observed-item reference",
                )
            candidate["enmityManualInput"]["observedItemReference"] = None
        candidate["copiedItemEntries"] = retained
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
        self._migration_pending = False
        return saved

    def open(self, path_value: str | Path) -> None:
        """Replace the session only after bounded decode and full v3 migration."""

        path = Path(path_value)
        decoded, _raw_bytes = load_file_result(path)
        try:
            candidate = copy.deepcopy(decoded.document)
        except RecursionError as error:
            raise BuildStateError(
                "OPEN_STATE_NESTING",
                "Opened build-state exceeds safe copy nesting limits",
            ) from error
        validate_document(candidate)
        self._preflight_open_consumers(candidate)
        canonical = serialize(candidate)
        # Everything above may fail; no session member changes until this point.
        self._state = candidate
        self.current_path = path.resolve()
        self._saved_canonical_bytes = canonical
        self._migration_pending = decoded.migrated
        self.last_failed_import = None
        self.pending_import_result = None

    def _preflight_open_consumers(self, candidate: Mapping[str, Any]) -> None:
        """Prove BUILD-003 presentation consumers can derive from the candidate.

        Runtime evidence resources may be unavailable; that fails closed only for
        dependent Enmity outputs and must not reject an otherwise valid build.
        A missing Flame Link level table fails closed only for Flame Link output.
        """

        from golden_glory_lab.item_review import (
            CopiedItemRecognitionError,
            review_source_locators,
        )

        try:
            derive_item_reviews(
                candidate,
                enmity_reference=self._enmity_reference,
            )
            review_source_locators(candidate)
            evaluate_enmity(
                candidate["enmityManualInput"],
                self.gate_decisions()[ENMITY_OUTPUT_ID],
                self.gate_decisions()[ENMITY_TARGET_OUTPUT_ID],
            )
            if self._flame_link_table is not None:
                evaluate_flame_link(
                    candidate["flameLinkPlayerChain"],
                    self._flame_link_table,
                )
        except CopiedItemRecognitionError as error:
            raise BuildStateError(error.code, error.message) from error
        except UnicodeEncodeError as error:
            raise BuildStateError(
                "STRICT_UTF8_REQUIRED",
                f"Opened build-state review material is not strict UTF-8 "
                f"encodable at character {error.start}",
            ) from error
        except RecursionError as error:
            raise BuildStateError(
                "OPEN_REVIEW_NESTING",
                "Opened build-state exceeds safe review-derivation nesting limits",
            ) from error

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

    def item_reviews(
        self,
        *,
        provenance: str | None = None,
        role: str | None = None,
        recognition_state: str | None = None,
    ) -> list[ItemReview]:
        reviews = derive_item_reviews(
            self._state,
            enmity_reference=self._enmity_reference,
        )
        return [
            review
            for review in reviews
            if (provenance is None or review.provenanceKind == provenance)
            and (
                role is None
                or any(binding.role == role for binding in review.bindings)
            )
            and (
                recognition_state is None
                or review.recognitionState == recognition_state
            )
        ]

    def review_for_locator(
        self, locator: ReviewSourceLocator | Mapping[str, Any]
    ) -> ItemReview | None:
        resolved = (
            locator
            if isinstance(locator, ReviewSourceLocator)
            else ReviewSourceLocator.from_dict(dict(locator))
        )
        return next(
            (
                review
                for review in self.item_reviews()
                if review.sourceLocator == resolved
            ),
            None,
        )

    def set_enmity_input(
        self,
        *,
        final_uncapped_fire_resistance: str | None | object = _UNSET,
        maximum_fire_resistance: str | None | object = _UNSET,
        equipped_state: str | object = _UNSET,
        equipment_inclusion_state: str | object = _UNSET,
        measurement_context: Mapping[str, str] | object = _UNSET,
        target_game_version_acknowledgement: str | object = _UNSET,
        observed_item_reference: (
            ReviewSourceLocator | Mapping[str, Any] | None | object
        ) = _UNSET,
        target: str | None | object = _UNSET,
    ) -> None:
        """Atomically update canonical manual input; all decimals retain lexemes."""

        candidate = self.state
        value = candidate["enmityManualInput"]
        updates = (
            ("finalUncappedFireResistance", final_uncapped_fire_resistance),
            ("maximumFireResistance", maximum_fire_resistance),
            ("equippedState", equipped_state),
            ("equipmentInclusionState", equipment_inclusion_state),
            ("targetGameVersionAcknowledgement", target_game_version_acknowledgement),
            ("target", target),
        )
        for key, update in updates:
            if update is not _UNSET:
                value[key] = update
        if measurement_context is not _UNSET:
            value["measurementContext"] = dict(measurement_context)
        if observed_item_reference is not _UNSET:
            if observed_item_reference is None:
                value["observedItemReference"] = None
            elif isinstance(observed_item_reference, ReviewSourceLocator):
                value["observedItemReference"] = observed_item_reference.to_dict()
            else:
                value["observedItemReference"] = ReviewSourceLocator.from_dict(
                    dict(observed_item_reference)
                ).to_dict()
        self._commit(candidate)

    def _failed_runtime_gate(self, output_id: str) -> GateDecision:
        error = self._runtime_resource_error or {
            "code": "RUNTIME_RESOURCE_UNAVAILABLE",
            "message": "The packaged runtime evidence resource is unavailable",
        }
        reason = GateReason(
            code=error["code"],
            message=error["message"],
            outputId=output_id,
            unmetBehavior="withhold-requested-output",
        )
        return GateDecision(
            outputId=output_id,
            available=False,
            state="unavailable",
            value=None,
            reasons=(reason,),
            claimReferences=(),
        )

    def gate_decisions(self) -> dict[str, GateDecision]:
        output_ids = (ENMITY_OUTPUT_ID, ENMITY_TARGET_OUTPUT_ID)
        if self._gate_manifest is None:
            return {
                output_id: self._failed_runtime_gate(output_id)
                for output_id in output_ids
            }
        return {
            output_id: evaluate_output(self._gate_manifest, output_id)
            for output_id in output_ids
        }

    def runtime_evidence_status(self) -> dict[str, Any]:
        decisions = self.gate_decisions()
        if self._gate_manifest is None:
            return {
                "state": "unavailable",
                "resourceError": copy.deepcopy(self._runtime_resource_error),
                "manifest": None,
                "outputs": {
                    key: decision.to_dict() for key, decision in decisions.items()
                },
            }
        return {
            "state": "available",
            "resourceError": None,
            "manifest": {
                "manifestVersion": self._gate_manifest.manifestVersion,
                "targetGameVersion": self._gate_manifest.targetGameVersion,
                "byteSha256": self._gate_manifest.byteSha256,
                "sourceArtifacts": [
                    value.to_dict()
                    for value in self._gate_manifest.sourceArtifacts
                ],
                "claims": [value.to_dict() for value in self._gate_manifest.claims],
            },
            "outputs": {
                key: decision.to_dict() for key, decision in decisions.items()
            },
        }

    def enmity_result(self) -> EnmityResult:
        decisions = self.gate_decisions()
        return evaluate_enmity(
            self._state["enmityManualInput"],
            decisions[ENMITY_OUTPUT_ID],
            decisions[ENMITY_TARGET_OUTPUT_ID],
        )

    def flame_link_table_status(self) -> dict[str, Any]:
        if self._flame_link_table is None:
            return {
                "state": "unavailable",
                "resourceError": copy.deepcopy(self._flame_link_table_error),
            }
        return {
            "state": "available",
            "resourceError": None,
            "artifactId": self._flame_link_table.artifactId,
            "minimumLevel": self._flame_link_table.minimumLevel,
            "maximumLevel": self._flame_link_table.maximumLevel,
        }

    def set_flame_link_input(
        self,
        *,
        golden_glory: Mapping[str, Any] | object = _UNSET,
        direct_link_buff_effect: Mapping[str, Any] | object = _UNSET,
        conditional_contributions: Sequence[Mapping[str, Any]] | object = _UNSET,
        flame_link_level: Mapping[str, Any] | object = _UNSET,
        luminary_maximum_life: Mapping[str, Any] | object = _UNSET,
    ) -> None:
        """Atomically update canonical Flame Link player-chain input."""

        candidate = self.state
        chain = candidate["flameLinkPlayerChain"]
        if golden_glory is not _UNSET:
            chain["goldenGlory"] = dict(golden_glory)
        if direct_link_buff_effect is not _UNSET:
            chain["directLinkBuffEffect"] = dict(direct_link_buff_effect)
        if conditional_contributions is not _UNSET:
            chain["conditionalContributions"] = [
                dict(entry) for entry in conditional_contributions
            ]
        if flame_link_level is not _UNSET:
            level = dict(flame_link_level)
            level["additionalLinkGemLevels"] = [
                dict(entry) for entry in level.get("additionalLinkGemLevels", [])
            ]
            chain["flameLinkLevel"] = level
        if luminary_maximum_life is not _UNSET:
            chain["luminaryMaximumLife"] = dict(luminary_maximum_life)
        self._commit(candidate)

    def recognize_player_chain_from_text(
        self, raw_text: str
    ) -> tuple[RecognizedPlayerChainLine, ...]:
        return recognize_player_chain_text(raw_text)

    def recognize_player_chain_from_reviewed_sources(
        self,
    ) -> tuple[RecognizedPlayerChainLine, ...]:
        """Advisory recognition across current PoB/copied/manual item texts."""

        found: list[RecognizedPlayerChainLine] = []
        for review in self.item_reviews():
            found.extend(recognize_player_chain_text(review.exactRawText))
        return tuple(found)

    def apply_recognized_light_radius(
        self,
        signed_value_lexeme: str,
        *,
        raw_source_text: str = "",
        allocated_state: str = "allocated",
        mercenary_target_state: str = "yes",
    ) -> None:
        """Apply a user-confirmed Light Radius recognition into reviewed GG input."""

        self.set_flame_link_input(
            golden_glory={
                "allocatedState": allocated_state,
                "mercenaryTargetState": mercenary_target_state,
                "reviewedLightRadiusPct": signed_value_lexeme,
                "provenanceKind": "recognized-reviewed",
                "reviewState": "reviewed",
                "rawSourceText": raw_source_text,
            }
        )

    def apply_recognized_direct_link_buff_effect(
        self,
        signed_value_lexeme: str,
        *,
        raw_source_text: str = "",
    ) -> None:
        """Apply a user-confirmed direct Link Buff Effect recognition."""

        self.set_flame_link_input(
            direct_link_buff_effect={
                "reviewedDirectPct": signed_value_lexeme,
                "provenanceKind": "recognized-reviewed",
                "reviewState": "reviewed",
                "rawSourceText": raw_source_text,
            }
        )

    def flame_link_result(self) -> FlameLinkResult:
        if self._flame_link_table is None:
            error = self._flame_link_table_error or {
                "code": "FLAME_LINK_TABLE_MISSING",
                "message": "The packaged Flame Link level table is unavailable",
            }
            from golden_glory_lab.domain.flame_link import FlameLinkResult as Result

            return Result(
                outputId="flame-link-added-fire-damage-granted-v1",
                label="Added Fire Damage granted to linked Mercenary",
                targetGameVersion="Path of Exile 1 3.29.1",
                formulaVersionId="flame-link-player-chain-v1",
                roundingPolicyId="modelled-nearest-integer-half-up-v1",
                roundingPolicyLabel="Modelled nearest-integer result",
                state="unavailable",
                available=False,
                goldenGloryContributionPct=None,
                directLinkContributionPct=None,
                conditionalContributionPct=None,
                netLinkSkillBuffEffectPct=None,
                linkEffectMultiplier=None,
                baseFlameLinkLevel=None,
                additionalLinkGemLevels=None,
                effectiveFlameLinkLevel=None,
                luminaryMaximumLife=None,
                lifeComponent=None,
                levelFlatMin=None,
                levelFlatMax=None,
                unscaledMin=None,
                unscaledMax=None,
                exactPreRoundMin=None,
                exactPreRoundMax=None,
                modelledIntegerMin=None,
                modelledIntegerMax=None,
                contributionBreakdown={},
                levelBreakdown={},
                reasons=(
                    {
                        "code": error["code"],
                        "message": error["message"],
                    },
                ),
            )
        return evaluate_flame_link(
            self._state["flameLinkPlayerChain"],
            self._flame_link_table,
        )

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
            "migrationPending": self._migration_pending,
            "importerWarnings": self.importer_warning_state(),
            "runtimeEvidence": self.runtime_evidence_status()["state"],
            "enmityOutput": self.enmity_result().state,
            "flameLinkOutput": self.flame_link_result().state,
            "flameLinkTable": self.flame_link_table_status()["state"],
            "mechanics": MECHANICS_STATUS,
        }

    def mechanics_status(self) -> list[dict[str, Any]]:
        return mechanics_availability()
