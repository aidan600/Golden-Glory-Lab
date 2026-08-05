from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from runpy import run_path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from golden_glory_lab.domain import (  # noqa: E402
    DECIMAL_DIGIT_LIMIT,
    ENMITY_OUTPUT_ID,
    ENMITY_TARGET_OUTPUT_ID,
    DecimalInputError,
    evaluate_enmity,
    parse_decimal_text,
)
from golden_glory_lab.evidence_gate import (  # noqa: E402
    GateDecision,
    GateReason,
    RuntimeResourceError,
    evaluate_output,
    load_gate_manifest,
    parse_enmity_reference_bytes,
    parse_gate_manifest_bytes,
)
_manifest_validator = run_path(
    str(ROOT / "scripts" / "validate" / "run_runtime_evidence_manifest.py")
)
MANIFEST_PATH = _manifest_validator["MANIFEST_PATH"]
ManifestValidationError = _manifest_validator["ManifestValidationError"]
validate_manifest = _manifest_validator["validate_manifest"]

MECHANICS_FIXTURE = (
    ROOT / "fixtures" / "mechanics" / "aud-005-enmitys-embrace-gates-v1.json"
)


def manifest_json() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def parsed_mutation(value: dict):
    return parse_gate_manifest_bytes(
        (json.dumps(value, separators=(",", ":")) + "\n").encode("utf-8"),
        verify_pinned_hash=False,
    )


def complete_context() -> dict[str, str]:
    return {
        "mercenaryIdentityLevel": "Synthetic permanent Mercenary, level 90",
        "activeStateSelection": "Active combat state recorded",
        "zoneOrUiContext": "Hideout character UI",
        "relevantEffectsConditions": "No temporary resistance effects",
        "equipmentStateDescription": "Enmity equipped in Ring 1",
        "captureTimingDescription": "Captured after UI refresh",
    }


def complete_input(**overrides: object) -> dict:
    value = {
        "finalUncappedFireResistance": "300",
        "maximumFireResistance": "75",
        "equippedState": "equipped",
        "equipmentInclusionState": "unknown",
        "measurementContext": complete_context(),
        "targetGameVersionAcknowledgement": "confirmed-3.29.1",
        "observedItemReference": None,
        "target": "200",
    }
    value.update(overrides)
    return value


def passing_gates():
    manifest = load_gate_manifest()
    return (
        evaluate_output(manifest, ENMITY_OUTPUT_ID),
        evaluate_output(manifest, ENMITY_TARGET_OUTPUT_ID),
    )


def failed_gate(output_id: str, *, state: str = "unavailable") -> GateDecision:
    return GateDecision(
        outputId=output_id,
        available=False,
        state=state,
        value=None,
        reasons=(
            GateReason(
                code="SYNTHETIC_GATE_FAILURE",
                message="Synthetic exact gate failure",
                outputId=output_id,
                auditId="AUD-005",
                contractVersion="1.0.0",
                claimId="AUD-005-C03",
                unmetBehavior="withhold-requested-output",
            ),
        ),
        claimReferences=("AUD-005-C03",),
    )


