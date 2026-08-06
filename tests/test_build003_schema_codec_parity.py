from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from golden_glory_lab.build_state import (  # noqa: E402
    BuildStateError,
    decode,
    empty_document,
    validate_document,
)
from golden_glory_lab.build_state.codec_v3 import empty_flame_link_player_chain  # noqa: E402
from golden_glory_lab.domain import evaluate_flame_link, load_flame_link_level_table  # noqa: E402

try:
    import jsonschema
    from referencing import Registry, Resource
except ImportError:  # pragma: no cover
    jsonschema = None  # type: ignore[assignment]
    Registry = None  # type: ignore[assignment]
    Resource = None  # type: ignore[assignment]


SCHEMA_PATH = ROOT / "data" / "schemas" / "build-state-v3.schema.json"
DIGEST = "a" * 64


def _load_validator() -> Any:
    if jsonschema is None or Registry is None or Resource is None:
        raise unittest.SkipTest("jsonschema and referencing are required")
    schemas = {}
    for path in sorted((ROOT / "data" / "schemas").glob("*.schema.json")):
        schemas[path.name] = json.loads(path.read_text(encoding="utf-8"))
    registry = Registry().with_resources(
        [(schema["$id"], Resource.from_contents(schema)) for schema in schemas.values()]
    )
    return jsonschema.Draft202012Validator(
        schemas["build-state-v3.schema.json"], registry=registry
    )


def _schema_valid(validator: Any, document: dict[str, Any]) -> bool:
    return not any(validator.iter_errors(document))


def _codec_valid(document: dict[str, Any]) -> bool:
    try:
        validate_document(document)
    except BuildStateError:
        return False
    return True


def _decode_raw(document: dict[str, Any]) -> tuple[bool, bool | None]:
    try:
        decoded = decode(json.dumps(document, separators=(",", ":")).encode("utf-8"))
    except BuildStateError:
        return False, None
    return True, decoded.migrated


