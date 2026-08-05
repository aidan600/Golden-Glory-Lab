# DEC-003 — Manual-first fallbacks and owner-input boundaries

## Status

accepted

## Context

After BUILD-001 and BUILD-002 merged, historical roadmaps, project-source packs,
chat attachments, and an unmerged local PROOF-003 scaffolding branch still
presented automatic Mercenary-sheet derivation, screenshot capture, and broad
environment metadata as if they were current first-release blockers. Missing
mechanics evidence was repeatedly treated as blocking the whole product
workflow, including already-safe manual entry paths.

The repository needed a durable product decision that separates:

- automatic derivation, which requires confirmed or supported mechanics
  evidence; from
- manual, provenance-labelled entry, which remains available when safe; and
- optional future automation, which must not reopen as a release gate merely
  because an earlier plan listed it.

## Options considered

- Treat Mercenary-sheet observation and automatic derivation as first-release
  blockers until OQ-002 and OQ-003 close.
- Keep BUILD-002’s manual isolated Enmity path as the first-release fallback,
  defer automatic sheet derivation, and limit owner questions to answers that
  change current product behavior.
- Require ordinary users to supply screenshots or laboratory-style evidence
  packages as product inputs.

## Decision

Missing mechanics evidence blocks automatic derivation, not manual entry and
not the entire product workflow.

For the first release:

- BUILD-002’s manual isolated Enmity input path is sufficient.
- Automatic Mercenary-sheet derivation is deferred and nonblocking.
- Screenshots are not an ordinary product input path and are not required for
  ordinary use.
- Realm, mode, league, UI language, and display resolution are not product
  inputs.
- Client version may appear as evidence metadata but is not normally a user
  input unless a calculation consumes it.
- Owner questions are asked only when their answer materially changes current
  product behavior.
- Optional automatic derivation cannot become a first-release blocker merely
  because it could be useful later.

Manual inputs must be visibly labelled manual or user-attested, retain
provenance and context where needed, never be silently combined with uncertain
derived components, and remain distinct from confirmed mechanics-derived
values.

Future tasks may not reopen these choices without a new product decision or
evidence that materially changes the tradeoff.

## Consequences

- [OQ-002](../OPEN_QUESTIONS.md) and [OQ-003](../OPEN_QUESTIONS.md) are
  nonblocking and deferred for first-release planning.
- [PROOF-003](../proofs/PROOF-003-mercenary-sheet-observation.md) remains
  deferred before observation and is not a production blocker.
- Active mechanics work concentrates on the player-side Light Radius / Golden
  Glory / direct Link / Flame Link chain ([OQ-004](../OPEN_QUESTIONS.md),
  [OQ-005](../OPEN_QUESTIONS.md)).
- Agents and contributors read [CURRENT_STATE.md](../CURRENT_STATE.md) before
  planning substantial work and treat historical attachments or unmerged
  branches as noncanonical.

## Revisit conditions

Revisit only when:

- automatic Mercenary-sheet derivation becomes an active product priority; and
- that derivation blocks a named ordinary user capability; or
- new evidence materially changes the manual-first tradeoff and a replacement
  decision is recorded.

## Evidence or audit dependencies

- [BUILD-001](../builds/BUILD-001-desktop-intake-mapping.md) and
  [BUILD-002](../builds/BUILD-002-copied-item-enmity.md) supply the merged
  intake and manual Enmity fallback.
- [AUD-002](../audits/AUD-002.md) and [AUD-005](../audits/AUD-005.md) keep
  derived sheet paths gated while preserving labelled manual final inputs.
- [CURRENT_STATE.md](../CURRENT_STATE.md) records the operational consequence.

## Related records

- [CURRENT_STATE.md](../CURRENT_STATE.md)
- [PRODUCT_DIRECTION.md](../PRODUCT_DIRECTION.md)
- [PRODUCT_ROADMAP.md](../PRODUCT_ROADMAP.md)
- [OPEN_QUESTIONS.md](../OPEN_QUESTIONS.md)
- [PROOF-003 deferred record](../proofs/PROOF-003-mercenary-sheet-observation.md)

## Supersession details

Not superseded.

DEC-002 exists only inside the deferred local `proof/mercenary-sheet-observation`
scaffolding and is not a canonical repository decision. This record does not
reuse or adopt that ID.