class RuntimeEvidenceGateTests(unittest.TestCase):
    def test_exact_manifest_and_both_outputs_pass(self) -> None:
        report = validate_manifest()
        self.assertEqual(report["status"], "PASS")
        manifest = load_gate_manifest()
        main = evaluate_output(manifest, ENMITY_OUTPUT_ID)
        target = evaluate_output(manifest, ENMITY_TARGET_OUTPUT_ID)
        self.assertTrue(main.available)
        self.assertTrue(target.available)
        self.assertIsNone(main.value)
        self.assertEqual(
            set(main.claimReferences),
            {"AUD-005-C03", "AUD-005-C04", "AUD-002-C06"},
        )

    def test_missing_wrong_audit_contract_and_claim_id_have_exact_reasons(self) -> None:
        cases = []
        missing = manifest_json()
        missing["claims"] = [
            claim for claim in missing["claims"] if claim["claimId"] != "AUD-005-C03"
        ]
        cases.append((missing, "MISSING_CLAIM"))

        wrong_audit = manifest_json()
        wrong_audit["claims"][0]["auditId"] = "AUD-999"
        cases.append((wrong_audit, "AUDIT_ID_MISMATCH"))

        wrong_contract = manifest_json()
        wrong_contract["claims"][0]["contractVersion"] = "9.9.9"
        cases.append((wrong_contract, "CONTRACT_VERSION_MISMATCH"))

        wrong_claim = manifest_json()
        wrong_claim["outputs"][0]["requirements"][0]["claimId"] = "AUD-005-C99"
        cases.append((wrong_claim, "MISSING_CLAIM"))

        for mutation, expected_code in cases:
            with self.subTest(code=expected_code):
                decision = evaluate_output(parsed_mutation(mutation), ENMITY_OUTPUT_ID)
                self.assertFalse(decision.available)
                self.assertIn(expected_code, {reason.code for reason in decision.reasons})
                self.assertIsNone(decision.value)

    def test_polarity_status_ordering_and_failed_statuses(self) -> None:
        wrong_polarity = manifest_json()
        wrong_polarity["claims"][0]["gatePolarity"] = "product-policy"
        decision = evaluate_output(parsed_mutation(wrong_polarity), ENMITY_OUTPUT_ID)
        self.assertIn("GATE_POLARITY_MISMATCH", {reason.code for reason in decision.reasons})

        confirmed = manifest_json()
        confirmed["claims"][0]["currentClaimStatus"] = "confirmed"
        self.assertTrue(evaluate_output(parsed_mutation(confirmed), ENMITY_OUTPUT_ID).available)

        confirmed_minimum = manifest_json()
        confirmed_minimum["outputs"][0]["requirements"][0]["minimumStatus"] = "confirmed"
        decision = evaluate_output(parsed_mutation(confirmed_minimum), ENMITY_OUTPUT_ID)
        self.assertIn("CLAIM_STATUS_BELOW_MINIMUM", {reason.code for reason in decision.reasons})
        confirmed_minimum["claims"][0]["currentClaimStatus"] = "confirmed"
        self.assertTrue(
            evaluate_output(parsed_mutation(confirmed_minimum), ENMITY_OUTPUT_ID).available
        )

        for status in ("provisional", "unknown", "superseded"):
            mutation = manifest_json()
            mutation["claims"][0]["currentClaimStatus"] = status
            decision = evaluate_output(parsed_mutation(mutation), ENMITY_OUTPUT_ID)
            with self.subTest(status=status):
                self.assertFalse(decision.available)
                self.assertIn(
                    "CLAIM_STATUS_UNAVAILABLE",
                    {reason.code for reason in decision.reasons},
                )

    def test_policy_modes_are_explicit_and_not_ordinal(self) -> None:
        missing_policy = manifest_json()
        missing_policy["claims"] = [
            claim
            for claim in missing_policy["claims"]
            if claim["claimId"] != "AUD-002-C06"
        ]
        decision = evaluate_output(parsed_mutation(missing_policy), ENMITY_OUTPUT_ID)
        self.assertIn("MISSING_CLAIM", {reason.code for reason in decision.reasons})

        wrong_mode = manifest_json()
        policy = next(
            claim for claim in wrong_mode["claims"] if claim["claimId"] == "AUD-002-C06"
        )
        policy["policyMode"] = "requires-applicable-policy"
        decision = evaluate_output(parsed_mutation(wrong_mode), ENMITY_OUTPUT_ID)
        self.assertIn("POLICY_MODE_MISMATCH", {reason.code for reason in decision.reasons})
        requirement = next(
            value
            for value in load_gate_manifest().outputs[0].requirements
            if value.claimId == "AUD-002-C06"
        )
        self.assertIsNone(requirement.minimumStatus)
        self.assertIsNone(requirement.gateMode)

    def test_version_mismatch_and_smallest_output_withdrawal(self) -> None:
        manifest = load_gate_manifest()
        decision = evaluate_output(
            manifest,
            ENMITY_OUTPUT_ID,
            target_game_version="Path of Exile 1 9.9.9",
        )
        self.assertEqual(decision.state, "version-mismatched")
        self.assertIsNone(decision.value)

        target_policy_failure = manifest_json()
        claim = next(
            value
            for value in target_policy_failure["claims"]
            if value["claimId"] == "AUD-005-C10"
        )
        claim["currentClaimStatus"] = "provisional"
        mutated = parsed_mutation(target_policy_failure)
        self.assertTrue(evaluate_output(mutated, ENMITY_OUTPUT_ID).available)
        self.assertFalse(evaluate_output(mutated, ENMITY_TARGET_OUTPUT_ID).available)

    def test_consumer_pin_and_source_byte_hash_mutations_fail(self) -> None:
        with self.assertRaises(RuntimeResourceError) as raised:
            parse_gate_manifest_bytes(MANIFEST_PATH.read_bytes() + b" ")
        self.assertEqual(raised.exception.code, "RUNTIME_MANIFEST_HASH_MISMATCH")
        with self.assertRaises(ManifestValidationError):
            validate_manifest(
                source_overrides={
                    "docs/audits/AUD-005.md": (
                        ROOT / "docs" / "audits" / "AUD-005.md"
                    ).read_bytes()
                    + b"\n"
                }
            )

    def test_reference_loader_rejects_consumed_contract_cap_and_policy_mutations(self) -> None:
        path = (
            ROOT
            / "src"
            / "golden_glory_lab"
            / "runtime_data"
            / "enmity-reference-v1.json"
        )
        source = json.loads(path.read_text(encoding="utf-8"))
        mutations = []
        wrong_contract = json.loads(json.dumps(source))
        wrong_contract["contractVersion"] = "9.9.9"
        mutations.append(wrong_contract)
        wrong_cap = json.loads(json.dumps(source))
        wrong_cap["itemSpecificCapPercent"] = 201
        mutations.append(wrong_cap)
        wrong_policy = json.loads(json.dumps(source))
        wrong_policy["observedValuePolicy"]["provesOwnership"] = True
        mutations.append(wrong_policy)
        bad_claim = json.loads(json.dumps(source))
        bad_claim["claimReferences"] = ["AUD-005-C01", "AUD-005-C01"]
        mutations.append(bad_claim)
        for mutation in mutations:
            data = (json.dumps(mutation, separators=(",", ":")) + "\n").encode()
            with self.subTest(mutation=mutation), self.assertRaises(
                RuntimeResourceError
            ):
                parse_enmity_reference_bytes(data, verify_pinned_hash=False)

    def test_runtime_resource_failure_withdraws_only_dependent_recognition_and_output(self) -> None:
        from golden_glory_lab.desktop.service import ApplicationService

        failure = RuntimeResourceError("RUNTIME_RESOURCE_MISSING", "synthetic missing")
        with patch(
            "golden_glory_lab.desktop.service.load_runtime_bundle",
            side_effect=failure,
        ):
            service = ApplicationService()
            outcome = service.attempt_raw_xml(
                ROOT / "fixtures" / "pob" / "proof" / "equivalent.xml"
            )
            self.assertEqual(outcome, "imported")
            service.add_copied_entry(
                "Item Class: Rings\nRarity: Unique\nEnmity's Embrace\nVermillion Ring\n"
            )
            review = service.item_reviews(provenance="copied-text")[0]
            self.assertIsNone(review.referenceMatch)
            self.assertIsNotNone(review.parsedIdentity)
            result = service.enmity_result()
            self.assertFalse(result.available)
            self.assertIsNone(result.value)
            self.assertEqual(
                service.runtime_evidence_status()["resourceError"]["code"],
                "RUNTIME_RESOURCE_MISSING",
            )
            self.assertTrue(service.item_sets())
            self.assertTrue(service.canonical_bytes)