def _mutate(document: dict[str, Any], mutator: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
    updated = copy.deepcopy(document)
    mutator(updated)
    return updated


def _set_recognition(doc: dict[str, Any], source: Any) -> None:
    doc["flameLinkPlayerChain"]["goldenGlory"]["recognitionSource"] = source


class SchemaCodecDecodeContractTests(unittest.TestCase):
    """Schema-expressible parity plus documented codec/decode exceptions."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.validator = _load_validator()
        cls.base = empty_document()
        cls.table = load_flame_link_level_table()

    def _assert_schema_codec_agree(
        self, label: str, document: dict[str, Any], *, expect_valid: bool
    ) -> None:
        schema_ok = _schema_valid(self.validator, document)
        codec_ok = _codec_valid(document)
        with self.subTest(label=label, layer="schema-codec"):
            self.assertEqual(schema_ok, expect_valid, f"schema mismatch for {label}")
            self.assertEqual(codec_ok, expect_valid, f"codec mismatch for {label}")
            self.assertEqual(schema_ok, codec_ok, f"schema/codec disagreement for {label}")

    def _assert_decode_matches_codec(
        self, label: str, document: dict[str, Any], *, expect_valid: bool
    ) -> None:
        decode_ok, _migrated = _decode_raw(document)
        with self.subTest(label=label, layer="decode"):
            self.assertEqual(decode_ok, expect_valid, f"decode mismatch for {label}")

    def test_recognition_source_matrix(self) -> None:
        cases: list[tuple[str, bool, Callable[[dict[str, Any]], None]]] = [
            (
                "none-null-valid",
                True,
                lambda doc: _set_recognition(doc, {"kind": "none", "digest": None}),
            ),
            (
                "none-with-hex-invalid",
                False,
                lambda doc: _set_recognition(doc, {"kind": "none", "digest": DIGEST}),
            ),
            (
                "advisory-valid",
                True,
                lambda doc: _set_recognition(
                    doc, {"kind": "advisory-text", "digest": DIGEST}
                ),
            ),
            (
                "pob-valid",
                True,
                lambda doc: _set_recognition(doc, {"kind": "pob-import", "digest": DIGEST}),
            ),
            (
                "copied-valid",
                True,
                lambda doc: _set_recognition(
                    doc, {"kind": "copied-text", "digest": DIGEST}
                ),
            ),
            (
                "advisory-null-digest-invalid",
                False,
                lambda doc: _set_recognition(
                    doc, {"kind": "advisory-text", "digest": None}
                ),
            ),
            (
                "digest-uppercase-invalid",
                False,
                lambda doc: _set_recognition(
                    doc, {"kind": "advisory-text", "digest": "A" * 64}
                ),
            ),
            (
                "digest-short-invalid",
                False,
                lambda doc: _set_recognition(
                    doc, {"kind": "advisory-text", "digest": "a" * 63}
                ),
            ),
            (
                "unknown-kind-invalid",
                False,
                lambda doc: _set_recognition(doc, {"kind": "other", "digest": None}),
            ),
            (
                "unknown-property-invalid",
                False,
                lambda doc: _set_recognition(
                    doc, {"kind": "none", "digest": None, "extra": 1}
                ),
            ),
            (
                "present-empty-object-invalid",
                False,
                lambda doc: _set_recognition(doc, {}),
            ),
            (
                "present-only-kind-invalid",
                False,
                lambda doc: _set_recognition(doc, {"kind": "none"}),
            ),
            (
                "present-only-digest-invalid",
                False,
                lambda doc: _set_recognition(doc, {"digest": None}),
            ),
            (
                "present-null-invalid",
                False,
                lambda doc: _set_recognition(doc, None),
            ),
            (
                "present-list-invalid",
                False,
                lambda doc: _set_recognition(doc, []),
            ),
            (
                "present-string-invalid",
                False,
                lambda doc: _set_recognition(doc, "none"),
            ),
        ]
        for label, expect_valid, mutator in cases:
            document = _mutate(self.base, mutator)
            self._assert_schema_codec_agree(label, document, expect_valid=expect_valid)
            self._assert_decode_matches_codec(label, document, expect_valid=expect_valid)

    def test_absent_recognition_source_compatibility_exception(self) -> None:
        document = copy.deepcopy(self.base)
        del document["flameLinkPlayerChain"]["goldenGlory"]["recognitionSource"]
        schema_ok = _schema_valid(self.validator, document)
        codec_ok = _codec_valid(document)
        decode_ok, migrated = _decode_raw(document)
        self.assertFalse(schema_ok)
        self.assertFalse(codec_ok)
        self.assertTrue(decode_ok)
        self.assertTrue(migrated)

    def test_whitespace_recognized_source_text(self) -> None:
        def set_gg(raw: str, recognition: dict[str, Any]) -> Callable[[dict[str, Any]], None]:
            def mutator(doc: dict[str, Any]) -> None:
                doc["flameLinkPlayerChain"]["goldenGlory"].update(
                    {
                        "allocatedState": "allocated",
                        "mercenaryTargetState": "yes",
                        "reviewedLightRadiusPct": "10",
                        "provenanceKind": "recognized-reviewed",
                        "reviewState": "reviewed",
                        "rawSourceText": raw,
                        "recognitionSource": recognition,
                    }
                )

            return mutator

        ordinary = _mutate(
            self.base,
            set_gg("10% increased Light Radius", {"kind": "none", "digest": None}),
        )
        self._assert_schema_codec_agree("recognized-raw-ok", ordinary, expect_valid=True)
        self._assert_decode_matches_codec("recognized-raw-ok", ordinary, expect_valid=True)

        for label, whitespace in (
            ("space", " "),
            ("tab", "\t"),
            ("newline", "\n"),
            ("mixed", "   \r\n   "),
        ):
            document = _mutate(
                self.base,
                set_gg(whitespace, {"kind": "none", "digest": None}),
            )
            self._assert_schema_codec_agree(
                f"whitespace-only-{label}", document, expect_valid=False
            )
            self._assert_decode_matches_codec(
                f"whitespace-only-{label}", document, expect_valid=False
            )

        with_digest = _mutate(
            self.base,
            set_gg("   ", {"kind": "advisory-text", "digest": DIGEST}),
        )
        self._assert_schema_codec_agree(
            "whitespace-with-digest-ok", with_digest, expect_valid=True
        )
        self._assert_decode_matches_codec(
            "whitespace-with-digest-ok", with_digest, expect_valid=True
        )

    def test_scalar_provenance_matrix(self) -> None:
        cases: list[tuple[str, bool, Callable[[dict[str, Any]], None]]] = [
            (
                "manual-reviewed-with-value",
                True,
                lambda doc: doc["flameLinkPlayerChain"]["directLinkBuffEffect"].update(
                    {
                        "reviewedDirectPct": "5",
                        "provenanceKind": "manual-reviewed",
                        "reviewState": "reviewed",
                    }
                ),
            ),
            (
                "manual-reviewed-without-value",
                False,
                lambda doc: doc["flameLinkPlayerChain"]["directLinkBuffEffect"].update(
                    {
                        "reviewedDirectPct": None,
                        "provenanceKind": "manual-reviewed",
                        "reviewState": "reviewed",
                    }
                ),
            ),
            (
                "recognized-with-source",
                True,
                lambda doc: doc["flameLinkPlayerChain"]["luminaryMaximumLife"].update(
                    {
                        "reviewedLife": "100",
                        "provenanceKind": "recognized-reviewed",
                        "reviewState": "reviewed",
                        "rawSourceText": "100 Life",
                    }
                ),
            ),
            (
                "recognized-without-source",
                False,
                lambda doc: doc["flameLinkPlayerChain"]["luminaryMaximumLife"].update(
                    {
                        "reviewedLife": "100",
                        "provenanceKind": "recognized-reviewed",
                        "reviewState": "reviewed",
                        "rawSourceText": "",
                        "recognitionSource": {"kind": "none", "digest": None},
                    }
                ),
            ),
            (
                "unreviewed-unreviewed",
                True,
                lambda doc: doc["flameLinkPlayerChain"]["goldenGlory"].update(
                    {"provenanceKind": "unreviewed", "reviewState": "unreviewed"}
                ),
            ),
            (
                "unreviewed-reviewed-mismatch",
                False,
                lambda doc: doc["flameLinkPlayerChain"]["goldenGlory"].update(
                    {"provenanceKind": "unreviewed", "reviewState": "reviewed"}
                ),
            ),
            (
                "catalog-default-golden-glory",
                False,
                lambda doc: doc["flameLinkPlayerChain"]["goldenGlory"].update(
                    {"provenanceKind": "catalog-default"}
                ),
            ),
            (
                "catalog-default-direct",
                False,
                lambda doc: doc["flameLinkPlayerChain"]["directLinkBuffEffect"].update(
                    {
                        "reviewedDirectPct": "500",
                        "provenanceKind": "catalog-default",
                        "reviewState": "reviewed",
                    }
                ),
            ),
            (
                "catalog-default-life",
                False,
                lambda doc: doc["flameLinkPlayerChain"]["luminaryMaximumLife"].update(
                    {
                        "reviewedLife": "5000",
                        "provenanceKind": "catalog-default",
                        "reviewState": "reviewed",
                    }
                ),
            ),
        ]
        for label, expect_valid, mutator in cases:
            document = _mutate(self.base, mutator)
            self._assert_schema_codec_agree(label, document, expect_valid=expect_valid)
            self._assert_decode_matches_codec(label, document, expect_valid=expect_valid)

    def test_conditional_catalog_matrix(self) -> None:
        def set_powerful(**updates: Any) -> Callable[[dict[str, Any]], None]:
            def mutator(doc: dict[str, Any]) -> None:
                entry = doc["flameLinkPlayerChain"]["conditionalContributions"][0]
                entry.update(updates)

            return mutator

        cases: list[tuple[str, bool, Callable[[dict[str, Any]], None]]] = [
            ("powerful-catalog-default", True, lambda _doc: None),
            (
                "inspiring-catalog-default",
                True,
                lambda doc: None,
            ),
            (
                "powerful-value-21",
                False,
                set_powerful(valuePct="21"),
            ),
            (
                "inspiring-value-21",
                False,
                lambda doc: doc["flameLinkPlayerChain"]["conditionalContributions"][1].update(
                    {"valuePct": "21"}
                ),
            ),
            (
                "powerful-kind-inspiring",
                False,
                set_powerful(kind="inspiring-bond"),
            ),
            (
                "powerful-kind-manual",
                False,
                set_powerful(kind="manual"),
            ),
            (
                "inspiring-wrong-id",
                False,
                lambda doc: doc["flameLinkPlayerChain"]["conditionalContributions"][1].update(
                    {"contributionId": "other-inspiring"}
                ),
            ),
            (
                "generic-with-powerful-kind",
                False,
                lambda doc: doc["flameLinkPlayerChain"]["conditionalContributions"].append(
                    {
                        "contributionId": "manual-conditional-0001",
                        "label": "Bad",
                        "valuePct": "20",
                        "conditionState": "inactive",
                        "kind": "powerful-bond",
                        "provenanceKind": "manual-reviewed",
                        "rawSourceText": "",
                        "recognitionSource": {"kind": "none", "digest": None},
                    }
                ),
            ),
            (
                "generic-catalog-default",
                False,
                lambda doc: doc["flameLinkPlayerChain"]["conditionalContributions"].append(
                    {
                        "contributionId": "manual-conditional-0001",
                        "label": "Bad",
                        "valuePct": "5",
                        "conditionState": "inactive",
                        "kind": "manual",
                        "provenanceKind": "catalog-default",
                        "rawSourceText": "",
                        "recognitionSource": {"kind": "none", "digest": None},
                    }
                ),
            ),
            (
                "catalog-default-with-raw",
                False,
                set_powerful(rawSourceText="Powerful Bond"),
            ),
            (
                "catalog-default-with-digest",
                False,
                set_powerful(
                    recognitionSource={"kind": "advisory-text", "digest": DIGEST}
                ),
            ),
            (
                "generic-manual-valid",
                True,
                lambda doc: doc["flameLinkPlayerChain"]["conditionalContributions"].append(
                    {
                        "contributionId": "manual-conditional-0001",
                        "label": "Manual",
                        "valuePct": "5",
                        "conditionState": "inactive",
                        "kind": "manual",
                        "provenanceKind": "manual-reviewed",
                        "rawSourceText": "",
                        "recognitionSource": {"kind": "none", "digest": None},
                    }
                ),
            ),
            (
                "recognized-catalog-row-valid",
                True,
                set_powerful(
                    provenanceKind="recognized-reviewed",
                    rawSourceText="Powerful Bond",
                    recognitionSource={"kind": "advisory-text", "digest": DIGEST},
                ),
            ),
        ]
        for label, expect_valid, mutator in cases:
            document = _mutate(self.base, mutator)
            self._assert_schema_codec_agree(label, document, expect_valid=expect_valid)
            self._assert_decode_matches_codec(label, document, expect_valid=expect_valid)

    def test_duplicate_ids_are_codec_only(self) -> None:
        document = copy.deepcopy(self.base)
        document["flameLinkPlayerChain"]["conditionalContributions"].append(
            copy.deepcopy(document["flameLinkPlayerChain"]["conditionalContributions"][0])
        )
        schema_ok = _schema_valid(self.validator, document)
        codec_ok = _codec_valid(document)
        decode_ok, _migrated = _decode_raw(document)
        self.assertTrue(schema_ok, "duplicate contributionId is not schema-expressible")
        self.assertFalse(codec_ok)
        self.assertFalse(decode_ok)

        levels = document["flameLinkPlayerChain"]["flameLinkLevel"]["additionalLinkGemLevels"]
        levels.append(copy.deepcopy(levels[0]))
        # After duplicate conditional already invalid in codec; rebuild for level-only case.
        level_doc = copy.deepcopy(self.base)
        level_rows = level_doc["flameLinkPlayerChain"]["flameLinkLevel"][
            "additionalLinkGemLevels"
        ]
        level_rows.append(copy.deepcopy(level_rows[0]))
        schema_ok = _schema_valid(self.validator, level_doc)
        codec_ok = _codec_valid(level_doc)
        decode_ok, _migrated = _decode_raw(level_doc)
        self.assertTrue(schema_ok)
        self.assertFalse(codec_ok)
        self.assertFalse(decode_ok)

    def test_additional_level_regression(self) -> None:
        cases: list[tuple[str, bool, Callable[[dict[str, Any]], None]]] = [
            ("empowered-catalog-2", True, lambda _doc: None),
            (
                "empowered-catalog-1",
                False,
                lambda doc: doc["flameLinkPlayerChain"]["flameLinkLevel"][
                    "additionalLinkGemLevels"
                ][0].update({"levels": 1}),
            ),
            (
                "empowered-catalog-3",
                False,
                lambda doc: doc["flameLinkPlayerChain"]["flameLinkLevel"][
                    "additionalLinkGemLevels"
                ][0].update({"levels": 3}),
            ),
            (
                "generic-catalog-default-level",
                False,
                lambda doc: doc["flameLinkPlayerChain"]["flameLinkLevel"][
                    "additionalLinkGemLevels"
                ].append(
                    {
                        "contributionId": "manual-level-0001",
                        "label": "Bad",
                        "levels": 2,
                        "activeState": "inactive",
                        "provenanceKind": "catalog-default",
                        "rawSourceText": "",
                        "recognitionSource": {"kind": "none", "digest": None},
                    }
                ),
            ),
        ]
        for label, expect_valid, mutator in cases:
            document = _mutate(self.base, mutator)
            self._assert_schema_codec_agree(label, document, expect_valid=expect_valid)
            self._assert_decode_matches_codec(label, document, expect_valid=expect_valid)

    def test_domain_fail_closed_for_malformed_provenance(self) -> None:
        chain = empty_flame_link_player_chain()
        for entry in chain["conditionalContributions"]:
            entry["conditionState"] = "inactive"
        chain["flameLinkLevel"]["additionalLinkGemLevels"][0]["activeState"] = "inactive"

        # Direct catalog-default 500% must not count.
        chain["goldenGlory"].update(
            {
                "allocatedState": "not-allocated",
                "mercenaryTargetState": "yes",
                "reviewedLightRadiusPct": "0",
                "provenanceKind": "manual-reviewed",
                "reviewState": "reviewed",
            }
        )
        chain["directLinkBuffEffect"].update(
            {
                "reviewedDirectPct": "500",
                "provenanceKind": "catalog-default",
                "reviewState": "reviewed",
            }
        )
        chain["luminaryMaximumLife"].update(
            {
                "reviewedLife": "5000",
                "provenanceKind": "manual-reviewed",
                "reviewState": "reviewed",
            }
        )
        result = evaluate_flame_link(chain, self.table)
        self.assertFalse(result.available)
        self.assertTrue(
            any(
                reason["code"] == "DIRECT_LINK_BUFF_EFFECT_PROVENANCE_INVALID"
                for reason in result.reasons
            )
        )

        # Golden Glory catalog-default cannot count when allocated.
        chain["goldenGlory"].update(
            {
                "allocatedState": "allocated",
                "mercenaryTargetState": "yes",
                "reviewedLightRadiusPct": "40",
                "provenanceKind": "catalog-default",
                "reviewState": "reviewed",
            }
        )
        chain["directLinkBuffEffect"].update(
            {
                "reviewedDirectPct": "0",
                "provenanceKind": "manual-reviewed",
                "reviewState": "reviewed",
            }
        )
        result = evaluate_flame_link(chain, self.table)
        self.assertFalse(result.available)
        self.assertTrue(
            any(
                reason["code"] == "GOLDEN_GLORY_PROVENANCE_INVALID"
                for reason in result.reasons
            )
        )

        # Life catalog-default cannot count.
        chain["goldenGlory"].update(
            {
                "allocatedState": "not-allocated",
                "provenanceKind": "manual-reviewed",
                "reviewedLightRadiusPct": "0",
            }
        )
        chain["luminaryMaximumLife"].update(
            {
                "reviewedLife": "5000",
                "provenanceKind": "catalog-default",
                "reviewState": "reviewed",
            }
        )
        result = evaluate_flame_link(chain, self.table)
        self.assertFalse(result.available)
        self.assertTrue(
            any(
                reason["code"] == "LUMINARY_MAXIMUM_LIFE_PROVENANCE_INVALID"
                for reason in result.reasons
            )
        )

        # Active generic catalog-default cannot count.
        chain["luminaryMaximumLife"].update(
            {
                "provenanceKind": "manual-reviewed",
                "reviewState": "reviewed",
                "reviewedLife": "5000",
            }
        )
        chain["conditionalContributions"].append(
            {
                "contributionId": "manual-bad",
                "label": "Bad",
                "valuePct": "50",
                "conditionState": "active",
                "kind": "manual",
                "provenanceKind": "catalog-default",
                "rawSourceText": "",
                "recognitionSource": {"kind": "none", "digest": None},
            }
        )
        result = evaluate_flame_link(chain, self.table)
        self.assertFalse(result.available)
        self.assertTrue(
            any(
                reason["code"] == "CONDITIONAL_CONTRIBUTION_PROVENANCE_INVALID"
                for reason in result.reasons
            )
        )

        # Malformed Powerful Bond catalog-default cannot count.
        chain["conditionalContributions"] = [
            {
                "contributionId": "powerful-bond",
                "label": "Powerful Bond",
                "valuePct": "21",
                "conditionState": "active",
                "kind": "powerful-bond",
                "provenanceKind": "catalog-default",
                "rawSourceText": "",
                "recognitionSource": {"kind": "none", "digest": None},
            },
            {
                "contributionId": "inspiring-bond",
                "label": "Inspiring Bond",
                "valuePct": "20",
                "conditionState": "inactive",
                "kind": "inspiring-bond",
                "provenanceKind": "catalog-default",
                "rawSourceText": "",
                "recognitionSource": {"kind": "none", "digest": None},
            },
        ]
        result = evaluate_flame_link(chain, self.table)
        self.assertFalse(result.available)

        # Valid protected catalog defaults still calculate.
        chain = empty_flame_link_player_chain()
        chain["goldenGlory"].update(
            {
                "allocatedState": "not-allocated",
                "mercenaryTargetState": "yes",
                "reviewedLightRadiusPct": "0",
                "provenanceKind": "manual-reviewed",
                "reviewState": "reviewed",
            }
        )
        chain["directLinkBuffEffect"].update(
            {
                "reviewedDirectPct": "0",
                "provenanceKind": "manual-reviewed",
                "reviewState": "reviewed",
            }
        )
        for entry in chain["conditionalContributions"]:
            if entry["contributionId"] == "powerful-bond":
                entry["conditionState"] = "active"
            else:
                entry["conditionState"] = "inactive"
        chain["flameLinkLevel"]["additionalLinkGemLevels"][0]["activeState"] = "inactive"
        chain["luminaryMaximumLife"].update(
            {
                "reviewedLife": "0",
                "provenanceKind": "manual-reviewed",
                "reviewState": "reviewed",
            }
        )
        result = evaluate_flame_link(chain, self.table)
        self.assertTrue(result.available)
        self.assertEqual(result.netLinkSkillBuffEffectPct, "20")

    def test_empowered_bond_levels_locked_across_provenance(self) -> None:
        """Empowered Bond identity is always +2 regardless of provenance."""

        def set_empowered(
            *,
            levels: int,
            provenance: str,
            raw: str = "",
            recognition: dict[str, Any] | None = None,
        ) -> Callable[[dict[str, Any]], None]:
            if recognition is None:
                recognition = {"kind": "none", "digest": None}

            def mutator(doc: dict[str, Any]) -> None:
                doc["flameLinkPlayerChain"]["flameLinkLevel"]["additionalLinkGemLevels"][
                    0
                ].update(
                    {
                        "contributionId": "empowered-bond",
                        "label": "Empowered Bond",
                        "levels": levels,
                        "activeState": "inactive",
                        "provenanceKind": provenance,
                        "rawSourceText": raw,
                        "recognitionSource": recognition,
                    }
                )

            return mutator

        cases: list[tuple[str, bool, Callable[[dict[str, Any]], None]]] = [
            ("empowered-catalog-2", True, set_empowered(levels=2, provenance="catalog-default")),
            (
                "empowered-manual-2",
                True,
                set_empowered(levels=2, provenance="manual-reviewed"),
            ),
            (
                "empowered-recognized-2",
                True,
                set_empowered(
                    levels=2,
                    provenance="recognized-reviewed",
                    raw="Empowered Bond",
                ),
            ),
            ("empowered-catalog-1", False, set_empowered(levels=1, provenance="catalog-default")),
            ("empowered-catalog-3", False, set_empowered(levels=3, provenance="catalog-default")),
            ("empowered-manual-1", False, set_empowered(levels=1, provenance="manual-reviewed")),
            ("empowered-manual-3", False, set_empowered(levels=3, provenance="manual-reviewed")),
            (
                "empowered-recognized-1",
                False,
                set_empowered(
                    levels=1,
                    provenance="recognized-reviewed",
                    raw="Empowered Bond",
                ),
            ),
            (
                "empowered-recognized-3",
                False,
                set_empowered(
                    levels=3,
                    provenance="recognized-reviewed",
                    raw="Empowered Bond",
                ),
            ),
            (
                "empowered-catalog-with-raw",
                False,
                set_empowered(
                    levels=2,
                    provenance="catalog-default",
                    raw="Empowered Bond",
                ),
            ),
            (
                "empowered-catalog-with-digest",
                False,
                set_empowered(
                    levels=2,
                    provenance="catalog-default",
                    recognition={"kind": "advisory-text", "digest": DIGEST},
                ),
            ),
            (
                "empowered-catalog-with-pob-digest",
                False,
                set_empowered(
                    levels=2,
                    provenance="catalog-default",
                    recognition={"kind": "pob-import", "digest": DIGEST},
                ),
            ),
            (
                "empowered-catalog-with-copied-digest",
                False,
                set_empowered(
                    levels=2,
                    provenance="catalog-default",
                    recognition={"kind": "copied-text", "digest": DIGEST},
                ),
            ),
            (
                "empowered-catalog-none-with-digest",
                False,
                set_empowered(
                    levels=2,
                    provenance="catalog-default",
                    recognition={"kind": "none", "digest": DIGEST},
                ),
            ),
        ]
        for label, expect_valid, mutator in cases:
            document = _mutate(self.base, mutator)
            self._assert_schema_codec_agree(label, document, expect_valid=expect_valid)
            self._assert_decode_matches_codec(label, document, expect_valid=expect_valid)

    def test_forbidden_bond_ids_as_additional_levels(self) -> None:
        for bond_id, label in (
            ("powerful-bond", "Powerful Bond"),
            ("inspiring-bond", "Inspiring Bond"),
        ):
            document = _mutate(
                self.base,
                lambda doc, bond_id=bond_id, label=label: doc["flameLinkPlayerChain"][
                    "flameLinkLevel"
                ]["additionalLinkGemLevels"].append(
                    {
                        "contributionId": bond_id,
                        "label": label,
                        "levels": 1,
                        "activeState": "inactive",
                        "provenanceKind": "manual-reviewed",
                        "rawSourceText": "",
                        "recognitionSource": {"kind": "none", "digest": None},
                    }
                ),
            )
            self._assert_schema_codec_agree(
                f"forbid-{bond_id}-level", document, expect_valid=False
            )
            self._assert_decode_matches_codec(
                f"forbid-{bond_id}-level", document, expect_valid=False
            )

    def test_generic_recognized_additional_level_identity(self) -> None:
        def append_generic(
            *,
            raw: str,
            recognition: dict[str, Any],
            levels: int = 1,
        ) -> Callable[[dict[str, Any]], None]:
            def mutator(doc: dict[str, Any]) -> None:
                doc["flameLinkPlayerChain"]["flameLinkLevel"]["additionalLinkGemLevels"].append(
                    {
                        "contributionId": "manual-level-0001",
                        "label": "Generic",
                        "levels": levels,
                        "activeState": "inactive",
                        "provenanceKind": "recognized-reviewed",
                        "rawSourceText": raw,
                        "recognitionSource": recognition,
                    }
                )

            return mutator

        cases: list[tuple[str, bool, Callable[[dict[str, Any]], None]]] = [
            (
                "generic-recognized-raw",
                True,
                append_generic(
                    raw="+1 to Level of all Link Skill Gems",
                    recognition={"kind": "none", "digest": None},
                ),
            ),
            (
                "generic-recognized-digest",
                True,
                append_generic(
                    raw="",
                    recognition={"kind": "advisory-text", "digest": DIGEST},
                ),
            ),
            (
                "generic-recognized-no-identity",
                False,
                append_generic(
                    raw="",
                    recognition={"kind": "none", "digest": None},
                ),
            ),
            (
                "generic-recognized-whitespace",
                False,
                append_generic(
                    raw="   \n\t  ",
                    recognition={"kind": "none", "digest": None},
                ),
            ),
            (
                "generic-recognized-short-digest",
                False,
                append_generic(
                    raw="",
                    recognition={"kind": "advisory-text", "digest": "x"},
                ),
            ),
            (
                "generic-recognized-uppercase-digest",
                False,
                append_generic(
                    raw="",
                    recognition={"kind": "advisory-text", "digest": "A" * 64},
                ),
            ),
        ]
        for label, expect_valid, mutator in cases:
            document = _mutate(self.base, mutator)
            self._assert_schema_codec_agree(label, document, expect_valid=expect_valid)
            self._assert_decode_matches_codec(label, document, expect_valid=expect_valid)

    def test_strict_integer_representation_codec_only(self) -> None:
        """Draft 2020-12 accepts 2.0 as integer; codec/decoder require JSON ints."""

        base_float = _mutate(
            self.base,
            lambda doc: doc["flameLinkPlayerChain"]["flameLinkLevel"].update(
                {"baseLevel": 21.0}
            ),
        )
        schema_ok = _schema_valid(self.validator, base_float)
        codec_ok = _codec_valid(base_float)
        decode_ok, _migrated = _decode_raw(base_float)
        self.assertTrue(schema_ok, "schema may accept mathematically integral float baseLevel")
        self.assertFalse(codec_ok)
        self.assertFalse(decode_ok)

        levels_float = _mutate(
            self.base,
            lambda doc: doc["flameLinkPlayerChain"]["flameLinkLevel"][
                "additionalLinkGemLevels"
            ][0].update({"levels": 2.0}),
        )
        schema_ok = _schema_valid(self.validator, levels_float)
        codec_ok = _codec_valid(levels_float)
        decode_ok, _migrated = _decode_raw(levels_float)
        self.assertTrue(schema_ok, "schema may accept mathematically integral float levels")
        self.assertFalse(codec_ok)
        self.assertFalse(decode_ok)


def _domain_baseline_chain() -> dict[str, Any]:
    chain = empty_flame_link_player_chain()
    chain["goldenGlory"].update(
        {
            "allocatedState": "not-allocated",
            "mercenaryTargetState": "yes",
            "reviewedLightRadiusPct": "0",
            "provenanceKind": "manual-reviewed",
            "reviewState": "reviewed",
        }
    )
    chain["directLinkBuffEffect"].update(
        {
            "reviewedDirectPct": "0",
            "provenanceKind": "manual-reviewed",
            "reviewState": "reviewed",
        }
    )
    for entry in chain["conditionalContributions"]:
        entry["conditionState"] = "inactive"
    chain["luminaryMaximumLife"].update(
        {
            "reviewedLife": "0",
            "provenanceKind": "manual-reviewed",
            "reviewState": "reviewed",
        }
    )
    return chain


class AdditionalLevelDomainContractTests(unittest.TestCase):
    """Direct evaluator fail-closed contract for malformed additional-level rows."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.table = load_flame_link_level_table()

    def _evaluate_with_levels(
        self,
        rows: list[dict[str, Any]],
        *,
        base_level: Any = 21,
    ) -> Any:
        chain = _domain_baseline_chain()
        chain["flameLinkLevel"]["baseLevel"] = base_level
        chain["flameLinkLevel"]["baseLevelProvenance"] = "manual-benchmark-default"
        chain["flameLinkLevel"]["additionalLinkGemLevels"] = rows
        return evaluate_flame_link(chain, self.table)

    def _assert_unavailable(
        self,
        result: Any,
        *,
        code: str,
        expected_effective: int | None = None,
    ) -> None:
        self.assertFalse(result.available)
        self.assertTrue(
            any(reason["code"] == code for reason in result.reasons),
            f"expected {code} in {[r['code'] for r in result.reasons]}",
        )
        if expected_effective is not None:
            self.assertNotEqual(result.effectiveFlameLinkLevel, expected_effective)

    def test_domain_adversarial_additional_levels(self) -> None:
        none_source = {"kind": "none", "digest": None}
        good_digest = {"kind": "advisory-text", "digest": DIGEST}

        def row(
            contribution_id: str,
            levels: Any,
            *,
            provenance: Any = "manual-reviewed",
            active: str = "active",
            raw: str = "",
            recognition: dict[str, Any] | None = None,
            label: str = "Row",
        ) -> dict[str, Any]:
            return {
                "contributionId": contribution_id,
                "label": label,
                "levels": levels,
                "activeState": active,
                "provenanceKind": provenance,
                "rawSourceText": raw,
                "recognitionSource": recognition if recognition is not None else none_source,
            }

        negative_cases: list[tuple[str, list[dict[str, Any]], str, Any]] = [
            (
                "empowered-manual-3",
                [row("empowered-bond", 3, provenance="manual-reviewed", label="Empowered Bond")],
                "ADDITIONAL_LINK_LEVEL_CATALOG_INVALID",
                21,
            ),
            (
                "empowered-recognized-1",
                [
                    row(
                        "empowered-bond",
                        1,
                        provenance="recognized-reviewed",
                        raw="Empowered Bond",
                        label="Empowered Bond",
                    )
                ],
                "ADDITIONAL_LINK_LEVEL_CATALOG_INVALID",
                21,
            ),
            (
                "powerful-bond-level",
                [row("powerful-bond", 1, label="Powerful Bond")],
                "ADDITIONAL_LINK_LEVEL_CATALOG_INVALID",
                21,
            ),
            (
                "inspiring-bond-level",
                [row("inspiring-bond", 1, label="Inspiring Bond")],
                "ADDITIONAL_LINK_LEVEL_CATALOG_INVALID",
                21,
            ),
            (
                "unknown-provenance",
                [row("manual-level-0001", 1, provenance="forged")],
                "ADDITIONAL_LINK_LEVEL_PROVENANCE_INVALID",
                21,
            ),
            (
                "unreviewed-provenance",
                [row("manual-level-0001", 1, provenance="unreviewed")],
                "ADDITIONAL_LINK_LEVEL_PROVENANCE_INVALID",
                21,
            ),
            (
                "missing-provenance",
                [row("manual-level-0001", 1, provenance=None)],
                "ADDITIONAL_LINK_LEVEL_PROVENANCE_INVALID",
                21,
            ),
            (
                "empty-provenance",
                [row("manual-level-0001", 1, provenance="")],
                "ADDITIONAL_LINK_LEVEL_PROVENANCE_INVALID",
                21,
            ),
            (
                "recognized-without-source",
                [row("manual-level-0001", 1, provenance="recognized-reviewed")],
                "ADDITIONAL_LINK_LEVEL_PROVENANCE_INVALID",
                21,
            ),
            (
                "recognized-short-digest",
                [
                    row(
                        "manual-level-0001",
                        1,
                        provenance="recognized-reviewed",
                        recognition={"kind": "advisory-text", "digest": "x"},
                    )
                ],
                "ADDITIONAL_LINK_LEVEL_PROVENANCE_INVALID",
                21,
            ),
            (
                "recognized-uppercase-digest",
                [
                    row(
                        "manual-level-0001",
                        1,
                        provenance="recognized-reviewed",
                        recognition={"kind": "advisory-text", "digest": "A" * 64},
                    )
                ],
                "ADDITIONAL_LINK_LEVEL_PROVENANCE_INVALID",
                21,
            ),
            (
                "recognized-null-digest-whitespace",
                [
                    row(
                        "manual-level-0001",
                        1,
                        provenance="recognized-reviewed",
                        raw="   ",
                        recognition={"kind": "advisory-text", "digest": None},
                    )
                ],
                "ADDITIONAL_LINK_LEVEL_PROVENANCE_INVALID",
                21,
            ),
            (
                "string-levels",
                [row("manual-level-0001", "2")],
                "ADDITIONAL_LINK_LEVEL_VALUE_INVALID",
                21,
            ),
            (
                "fractional-levels",
                [row("manual-level-0001", 2.9)],
                "ADDITIONAL_LINK_LEVEL_VALUE_INVALID",
                21,
            ),
            (
                "boolean-levels",
                [row("manual-level-0001", True)],
                "ADDITIONAL_LINK_LEVEL_VALUE_INVALID",
                21,
            ),
            (
                "catalog-empowered-with-raw",
                [
                    row(
                        "empowered-bond",
                        2,
                        provenance="catalog-default",
                        raw="Empowered Bond",
                        label="Empowered Bond",
                    )
                ],
                "ADDITIONAL_LINK_LEVEL_PROVENANCE_INVALID",
                21,
            ),
            (
                "catalog-empowered-with-digest",
                [
                    row(
                        "empowered-bond",
                        2,
                        provenance="catalog-default",
                        recognition=good_digest,
                        label="Empowered Bond",
                    )
                ],
                "ADDITIONAL_LINK_LEVEL_PROVENANCE_INVALID",
                21,
            ),
        ]
        for label, rows, code, base in negative_cases:
            with self.subTest(label=label):
                result = self._evaluate_with_levels(rows, base_level=base)
                self._assert_unavailable(result, code=code, expected_effective=base + 1)

        for label, base in (
            ("string-base", "21"),
            ("fractional-base", 21.0),
            ("boolean-base", True),
        ):
            with self.subTest(label=label):
                result = self._evaluate_with_levels(
                    [row("manual-level-0001", 1, active="inactive")],
                    base_level=base,
                )
                self.assertFalse(result.available)
                self.assertTrue(
                    any(
                        reason["code"] == "FLAME_LINK_BASE_LEVEL_INVALID"
                        for reason in result.reasons
                    )
                )
                self.assertIsNone(result.effectiveFlameLinkLevel)

        positive_cases: list[tuple[str, list[dict[str, Any]], int]] = [
            (
                "manual-generic-plus-1",
                [row("manual-level-0001", 1)],
                22,
            ),
            (
                "manual-generic-minus-1",
                [row("manual-level-0001", -1)],
                20,
            ),
            (
                "recognized-generic-plus-1-raw",
                [
                    row(
                        "manual-level-0001",
                        1,
                        provenance="recognized-reviewed",
                        raw="+1 to Level of all Link Skill Gems",
                    )
                ],
                22,
            ),
            (
                "recognized-generic-plus-1-digest",
                [
                    row(
                        "manual-level-0001",
                        1,
                        provenance="recognized-reviewed",
                        recognition=good_digest,
                    )
                ],
                22,
            ),
            (
                "empowered-catalog-2",
                [
                    row(
                        "empowered-bond",
                        2,
                        provenance="catalog-default",
                        label="Empowered Bond",
                    )
                ],
                23,
            ),
            (
                "empowered-manual-2",
                [
                    row(
                        "empowered-bond",
                        2,
                        provenance="manual-reviewed",
                        label="Empowered Bond",
                    )
                ],
                23,
            ),
            (
                "empowered-recognized-2",
                [
                    row(
                        "empowered-bond",
                        2,
                        provenance="recognized-reviewed",
                        raw="Empowered Bond",
                        label="Empowered Bond",
                    )
                ],
                23,
            ),
        ]
        for label, rows, expected_level in positive_cases:
            with self.subTest(label=label):
                result = self._evaluate_with_levels(rows)
                self.assertTrue(result.available, result.reasons)
                self.assertEqual(result.effectiveFlameLinkLevel, expected_level)


class DomainRecognitionAndBaseProvenanceTests(unittest.TestCase):
    """Direct evaluator recognition-source and base-level provenance contracts."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.table = load_flame_link_level_table()

    def _baseline(self) -> dict[str, Any]:
        return _domain_baseline_chain()

    def _assert_unavailable_code(self, result: Any, code: str) -> None:
        self.assertFalse(result.available, result.reasons)
        self.assertIn(code, {reason["code"] for reason in result.reasons})

    def test_malformed_recognition_source_rejected_across_inputs(self) -> None:
        malformed: list[Any] = [
            {"kind": "pob-import", "digest": "x"},
            {"kind": "advisory-text", "digest": "A" * 64},
            {"kind": "copied-text", "digest": None},
            {"kind": "none", "digest": DIGEST},
            {"kind": "pob-import"},
            {"digest": DIGEST},
            {"kind": "pob-import", "digest": DIGEST, "extra": True},
            {},
            None,
            "bad",
        ]
        categories = (
            "goldenGlory",
            "directLinkBuffEffect",
            "luminaryMaximumLife",
            "conditional",
            "additionalLevel",
        )
        for category in categories:
            for index, source in enumerate(malformed):
                with self.subTest(category=category, index=index, source=source):
                    chain = self._baseline()
                    chain["flameLinkLevel"]["additionalLinkGemLevels"][0][
                        "activeState"
                    ] = "inactive"
                    if category == "goldenGlory":
                        chain["goldenGlory"].update(
                            {
                                "allocatedState": "allocated",
                                "mercenaryTargetState": "yes",
                                "reviewedLightRadiusPct": "40",
                                "provenanceKind": "recognized-reviewed",
                                "reviewState": "reviewed",
                                "rawSourceText": "   \t\n  ",
                                "recognitionSource": source,
                            }
                        )
                        expected = "GOLDEN_GLORY_PROVENANCE_INVALID"
                    elif category == "directLinkBuffEffect":
                        chain["directLinkBuffEffect"].update(
                            {
                                "reviewedDirectPct": "10",
                                "provenanceKind": "recognized-reviewed",
                                "reviewState": "reviewed",
                                "rawSourceText": " \n ",
                                "recognitionSource": source,
                            }
                        )
                        expected = "DIRECT_LINK_BUFF_EFFECT_PROVENANCE_INVALID"
                    elif category == "luminaryMaximumLife":
                        chain["luminaryMaximumLife"].update(
                            {
                                "reviewedLife": "5000",
                                "provenanceKind": "recognized-reviewed",
                                "reviewState": "reviewed",
                                "rawSourceText": "\t",
                                "recognitionSource": source,
                            }
                        )
                        expected = "LUMINARY_MAXIMUM_LIFE_PROVENANCE_INVALID"
                    elif category == "conditional":
                        chain["conditionalContributions"] = [
                            {
                                "contributionId": "manual-conditional-0001",
                                "label": "Manual",
                                "valuePct": "5",
                                "conditionState": "active",
                                "kind": "manual",
                                "provenanceKind": "recognized-reviewed",
                                "rawSourceText": "  ",
                                "recognitionSource": source,
                            },
                            {
                                "contributionId": "inspiring-bond",
                                "label": "Inspiring Bond",
                                "valuePct": "20",
                                "conditionState": "inactive",
                                "kind": "inspiring-bond",
                                "provenanceKind": "catalog-default",
                                "rawSourceText": "",
                                "recognitionSource": {"kind": "none", "digest": None},
                            },
                        ]
                        expected = "CONDITIONAL_CONTRIBUTION_PROVENANCE_INVALID"
                    else:
                        chain["flameLinkLevel"]["additionalLinkGemLevels"] = [
                            {
                                "contributionId": "manual-level-0001",
                                "label": "Generic",
                                "levels": 1,
                                "activeState": "active",
                                "provenanceKind": "recognized-reviewed",
                                "rawSourceText": "\n\n",
                                "recognitionSource": source,
                            }
                        ]
                        expected = "ADDITIONAL_LINK_LEVEL_PROVENANCE_INVALID"
                    result = evaluate_flame_link(chain, self.table)
                    self._assert_unavailable_code(result, expected)

        # Positive controls: meaningful raw, or exact valid digest identity.
        for kind in ("advisory-text", "pob-import", "copied-text"):
            with self.subTest(positive="digest", kind=kind):
                chain = self._baseline()
                chain["flameLinkLevel"]["additionalLinkGemLevels"][0][
                    "activeState"
                ] = "inactive"
                chain["directLinkBuffEffect"].update(
                    {
                        "reviewedDirectPct": "10",
                        "provenanceKind": "recognized-reviewed",
                        "reviewState": "reviewed",
                        "rawSourceText": "",
                        "recognitionSource": {"kind": kind, "digest": DIGEST},
                    }
                )
                result = evaluate_flame_link(chain, self.table)
                self.assertTrue(result.available, result.reasons)
        with self.subTest(positive="raw-text"):
            chain = self._baseline()
            chain["flameLinkLevel"]["additionalLinkGemLevels"][0]["activeState"] = (
                "inactive"
            )
            chain["goldenGlory"].update(
                {
                    "allocatedState": "allocated",
                    "mercenaryTargetState": "yes",
                    "reviewedLightRadiusPct": "40",
                    "provenanceKind": "recognized-reviewed",
                    "reviewState": "reviewed",
                    "rawSourceText": "40% increased Light Radius",
                    "recognitionSource": {"kind": "none", "digest": None},
                }
            )
            result = evaluate_flame_link(chain, self.table)
            self.assertTrue(result.available, result.reasons)

    def test_catalog_missing_and_extra_fields_rejected(self) -> None:
        cases: list[tuple[str, Callable[[dict[str, Any]], None], str]] = [
            (
                "powerful-missing-raw",
                lambda chain: chain["conditionalContributions"][0].pop("rawSourceText"),
                "CONDITIONAL_CONTRIBUTION_PROVENANCE_INVALID",
            ),
            (
                "powerful-missing-digest-key",
                lambda chain: chain["conditionalContributions"][0][
                    "recognitionSource"
                ].pop("digest"),
                "CONDITIONAL_CONTRIBUTION_PROVENANCE_INVALID",
            ),
            (
                "powerful-extra-recognition-field",
                lambda chain: chain["conditionalContributions"][0][
                    "recognitionSource"
                ].__setitem__("extra", True),
                "CONDITIONAL_CONTRIBUTION_PROVENANCE_INVALID",
            ),
            (
                "empowered-missing-raw",
                lambda chain: (
                    chain["flameLinkLevel"]["additionalLinkGemLevels"][0].update(
                        {
                            "activeState": "active",
                            "provenanceKind": "catalog-default",
                            "levels": 2,
                        }
                    ),
                    chain["flameLinkLevel"]["additionalLinkGemLevels"][0].pop(
                        "rawSourceText"
                    ),
                ),
                "ADDITIONAL_LINK_LEVEL_PROVENANCE_INVALID",
            ),
            (
                "empowered-missing-digest-key",
                lambda chain: (
                    chain["flameLinkLevel"]["additionalLinkGemLevels"][0].update(
                        {
                            "activeState": "active",
                            "provenanceKind": "catalog-default",
                            "levels": 2,
                            "rawSourceText": "",
                            "recognitionSource": {"kind": "none"},
                        }
                    )
                ),
                "ADDITIONAL_LINK_LEVEL_PROVENANCE_INVALID",
            ),
            (
                "empowered-extra-recognition-field",
                lambda chain: (
                    chain["flameLinkLevel"]["additionalLinkGemLevels"][0].update(
                        {
                            "activeState": "active",
                            "provenanceKind": "catalog-default",
                            "levels": 2,
                            "rawSourceText": "",
                            "recognitionSource": {
                                "kind": "none",
                                "digest": None,
                                "extra": True,
                            },
                        }
                    )
                ),
                "ADDITIONAL_LINK_LEVEL_PROVENANCE_INVALID",
            ),
        ]
        for label, mutator, code in cases:
            with self.subTest(label=label):
                chain = self._baseline()
                for entry in chain["conditionalContributions"]:
                    if entry["contributionId"] == "powerful-bond":
                        entry.update(
                            {
                                "conditionState": "active",
                                "provenanceKind": "catalog-default",
                                "valuePct": "20",
                                "kind": "powerful-bond",
                                "rawSourceText": "",
                                "recognitionSource": {"kind": "none", "digest": None},
                            }
                        )
                    else:
                        entry["conditionState"] = "inactive"
                chain["flameLinkLevel"]["additionalLinkGemLevels"][0][
                    "activeState"
                ] = "inactive"
                mutator(chain)
                result = evaluate_flame_link(chain, self.table)
                self._assert_unavailable_code(result, code)

    def test_base_level_provenance_domain_validation(self) -> None:
        negative: list[tuple[str, dict[str, Any], str]] = [
            (
                "benchmark-mismatch",
                {"baseLevel": 25, "baseLevelProvenance": "manual-benchmark-default"},
                "FLAME_LINK_BASE_LEVEL_BENCHMARK_MISMATCH",
            ),
            (
                "forged",
                {"baseLevel": 21, "baseLevelProvenance": "forged"},
                "FLAME_LINK_BASE_LEVEL_PROVENANCE_INVALID",
            ),
            (
                "null-provenance",
                {"baseLevel": 21, "baseLevelProvenance": None},
                "FLAME_LINK_BASE_LEVEL_PROVENANCE_INVALID",
            ),
            (
                "empty-provenance",
                {"baseLevel": 21, "baseLevelProvenance": ""},
                "FLAME_LINK_BASE_LEVEL_PROVENANCE_INVALID",
            ),
        ]
        for label, level_block, code in negative:
            with self.subTest(label=label):
                chain = self._baseline()
                chain["flameLinkLevel"].update(level_block)
                chain["flameLinkLevel"]["additionalLinkGemLevels"][0][
                    "activeState"
                ] = "inactive"
                result = evaluate_flame_link(chain, self.table)
                self._assert_unavailable_code(result, code)
                self.assertIsNone(result.effectiveFlameLinkLevel)

        positives: list[tuple[str, dict[str, Any], int]] = [
            (
                "benchmark-21",
                {"baseLevel": 21, "baseLevelProvenance": "manual-benchmark-default"},
                21,
            ),
            (
                "manual-reviewed-20",
                {"baseLevel": 20, "baseLevelProvenance": "manual-reviewed"},
                20,
            ),
            (
                "imported-recognized-22",
                {"baseLevel": 22, "baseLevelProvenance": "imported-recognized"},
                22,
            ),
        ]
        for label, level_block, expected in positives:
            with self.subTest(label=label):
                chain = self._baseline()
                chain["flameLinkLevel"].update(level_block)
                chain["flameLinkLevel"]["additionalLinkGemLevels"][0][
                    "activeState"
                ] = "inactive"
                result = evaluate_flame_link(chain, self.table)
                self.assertTrue(result.available, result.reasons)
                self.assertEqual(result.effectiveFlameLinkLevel, expected)


if __name__ == "__main__":
    unittest.main()
