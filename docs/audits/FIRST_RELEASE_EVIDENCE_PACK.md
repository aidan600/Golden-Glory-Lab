# First-release evidence-pack status

## Task status

The first-release evidence-pack task covers [AUD-002](AUD-002.md),
[AUD-003](AUD-003.md), [AUD-004](AUD-004.md), and
[AUD-005](AUD-005.md). Each audit now has a versioned claim contract, material
sources in the [source registry](../../data/sources/registry.json), minimal
curated reference and/or synthetic gate material where appropriate, and
repository validation coverage.

The evidence-pack workstream/deliverable is structurally complete. Individual
unknown, provisional, superseded, or version-mismatched claims remain
downstream output gates. Those gates carry forward into Phase 3 and withhold
only their dependent automatic calculations. They do not reopen the
evidence-pack task and do not block manual-first or unrelated Phase 3 work.

This structural completion is not an implementation approval of every gated
mechanics result. Unsatisfied claim gates continue to withhold only their
dependent automatic outputs.

## Evidence-integrity repair

The pack is protected by `node scripts/validate/check_first_release_evidence_pack.mjs`:
it invokes a pinned isolated Draft 2020-12 validator for all ten artifacts and then
checks claim-inventory polarity, source manifests, source/claim containment, separate policy prerequisites, ordinal capability thresholds/ranks, Enmity locators, synthetic formula cases, withheld Flame Link fixture states, and real negative mutations. These regression guards make the existing evidence
contract reviewable; they do not upgrade any mechanics conclusion or reopen the
evidence-pack deliverable.

## Phase and downstream-gate status

Phase 1 is complete as the first-release evidence-pack deliverable. A supported
audit headline does not promote its unknown, provisional, superseded, or
version-mismatched load-bearing claims to supported mechanics. A downstream
consumer must inspect the exact claim and contract-version dependencies
recorded by each audit. Unresolved dependencies withhold only their dependent
automatic outputs; they do not require reopening Phase 1.

| Audit | Record status | Narrowly supported | Load-bearing gate that remains |
| --- | --- | --- | --- |
| [AUD-002](AUD-002.md) | blocked | Permanent-Mercenary/info-sheet scope and a manual-final-value safety contract. | `C03-C05` block derived sheet or sheet-plus-equipment values. `C06` is the separate adopted manual-input safety policy; it permits only manual final values with explicit context and inclusion state. |
| [AUD-003](AUD-003.md) | supported | Pinned Default-tree recognition and literal Golden Glory/direct-Link source facts. | `C08` leaves Powerful Bond unknown only when selected; `C12` withholds complete source coverage, arithmetic, stacking, activation, rounding, and a scaled result. |
| [AUD-004](AUD-004.md) | supported | Flame Link reference/ordinary-level facts, target eligibility, quality display, and reporting-state boundary. | `C09-C10` withhold a definitive scaled result; `C08` separately gates exceptional levels, and the 3.29.0 supporting source remains version-mismatched to the 3.29.1 target. |
| [AUD-005](AUD-005.md) | supported | Explicit-Enmity-equipped, same-context, integral manual `U`/`M` isolated arithmetic and Enmity-only target reporting. | `C05-C07` and AUD-002 `C03-C05` block penalty derivation, sheet-derived values, aggregation, enemy resistance, damage, and DPS. |

## Authorized boundaries

The pack establishes audit records, reference/review states, manual-input
contracts, and synthetic fixture behavior. It does **not** authorize any of
the following:

- a derived permanent-Mercenary sheet value or a sheet-plus-equipment result;
- a definitive scaled Flame Link granted-damage result, DPS, or total Mercenary
  damage;
- total Fire Penetration, enemy effective resistance, Enmity damage, or an
  ownership/availability inference; or
- a combined build score.

AUD-005 established the bounded manual isolated Enmity formula contract.
[BUILD-002](../builds/BUILD-002-copied-item-enmity.md) now consumes that
contract. The implemented output is Enmity’s own isolated contribution and
Enmity-only target reporting. It still requires manual, integral, same-state
final values and `enmity.equipped-state=equipped`. It is not a derived
Mercenary-sheet result and is not a license to infer those values from a sheet
or item text. Derived sheet inputs, penalty derivation, aggregation, enemy
resistance, damage, and DPS remain gated.

## Active versus deferred evidence

### Active first-release evidence work

Current priorities are [OQ-004](../OPEN_QUESTIONS.md) and
[OQ-005](../OPEN_QUESTIONS.md):

- Golden Glory conversion and activation;
- direct Link Skill Buff Effect treatment;
- Flame Link required inputs, scaling, and rounding.

### Deferred evidence for later automation

The following remain documented needs for deferred automatic features only.
They are not the current first-release evidence request and do not block the
manual Enmity path or unrelated Phase 3 work:

- [OQ-002](../OPEN_QUESTIONS.md) / [OQ-003](../OPEN_QUESTIONS.md): automatic
  Mercenary-sheet labels, semantics, equipment inclusion, and comparison
  context (future controlled sheet captures when that automation resumes);
- [OQ-006](../OPEN_QUESTIONS.md): derived or aggregate Enmity work (future
  Enmity-equipped before/after observations for penalty order, display
  precision, and rounding when that path resumes).

See [CURRENT_STATE.md](../CURRENT_STATE.md) and
[DEC-003](../decisions/DEC-003-manual-first-input-boundaries.md).

## Source and rights posture

`3.29.1` is a target-version freeze, not proof that older or supporting
records remained unchanged in live game data. The audit records identify the
specific official, PoB, extracted/community, and derived-policy source IDs;
the registry preserves their provenance, limitations, and access date.

Only minimal factual references, source locators, product contracts, and
original synthetic fixtures are retained. Raw upstream tables, copied pages,
assets, and player data are not vendored. PoB's software licence and PoEDB's
site-content terms do not establish redistribution rights for underlying game
data. Retention and redistribution therefore remain a legal/policy governance
decision rather than an affirmative licence conclusion.

## Packaging status

[PROOF-002](../proofs/PROOF-002-desktop-packaging.md) completed the Windows
desktop packaging proof and was adopted with named limitations.
[BUILD-001](../builds/BUILD-001-desktop-intake-mapping.md) and
[BUILD-002](../builds/BUILD-002-copied-item-enmity.md) consume that adopted
packaging path. The remaining Python-free clean-machine and enforced-egress
limitations are still real, but packaging is not the next roadmap task.