class DecimalInputTests(unittest.TestCase):
    def test_exact_grammar_lexeme_preservation_and_integrality(self) -> None:
        for value, integral in (
            ("0", True),
            ("-0", True),
            ("00075.00", True),
            ("-60", True),
            ("75.5", False),
        ):
            with self.subTest(value=value):
                parsed = parse_decimal_text(value)
                self.assertEqual(parsed.lexeme, value)
                self.assertEqual(parsed.integral, integral)

    def test_rejected_decimal_forms_and_digit_bound(self) -> None:
        rejected = (
            " 75",
            "75 ",
            "+75",
            "1e2",
            "1E2",
            "1.",
            ".5",
            "--1",
            "NaN",
            "Infinity",
            "1,5",
            "１２",
            "1 2",
        )
        for value in rejected:
            with self.subTest(value=value), self.assertRaises(DecimalInputError):
                parse_decimal_text(value)
        self.assertEqual(
            len(parse_decimal_text("9" * DECIMAL_DIGIT_LIMIT).lexeme),
            DECIMAL_DIGIT_LIMIT,
        )
        with self.assertRaises(DecimalInputError) as raised:
            parse_decimal_text("9" * (DECIMAL_DIGIT_LIMIT + 1))
        self.assertEqual(raised.exception.code, "DECIMAL_TEXT_DIGIT_LIMIT")


