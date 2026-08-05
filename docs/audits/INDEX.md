# Audit Index

Audit records are the durable evidence trail for bounded research. Start from
[the audit template](TEMPLATE.md), keep direct evidence separate from
inference, and register material sources before treating a conclusion as
current.

## Initial audit order and current status

| Order | Audit | Status | Dependency-aware intent |
| --- | --- | --- | --- |
| 1 | [AUD-001 — PoB item-set import contract](AUD-001.md) | supported | Establishes a pinned neutral import contract and explicit loadout mapping before a parser proof. |
| 2 | [AUD-002 — Permanent Mercenary passive-sheet fields](AUD-002.md) | blocked | Manual final values only; `C03-C05` block a derived permanent-Mercenary sheet path. |
| 3 | [AUD-003 — Light Radius source coverage](AUD-003.md) | supported | Scoped Default-tree coverage; `C08` and `C12` retain condition and arithmetic gates. |
| 4 | [AUD-004 — Flame Link](AUD-004.md) | supported | Reference contract only; `C09-C10` withhold a final scaled result. |
| 5 | [AUD-005 — Enmity's Embrace](AUD-005.md) | supported | Manual isolated Enmity path only; derived and aggregate paths remain gated. |
| 6 | AUD-006 — Critical strikes | planned | Deferred until the Flame Link and Enmity paths are established; remains a separate, ability-dependent audit. |

### [AUD-001 — PoB item-set import contract](AUD-001.md)

Status: supported. Current and historical source evidence establishes a pinned
contract for enumerating and preserving PoB item sets, item text, references,
alternate weapons, and relevant child sockets. [PROOF-001](../proofs/PROOF-001-pob-importer.md)
implemented and established the neutral importer;
[PROOF-002](../proofs/PROOF-002-desktop-packaging.md) packaged it;
[BUILD-001](../builds/BUILD-001-desktop-intake-mapping.md) and
[BUILD-002](../builds/BUILD-002-copied-item-enmity.md) consume it. Player and
Mercenary ownership always requires an explicit user mapping; source order is
never ownership evidence.

## First-release evidence-pack

The evidence-integrity gate validates the declared artifact inventory, source manifests,
positive-capability dependencies, and withheld fixture states without promoting an
unresolved claim.


See [first-release evidence-pack status](FIRST_RELEASE_EVIDENCE_PACK.md) for
the task/phase distinction and the exact claim gates. The pack is structurally
complete as a Phase 1 deliverable. Unsatisfied claim gates carry forward and
withhold only their dependent automatic outputs; they do not reopen the
evidence-pack task.

### [AUD-002 — Permanent Mercenary passive-sheet fields](AUD-002.md)

Status: blocked. It establishes permanent-Mercenary/info-sheet scope and a
manual-final-value safety contract, but `C03-C05` leave labels, semantics,
equipment inclusion, and comparable context unknown. A derived sheet value
therefore remains unavailable. Automatic Mercenary-sheet derivation is deferred
and nonblocking for the first release; the manual Enmity path remains available.

### [AUD-003 — Light Radius source coverage](AUD-003.md)

Status: supported. It establishes bounded Default-tree Light Radius and direct
Link Skill Buff Effect source recognition plus literal Golden Glory wording.
`C08` and `C12` still gate Powerful Bond's condition, complete source coverage,
arithmetic, stacking, runtime activation, and scaled output. Together with
AUD-004, these claims continue to gate the definitive player-chain result.

### [AUD-004 — Flame Link](AUD-004.md)

Status: supported. It establishes a Flame Link reference and reporting contract
for ordinary levels, but `C09-C10` withhold a definitive scaled integer granted
damage result. Exceptional levels remain separately gated. The definitive
player-chain result remains gated by these AUD-003/AUD-004 claims.

### [AUD-005 — Enmity's Embrace](AUD-005.md)

Status: supported. It establishes an explicitly equipped, same-context,
integral manual isolated Enmity path and target reporting.
[BUILD-002](../builds/BUILD-002-copied-item-enmity.md) implements that manual
isolated contract. Penalty derivation, sheet-derived values, aggregation,
enemy resistance, and damage remain gated.

### AUD-006 — Critical strikes

Audit attack and spell critical strikes separately after the Flame Link and
Enmity paths are established.
