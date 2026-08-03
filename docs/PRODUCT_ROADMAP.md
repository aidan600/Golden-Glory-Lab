# Product Roadmap

This roadmap describes the repository state after the product-direction and
roadmap documentation phase merges. It orders the work needed to reach a
useful offline desktop application without turning this roadmap into a second
product definition.

## Completed

- Repository workflow bootstrap is complete.
- [AUD-001 - PoB item-set import contract](audits/AUD-001.md) is merged as the
  accepted PoB import evidence boundary.
- PR A established the current [product direction](PRODUCT_DIRECTION.md) and
  this roadmap.

## Ordered next phases

| Order | Phase and intended outcome | Exit condition |
| --- | --- | --- |
| 1 | **PR B - implementation and best-of-two review workflow.** Record the intended implementation and review workflow for later changes. | The workflow outcome is documented without delaying the parser PROOF substantially. |
| 2 | **PoB parser PROOF.** Establish a framework-independent importer seam that accepts raw XML, uses a separate share-code adapter, emits deterministic neutral JSON, preserves the AUD-001 structures, reports malformed and unsupported input, enforces tested parser and resource limits, and never infers ownership. | A bounded, fixture-backed proof demonstrates the audited neutral intake and reporting seam. |
| 3 | **Permanent Mercenary passive-sheet audit.** Determine the exact manual fields and whether equipment or conditions are included. | An evidence-aware input contract identifies required fields and preserves unresolved limits. |
| 4 | **Light Radius source audit.** Establish the relevant, versioned player-source catalog. | Reviewed evidence defines the source coverage required for the initial Light Radius path. |
| 5 | **Flame Link audit.** Establish the data and mechanics boundary for the granted-damage path. | A bounded audit supports only the Flame Link calculation behavior that its evidence establishes. |
| 6 | **Enmity's Embrace audit.** Establish the overcap and Fire Penetration calculation boundary while preserving observed values. | A bounded audit supports only the Enmity behavior that its evidence establishes. |
| 7 | **Desktop packaging PROOF.** Test a Windows-first offline packaging approach before adopting a final desktop framework. | A bounded proof reports whether a local Windows-first package meets ordinary offline use, without selecting a framework by assumption. |
| 8 | **First usable desktop BUILD.** Deliver the ordinary local workflow with basic target, gap, cap, and surplus reporting. | A user can complete the first-release workflow in the product direction and save/reopen the resulting local build state. |
| 9 | **Completeness review and improvement patches.** Add reviewed/unreviewed and intentionally unused states, one-slot suggestions, and small multi-slot patches that preserve locked items and requirements. | Constraint-aware review can explain practical changes without rewarding already-satisfied objectives. |
| 10 | **Critical-strike audit and panel.** Keep critical-strike reconstruction independent and add a panel only after its dedicated audit. | The panel is bounded by its own evidence and does not create a combined build score. |
| 11 | **Product hardening.** Strengthen the validated product through ordinary-user feedback, regression coverage, and release-readiness work. | Known first-release risks are documented, prioritized, and either resolved or explicitly accepted. |

The parser PROOF is the next technical phase. PR B is a small documentation
phase immediately before it, not a reason to defer the proof.

## Roadmap guardrails

- Do not recreate Path of Building outside the agreed import boundary.
- Do not introduce a combined build score or make theoretical maximums the
  primary objective.
- Do not require comprehensive Mercenary DPS before the first usable product.
- Do not add runtime scraping or authenticated account access without a
  separate decision.
- Do not build infrastructure without an ordinary user consumer.
- Do not block the first release on optional critical-strike or spell modeling.