class EnmityDomainTests(unittest.TestCase):
    def setUp(self) -> None:
        self.main_gate, self.target_gate = passing_gates()

    def evaluate(self, **overrides: object):
        return evaluate_enmity(
            complete_input(**overrides), self.main_gate, self.target_gate
        )

    def test_every_applicable_aud005_numeric_fixture_case(self) -> None:
        fixture = json.loads(MECHANICS_FIXTURE.read_text(encoding="utf-8"))
        expected_ids = {
            "enmity-manual-no-overcap",
            "enmity-manual-one-point-overcap",
            "enmity-manual-item-cap",
            "enmity-manual-input-beyond-item-cap",
            "enmity-manual-nonpositive-overcap",
        }
        records = {
            record["id"]: record
            for record in fixture["records"]
            if record["id"] in expected_ids
        }
        self.assertEqual(set(records), expected_ids)
        for identifier, record in records.items():
            sources = record["data"].get("inputCases") or [record["data"]["input"]]
            expected = record["data"]["expected"]
            for source in sources:
                result = self.evaluate(
                    finalUncappedFireResistance=str(source["U"]),
                    maximumFireResistance=str(source["M"]),
                )
                with self.subTest(identifier=identifier, u=source["U"]):
                    self.assertEqual(result.state, "available")
                    self.assertEqual(result.overcap, expected["overcap"])
                    self.assertEqual(
                        result.value, expected["enmityOwnFirePenetration"]
                    )
                    self.assertEqual(
                        result.inputBeyondCap,
                        expected.get("inputBeyondCap", 0),
                    )

    def test_zero_and_negative_manual_values_are_not_clamped_inputs(self) -> None:
        for u in ("0", "-60"):
            result = self.evaluate(finalUncappedFireResistance=u)
            with self.subTest(u=u):
                self.assertTrue(result.available)
                self.assertEqual(result.overcap, 0)
                self.assertEqual(result.value, 0)
                self.assertEqual(result.inputLexemes["U"], u)

    def test_available_computed_zero_is_distinct_from_every_unavailable_null(self) -> None:
        zero = self.evaluate(
            finalUncappedFireResistance="75", maximumFireResistance="75"
        )
        self.assertTrue(zero.available)
        self.assertEqual(zero.state, "available")
        self.assertEqual(zero.value, 0)

        unavailable = self.evaluate(equippedState="unknown")
        self.assertFalse(unavailable.available)
        self.assertIsNone(unavailable.value)
        self.assertNotEqual(unavailable.state, "available")

    def test_result_state_precedence(self) -> None:
        not_equipped = evaluate_enmity(
            complete_input(equippedState="not-equipped"),
            failed_gate(ENMITY_OUTPUT_ID),
            failed_gate(ENMITY_TARGET_OUTPUT_ID),
        )
        self.assertEqual(not_equipped.state, "not-applicable")
        self.assertIsNone(not_equipped.value)

        self.assertEqual(self.evaluate(equippedState="unknown").state, "unavailable")
        gated = evaluate_enmity(
            complete_input(),
            failed_gate(ENMITY_OUTPUT_ID),
            self.target_gate,
        )
        self.assertEqual(gated.state, "unavailable")
        self.assertEqual(gated.reasons[0]["code"], "SYNTHETIC_GATE_FAILURE")
        self.assertEqual(
            self.evaluate(targetGameVersionAcknowledgement="other-version").state,
            "version-mismatched",
        )
        self.assertEqual(
            self.evaluate(targetGameVersionAcknowledgement="unknown").state,
            "unavailable",
        )
        self.assertEqual(
            self.evaluate(finalUncappedFireResistance=None).state, "missing"
        )
        self.assertEqual(self.evaluate(maximumFireResistance=None).state, "missing")
        self.assertEqual(
            self.evaluate(measurementContext={**complete_context(), "zoneOrUiContext": ""}).state,
            "manually-required",
        )
        self.assertEqual(
            self.evaluate(equipmentInclusionState="unrecorded").state,
            "manually-required",
        )
        self.assertEqual(
            self.evaluate(finalUncappedFireResistance="300.5").state,
            "rounding-evidence-required",
        )
        self.assertEqual(
            self.evaluate(maximumFireResistance="75.25").state,
            "rounding-evidence-required",
        )

    def test_recorded_unknown_inclusion_is_eligible(self) -> None:
        result = self.evaluate(equipmentInclusionState="unknown")
        self.assertTrue(result.available)
        self.assertEqual(result.value, 200)

    def test_integral_target_states_and_formulas(self) -> None:
        below = self.evaluate(target="-1")
        self.assertEqual(below.target.state, "invalid-target")
        above = self.evaluate(target="201")
        self.assertEqual(above.target.state, "unreachable-by-Enmity")

        for target, gap, surplus, headroom in (
            ("0", 0, 200, 0),
            ("150", 0, 50, 0),
            ("200", 0, 0, 0),
        ):
            result = self.evaluate(target=target)
            with self.subTest(target=target):
                self.assertEqual(result.target.state, "available")
                self.assertEqual(result.target.gap, gap)
                self.assertEqual(result.target.surplus, surplus)
                self.assertEqual(result.target.capHeadroom, headroom)

        lower_contribution = self.evaluate(
            finalUncappedFireResistance="175", target="150"
        )
        self.assertEqual(lower_contribution.value, 100)
        self.assertEqual(lower_contribution.target.gap, 50)
        self.assertEqual(lower_contribution.target.surplus, 0)
        self.assertEqual(lower_contribution.target.capHeadroom, 100)

    def test_fractional_or_failed_target_never_withdraws_contribution(self) -> None:
        fractional = self.evaluate(target="199.5")
        self.assertTrue(fractional.available)
        self.assertEqual(fractional.value, 200)
        self.assertEqual(fractional.target.state, "invalid-target")
        self.assertEqual(fractional.target.targetLexeme, "199.5")

        target_gated = evaluate_enmity(
            complete_input(),
            self.main_gate,
            failed_gate(ENMITY_TARGET_OUTPUT_ID),
        )
        self.assertTrue(target_gated.available)
        self.assertEqual(target_gated.value, 200)
        self.assertFalse(target_gated.target.state == "available")
        self.assertIsNone(target_gated.target.gap)


