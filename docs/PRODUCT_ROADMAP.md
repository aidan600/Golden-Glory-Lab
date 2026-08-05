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
| 1 | **First-release evidence-pack PR.** Deliver AUD-002 (permanent Mercenary passive-sheet contract), AUD-003 (Light Radius and direct Link Skill Buff Effect source contract), AUD-004 (Flame Link data and calculation contract), and AUD-005 (Enmity's Embrace calculation contract) sequentially as separate evidence records in one coherent PR. | All four audit records are structurally complete, exact claim/version dependencies are machine-readable, and unresolved dependencies explicitly withhold only their dependent outputs. |
| 2 | **Desktop packaging PROOF consuming the adopted importer.** Test a Windows-first offline package that includes the adopted `golden_glory_lab.pob_import` module, calls `importPobRawXml` or `importPobShareCode`, and parses a permanent synthetic fixture inside the package. | The package runs the retained importer and its regression behavior from the packaged runtime without adding a second importer, selecting a framework by assumption, or implementing gated Flame Link/Enmity mechanics. |
| 3 | **First usable desktop BUILD.** Extend the adopted packaged shell and importer with explicit item-set mapping, only mechanics whose exact claim/version gates are satisfied, local persistence, UI, and evidence-aware target/gap/cap/surplus reporting. | A user can complete the first-release workflow and save/reopen local build state, while blocked mechanics remain explicit unavailable/review states. |
| 4 | **Completeness review and improvement patches.** Add reviewed/unreviewed and intentionally unused states, one-slot suggestions, and small multi-slot patches that preserve locked items and requirements. | Constraint-aware review explains practical changes without rewarding already-satisfied objectives. |
| 5 | **Critical-strike audit and panel.** Keep critical-strike reconstruction independent and add a panel only after its dedicated audit. | The panel is bounded by its evidence and does not create a combined score. |
| 6 | **Product hardening.** Strengthen the validated product through ordinary-user feedback, regression coverage, and release-readiness work. | Known first-release risks are resolved or explicitly accepted. |

## Current Phase 1 status

Phase 1 is complete as the first-release evidence-pack deliverable. All four
audit records are structurally complete, exact claim/version dependencies are
machine-readable, and unresolved dependencies explicitly withhold only their
dependent automatic outputs.

Some load-bearing claims remain unsatisfied. Those claims remain exact
downstream gates. Their dependent automatic mechanics remain unavailable.
Phase 1 does not need to be reopened. Manual-first and unrelated Phase 3 work
may proceed. The evidence-integrity repair adds regression guards for the
recorded contracts; it does not upgrade claim statuses or authorize gated
automatic results that remain unknown, provisional, superseded, or
version-mismatched.

See [first-release evidence-pack status](audits/FIRST_RELEASE_EVIDENCE_PACK.md)
and [CURRENT_STATE.md](CURRENT_STATE.md).

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

Phase 3 is in progress. See [CURRENT_STATE.md](CURRENT_STATE.md) for the
operational summary and
[DEC-003](decisions/DEC-003-manual-first-input-boundaries.md) for the
manual-first input boundary.

[BUILD-001](builds/BUILD-001-desktop-intake-mapping.md) is merged. It delivers
offline desktop intake, source-order item-set review, explicit Player/Mercenary
mapping, opaque manual Mercenary equipment, and deterministic local save/open.

[BUILD-002](builds/BUILD-002-copied-item-enmity.md) is merged. It adds bounded
copied-item recognition, common PoB/copied/manual review, exact evidence gates,
build-state v2 migration, and the authorized manual isolated Enmity
contribution with Enmity-only target, gap, surplus, cap, and input-beyond-cap
reporting. That manual isolated Enmity path satisfies the first-release
Mercenary Enmity fallback. OQ-007 is resolved only to the bounded recognition
contract.

Automatic Mercenary-sheet derivation is deferred and nonblocking for the first
release. OQ-002 and OQ-003 remain deferred evidence work for that future
automation only. OQ-006 retains only derived or aggregate Enmity questions;
the isolated manual result is implemented.

OQ-004 and OQ-005 are the active mechanics work for the player-side Light
Radius → Golden Glory, direct Link Skill Buff Effect, and Flame Link damage
granted chain. The intended next BUILD is a manual-first player calculation
chain with progressive recognition and labelled manual contribution entries.

Phase 3 remains incomplete until that player-side chain and the ordinary
first-release workflow are usable. Blocked derived Mercenary values, aggregate
penetration, unproven player-chain formulas, DPS labelling, recommendations,
and a combined score remain unavailable and nonnumeric. Unsatisfied Phase 1
claim gates carry forward as exact downstream output gates only; they do not
reopen the evidence-pack deliverable.

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
