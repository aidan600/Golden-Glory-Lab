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


if __name__ == "__main__":
    unittest.main()