class ExactIntegralArithmeticTests(unittest.TestCase):
    def setUp(self) -> None:
        self.main_gate, self.target_gate = passing_gates()

    def _evaluate(self, u: str, m: str = "0", **overrides: object):
        return evaluate_enmity(
            complete_input(
                finalUncappedFireResistance=u,
                maximumFireResistance=m,
                **overrides,
            ),
            self.main_gate,
            self.target_gate,
        )

    def _assert_exact_cases(self) -> None:
        thirty = "9" * 30
        result = self._evaluate(thirty, "0")
        self.assertTrue(result.available)
        self.assertEqual(result.overcap, int(thirty))
        self.assertEqual(result.value, 200)
        self.assertEqual(result.inputBeyondCap, int(thirty) - 200)
        self.assertEqual(result.inputLexemes["U"], thirty)

        huge = "9" * DECIMAL_DIGIT_LIMIT
        result = self._evaluate(huge, "0")
        self.assertTrue(result.available)
        self.assertEqual(result.overcap, int(huge))
        self.assertEqual(result.value, 200)
        self.assertEqual(result.inputBeyondCap, int(huge) - 200)
        self.assertEqual(result.inputLexemes["U"], huge)

        left = "1" + "0" * 127
        right = "9" * 127
        self.assertEqual(len(left), DECIMAL_DIGIT_LIMIT)
        result = self._evaluate(left, right)
        self.assertTrue(result.available)
        self.assertEqual(result.overcap, 1)
        self.assertEqual(result.value, 1)
        self.assertEqual(result.inputBeyondCap, 0)
        self.assertEqual(result.inputLexemes["U"], left)
        self.assertEqual(result.inputLexemes["M"], right)

        negative = "-" + "9" * 30
        result = self._evaluate(negative, "0")
        self.assertTrue(result.available)
        self.assertEqual(result.overcap, 0)
        self.assertEqual(result.value, 0)
        self.assertEqual(result.inputBeyondCap, 0)
        self.assertEqual(result.inputLexemes["U"], negative)

        exact = self._evaluate("275", "75")
        self.assertEqual(exact.overcap, 200)
        self.assertEqual(exact.value, 200)
        self.assertEqual(exact.inputBeyondCap, 0)

        capped = self._evaluate("300", "75")
        self.assertEqual(capped.overcap, 225)
        self.assertEqual(capped.value, 200)
        self.assertEqual(capped.inputBeyondCap, 25)

        zero = self._evaluate("75", "75")
        self.assertTrue(zero.available)
        self.assertEqual(zero.value, 0)
        self.assertEqual(zero.overcap, 0)

    def test_large_integral_arithmetic_is_exact(self) -> None:
        self._assert_exact_cases()

    def test_large_integral_arithmetic_ignores_decimal_context_precision(self) -> None:
        import decimal

        context = decimal.getcontext()
        original = context.copy()
        try:
            for precision in (1, 9, 28, 100):
                with self.subTest(precision=precision):
                    context.prec = precision
                    self._assert_exact_cases()
        finally:
            decimal.setcontext(original)


if __name__ == "__main__":
    unittest.main()
