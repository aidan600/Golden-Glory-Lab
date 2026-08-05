# Current State

## Purpose and authority

This document answers: what is implemented, what is active, and what is deferred
now?

It owns operational status only. It does not replace product scope, phase
ordering, audit conclusions, or settled decisions:

| Concern | Canonical owner |
| --- | --- |
| Where are we now | This document |
| Product scope | [PRODUCT_DIRECTION.md](PRODUCT_DIRECTION.md) |
| Phase ordering | [PRODUCT_ROADMAP.md](PRODUCT_ROADMAP.md) |
| Bounded audit, proof, or build conclusions | Their records under `docs/audits/`, `docs/proofs/`, and `docs/builds/` |
| Settled product choices | [Decision records](decisions/INDEX.md), especially [DEC-003](decisions/DEC-003-manual-first-input-boundaries.md) |

## Status date

2026-08-05

## Current main milestone

Phase 3 — first usable desktop BUILD — is in progress on `main` after
[BUILD-001](builds/BUILD-001-desktop-intake-mapping.md) and
[BUILD-002](builds/BUILD-002-copied-item-enmity.md).

## Merged outcomes

- **BUILD-001 (merged):** desktop intake; PoB raw XML and share-code import;
  source-order review; explicit Player and Mercenary mapping; opaque manual
  Mercenary equipment; deterministic local persistence.
- **BUILD-002 (merged):** copied-item recognition; common PoB/copied/manual
  review; exact evidence gates; build-state v2 migration; manual isolated
  Enmity contribution; Enmity-only target, gap, surplus, cap, and
  input-beyond-cap reporting.

## Current phase

Authoritative phase numbering (see [PRODUCT_ROADMAP.md](PRODUCT_ROADMAP.md)):

1. First-release evidence pack
2. Windows desktop packaging proof
3. First usable desktop BUILD — **in progress**
4. Completeness review and improvement patches
5. Critical-strike audit and panel
6. Product hardening

Older roadmaps that numbered AUD-001 as Phase 1, a parser as Phase 2, a
Mercenary-sheet audit as Phase 3, and the first product BUILD as Phase 6 are
historical snapshots only.

## Active product path

First-release player-side mechanics work:

    Light Radius
        -> Golden Glory contribution
    Direct Link Skill Buff Effect
        -> separate contribution
    Golden Glory contribution + direct Link contribution
        -> Flame Link damage granted

Active evidence work: [OQ-004](OPEN_QUESTIONS.md) and
[OQ-005](OPEN_QUESTIONS.md). That work determines only what is necessary to
implement this chain (conversion, activation, required inputs, scaling,
rounding, target-version applicability). Exhaustive source coverage is not a
prerequisite for a manual-first BUILD.

## Implemented manual fallbacks

BUILD-002’s manual isolated Enmity path is the first-release Mercenary Enmity
fallback. Missing mechanics evidence blocks automatic derivation, not manual
entry and not the entire product workflow.

Manual inputs must be labelled manual or user-attested, retain provenance and
context where needed, never be silently combined with uncertain derived
components, and remain distinct from confirmed mechanics-derived values.

## Nonblocking deferred automation

Automatic Mercenary-sheet derivation is deferred and nonblocking for the first
release. [OQ-002](OPEN_QUESTIONS.md) and [OQ-003](OPEN_QUESTIONS.md) are
nonblocking. Ordinary users are not required to submit screenshots. Realm,
mode, league, UI language, and display resolution are not product inputs.
Client version may be evidence metadata but is not normally a user input.

[PROOF-003](proofs/PROOF-003-mercenary-sheet-observation.md) is deferred before
observation. Unmerged local scaffolding existed but was not adopted or
imported.

## Active open questions

| ID | Role now |
| --- | --- |
| OQ-002 | Nonblocking; deferred — sheet labels/semantics for future automatic derivation |
| OQ-003 | Nonblocking; deferred — equipment inclusion/comparability for future automatic derivation |
| OQ-004 | Blocking; active — player-chain source/mechanics evidence |
| OQ-005 | Blocking; active — Golden Glory / direct Link / Flame Link formula evidence |
| OQ-006 | Nonblocking; deferred — derived/aggregate Enmity only; isolated manual path is implemented |
| OQ-007 | Resolved — BUILD-002 copied-item recognition boundary |

## Next two planned outcomes

1. Focused OQ-004 / OQ-005 mechanics contract for the player-side chain.
2. BUILD-003 direction (not yet implemented): progressive recognition of
   supported PoB/item/passive components; manual contribution entries for
   unsupported sources; provenance for every component; reviewed, missing,
   incomplete, and unavailable states; Golden Glory and direct Link shown
   separately; Flame Link granted damage only when formula gates pass; no DPS
   terminology; no comprehensive Mercenary model.

## Owner-input boundary

Ask the owner only when the answer materially changes current product behavior.
Do not reopen deferred automatic Mercenary-sheet derivation merely because a
historical plan listed it as a phase. See
[DEC-003](decisions/DEC-003-manual-first-input-boundaries.md).

## Knowledge-placement table

| Knowledge type | Canonical location | What it may control |
| --- | --- | --- |
| Product decisions | Product direction and decision records | Scope, priorities, required workflow |
| One build’s observed or manually entered values | Saved build state | Only that build’s calculations |
| Game-mechanics claims | Versioned audits and machine-readable contracts | Automatic derivation and formulas |
| Screenshots, synthetic PoBs, and test material | Evidence and fixtures | Validation, never universal truth |
| Unverified assumptions | Open-question register | Warnings, manual fallbacks, or deferred automation |

## Historical-material warning

Attachments, exported plans, external source packs, and detached roadmap files
are not canonical merely because they were included in a prompt. An explicit
current-task instruction may adopt or use attached material for that task.
Durable authority still requires the accepted result to be recorded in the
repository and merged through the normal workflow. Chat summaries and local
unmerged branches remain noncanonical durable records. Material under
[docs/reference/](reference/README.md) is historical or supporting only.
