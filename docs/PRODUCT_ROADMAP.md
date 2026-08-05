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
- [PROOF-002 - Windows desktop packaging](proofs/PROOF-002-desktop-packaging.md)
  adopts PyInstaller 6.21.0 with named clean-machine and egress limitations.

## Ordered phases

| Order | Phase and intended outcome | Exit condition |
| --- | --- | --- |
| 1 | **First-release evidence-pack PR.** Deliver AUD-002 (permanent Mercenary passive-sheet contract), AUD-003 (Light Radius and direct Link Skill Buff Effect source contract), AUD-004 (Flame Link data and calculation contract), and AUD-005 (Enmity's Embrace calculation contract) sequentially as separate evidence records in one coherent PR. | All four audit deliverables are structurally complete **and every load-bearing claim required by the scoped downstream result, including exact upstream contract/version dependencies, is confirmed or supported.** A provisional, unknown, superseded, or version-mismatched dependency withholds its dependent result. |
| 2 | **Desktop packaging PROOF consuming the adopted importer.** Test a Windows-first offline package that includes the adopted `golden_glory_lab.pob_import` module, calls `importPobRawXml` or `importPobShareCode`, and parses a permanent synthetic fixture inside the package. | The package runs the retained importer and its regression behavior from the packaged runtime without adding a second importer, selecting a framework by assumption, or implementing gated Flame Link/Enmity mechanics. |
| 3 | **First usable desktop BUILD.** Extend the adopted packaged shell and importer with explicit item-set mapping, only mechanics whose exact claim/version gates are satisfied, local persistence, UI, and evidence-aware target/gap/cap/surplus reporting. | A user can complete the first-release workflow and save/reopen local build state, while blocked mechanics remain explicit unavailable/review states. |
| 4 | **Completeness review and improvement patches.** Add reviewed/unreviewed and intentionally unused states, one-slot suggestions, and small multi-slot patches that preserve locked items and requirements. | Constraint-aware review explains practical changes without rewarding already-satisfied objectives. |
| 5 | **Critical-strike audit and panel.** Keep critical-strike reconstruction independent and add a panel only after its dedicated audit. | The panel is bounded by its evidence and does not create a combined score. |
| 6 | **Product hardening.** Strengthen the validated product through ordinary-user feedback, regression coverage, and release-readiness work. | Known first-release risks are resolved or explicitly accepted. |

## Current Phase 1 status

The first-release evidence pack is structurally complete as an AUDIT task, but
Phase 1 exit is not achieved: load-bearing dependencies remain unknown or
version-mismatched for the scoped mechanics results. The evidence-integrity repair adds regression guards for the recorded contracts, but it does not change any exit status or authorize a BUILD calculation.

The evidence pack is structurally complete, but it does not yet authorize the affected BUILD calculation.

The narrow evidence-batching and proof-adoption rules remain in
[the audit workflow](AUDIT_WORKFLOW.md). The owner has decided that no
standalone best-of-two workflow PR (formerly considered as PR B) is currently
required. Best-of-two ChatGPT review remains a flexible human practice outside
repository policy. A broader workflow document should be added only if an
actual coordination problem later justifies it; this is an intentional scope
decision, not forgotten roadmap work.

## Current Phase 2 status

[PROOF-002](proofs/PROOF-002-desktop-packaging.md) answers the packaging
question with PASS WITH LIMITATIONS and ADOPT WITH NAMED LIMITATIONS. The
adopted public importer runs from a copied PyInstaller one-directory bundle
without a source checkout or ambient Python path. A Python-free clean-machine
run and directly enforced outbound-network denial remain named limitations.

## Current Phase 3 status

Phase 3 is in progress. [BUILD-001](builds/BUILD-001-desktop-intake-mapping.md)
delivers the offline desktop intake, source-order item-set review, explicit
Player/Mercenary mapping, opaque manual Mercenary equipment, and deterministic
local save/open workflow.

[BUILD-002](builds/BUILD-002-copied-item-enmity.md) adds bounded copied-item
recognition with exact source preservation, a common provenance-aware item
review over PoB/copied/manual sources, exact claim/contract/status/polarity/
policy gates, build-state v2 migration, and only the authorized manual isolated
`Enmity’s own Fire Penetration contribution` with Enmity-only targets. OQ-007
is resolved only to that bounded recognition contract.

Phase 3 is not complete. OQ-002 through OQ-006 remain open. Derived permanent-
Mercenary values, component addition, Enmity's resistance-penalty
reconstruction, aggregate penetration, Light Radius, Golden Glory, Flame Link,
damage, DPS, recommendations, and a combined score remain blocked and
nonnumeric.

## Roadmap guardrails

- Do not recreate Path of Building outside the agreed import boundary.
- Reuse the adopted importer seam and regression suite; replacement requires
  explicit technical rationale and review.
- BUILD consumers must inspect exact claim/version gates and render
  unavailable/review states rather than infer missing mechanics.
- Do not introduce a combined build score or make theoretical maximums the
  primary objective.
- Do not require comprehensive Mercenary DPS before the first usable product.
- Do not add runtime scraping or authenticated account access without a
  separate decision.
- Do not build infrastructure without an ordinary user consumer.
- Do not block the first release on optional critical-strike or spell modeling.
