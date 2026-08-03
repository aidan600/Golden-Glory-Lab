# Product Roadmap

This roadmap describes the repository state after adoption of the reusable PoB
importer proof. It orders work toward a useful offline desktop application
without becoming a second product definition.

## Completed

- Repository workflow bootstrap is complete.
- [AUD-001 - PoB item-set import contract](audits/AUD-001.md) is merged as the
  accepted PoB import evidence boundary.
- The current [product direction](PRODUCT_DIRECTION.md) and roadmap are
  established.
- [PROOF-001 - reusable PoB importer](proofs/PROOF-001-pob-importer.md) is
  adopted with named limitations as the production-intent import seam.

## Ordered next phases

| Order | Phase and intended outcome | Exit condition |
| --- | --- | --- |
| 1 | **First-release evidence-pack PR.** Deliver AUD-002 (permanent Mercenary passive-sheet contract), AUD-003 (Light Radius and direct Link Skill Buff Effect source contract), AUD-004 (Flame Link data and calculation contract), and AUD-005 (Enmity's Embrace calculation contract) sequentially as separate evidence records in one coherent PR. | Each audit remains independently evidenced and ends with an implementation contract naming required inputs, established rules, unsupported/provisional/manually required behavior, evidence-backed tables or fixtures, and the expected downstream module or user flow. |
| 2 | **Desktop packaging PROOF consuming the adopted importer.** Test a Windows-first offline package that includes the actual adopted Python importer, calls the same public entry point, and parses a permanent fixture inside the package. | The package runs the retained importer and regression suite without adding a second importer or selecting a framework by assumption. |
| 3 | **First usable desktop BUILD.** Extend the adopted packaged shell and importer with explicit item-set mapping, audited mechanics, local persistence, UI, and basic target/gap/cap/surplus reporting. | A user can complete the first-release workflow and save/reopen local build state. |
| 4 | **Completeness review and improvement patches.** Add reviewed/unreviewed and intentionally unused states, one-slot suggestions, and small multi-slot patches that preserve locked items and requirements. | Constraint-aware review explains practical changes without rewarding already-satisfied objectives. |
| 5 | **Critical-strike audit and panel.** Keep critical-strike reconstruction independent and add a panel only after its dedicated audit. | The panel is bounded by its evidence and does not create a combined score. |
| 6 | **Product hardening.** Strengthen the validated product through ordinary-user feedback, regression coverage, and release-readiness work. | Known first-release risks are resolved or explicitly accepted. |

The narrow evidence-batching and proof-adoption rules remain in
[the audit workflow](AUDIT_WORKFLOW.md). The owner has decided that no
standalone best-of-two workflow PR (formerly considered as PR B) is currently
required. Best-of-two ChatGPT review remains a flexible human practice outside
repository policy. A broader workflow document should be added only if an
actual coordination problem later justifies it; this is an intentional scope
decision, not forgotten roadmap work.

## Roadmap guardrails

- Do not recreate Path of Building outside the agreed import boundary.
- Reuse the adopted importer seam and regression suite; replacement requires
  explicit technical rationale and review.
- Do not introduce a combined build score or make theoretical maximums the
  primary objective.
- Do not require comprehensive Mercenary DPS before the first usable product.
- Do not add runtime scraping or authenticated account access without a
  separate decision.
- Do not build infrastructure without an ordinary user consumer.
- Do not block the first release on optional critical-strike or spell modeling.
