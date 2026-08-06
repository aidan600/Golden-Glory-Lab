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
| Settled product choices | [Decision records](decisions/INDEX.md), especially [DEC-003](decisions/DEC-003-manual-first-input-boundaries.md) and [DEC-004](decisions/DEC-004-manual-first-flame-link-player-chain.md) |

## Status date

2026-08-06

## Current main milestone

Phase 3 — first usable desktop BUILD — continues after
[BUILD-004](builds/BUILD-004-manual-calculator-reset.md) resets the ordinary
product shell to a manual calculator, and
[BUILD-005](builds/BUILD-005-publication-readiness.md) prepares that
calculator for its first public v0.1.0 release (task branch; pending merge).

## Ordinary product now

The default desktop application is the **Golden Glory Calculator**:

- two top-level pages: Calculator and Light Radius Breakdown;
- manual Luminary and Mercenary/Enmity inputs;
- live Effective Link Skill Buff Effect, Link Effect Multiplier, Flame Link
  Added Fire Damage, and Enmity Fire Penetration;
- optional Light Radius breakdown that can copy a total into the Calculator;
- no DPS reporting.

PoB import, item mapping/review, save/open, provenance/evidence UI, and the
diagnostic `GoldenGloryApp` remain in the repository as experimental
infrastructure. They are not required to use the calculator.

## Merged outcomes

The two entries below describe the diagnostic desktop intake and copied-item
workflow. That workflow remains in the repository as experimental/internal
infrastructure behind the BUILD-002/BUILD-003 domain evaluators; it is not the
ordinary product surface. The manual two-page calculator (BUILD-004) is the
ordinary product, and it does not require PoB import to produce results.

- **BUILD-001 (merged):** desktop intake; PoB raw XML and share-code import;
  source-order review; explicit Player and Mercenary mapping; opaque manual
  Mercenary equipment; deterministic local persistence.
- **BUILD-002 (merged):** copied-item recognition; common PoB/copied/manual
  review; exact evidence gates; build-state v2 migration; manual isolated
  Enmity contribution; Enmity-only target, gap, surplus, cap, and
  input-beyond-cap reporting.

## Implemented on recent BUILD paths

- **BUILD-003:** manual-first Flame Link player chain; advisory Light Radius /
  Link Buff Effect recognition until explicit apply; build-state v3 with
  `flameLinkPlayerChain` and `recognitionSource`; packaged level table 1–40;
  modelled nearest-integer half-up granted Added Fire Damage.
- **BUILD-004:** ordinary-user product reset to the two-page manual calculator;
  narrow `manual_calculator` domain seam; shared Enmity overcap helper;
  one-file `GoldenGloryCalculator.exe` builder; PoB-modelled fractional
  Fire Resistance truncation; fixed non-resizable window sized for populated
  content on both tabs.
- **BUILD-005:** first-public-release readiness for that calculator —
  user-first README, `docs/INSTALL.md`, `docs/RELEASE_CHECKLIST.md`, a Windows
  Setup installer (Inno Setup), and a single-command release builder producing
  `GoldenGloryCalculator.exe` and `GoldenGloryCalculator-Setup.exe`. Product
  acceptance for v0.1.0 is based on those two executables, not on source
  checkout.

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

First-release player-side mechanics work is implemented for the manual-first
path:

    Light Radius
        -> Golden Glory contribution
    Direct Link Skill Buff Effect
        -> separate contribution
    Golden Glory contribution + direct Link contribution + active conditionals
        -> Flame Link damage granted (modelled)

[OQ-004](OPEN_QUESTIONS.md) and [OQ-005](OPEN_QUESTIONS.md) are resolved for
that manual-first path via [DEC-004](decisions/DEC-004-manual-first-flame-link-player-chain.md).
Live-game rounding confirmation, Powerful Bond auto-activation, and exhaustive
recognition remain unresolved and do not block the labelled manual workflow.

## Implemented manual fallbacks

The ordinary calculator and BUILD-002/BUILD-003 domain paths are the
first-release calculation surfaces. Missing mechanics evidence blocks automatic
derivation, not manual entry and not the entire product workflow.

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
| OQ-004 | Resolved for manual-first path — superseded by DEC-004 / BUILD-003; exhaustive recognition deferred |
| OQ-005 | Resolved for manual-first path — superseded by DEC-004 / BUILD-003; live rounding still open |
| OQ-006 | Nonblocking; deferred — derived/aggregate Enmity only; isolated manual path is implemented |
| OQ-007 | Resolved — BUILD-002 copied-item recognition boundary |

## Next two planned outcomes

1. Owner-test the installed and portable calculator executables; merge
   BUILD-004/BUILD-005 when accepted; owner creates and publishes GitHub
   Release v0.1.0 per [docs/RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md).
2. Optional later evidence work for live Flame Link rounding and conditional
   auto-activation; exhaustive recognition remains deferred.

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
