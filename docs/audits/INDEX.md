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
alternate weapons, and relevant child sockets. A later PROOF must implement and
test the neutral loader. Player and Mercenary ownership always requires an
explicit user mapping; source order is never ownership evidence.

## First-release evidence-pack

The evidence-integrity gate validates the declared artifact inventory, source manifests,
positive-capability dependencies, and withheld fixture states without promoting an
unresolved claim.


See [first-release evidence-pack status](FIRST_RELEASE_EVIDENCE_PACK.md) for
the task/phase distinction and the exact claim gates. The pack is structurally
complete, while the affected BUILD calculation remains unauthorized.

### [AUD-002 — Permanent Mercenary passive-sheet fields](AUD-002.md)

Status: blocked. It establishes permanent-Mercenary/info-sheet scope and a
manual-final-value safety contract, but `C03-C05` leave labels, semantics,
equipment inclusion, and comparable context unknown. A derived sheet value
therefore remains unavailable.

### [AUD-003 — Light Radius source coverage](AUD-003.md)

Status: supported. It establishes bounded Default-tree Light Radius and direct
Link Skill Buff Effect source recognition plus literal Golden Glory wording.
`C08` and `C12` still gate Powerful Bond's condition, complete source coverage,
arithmetic, stacking, runtime activation, and scaled output.

### [AUD-004 — Flame Link](AUD-004.md)

Status: supported. It establishes a Flame Link reference and reporting contract
for ordinary levels, but `C09-C10` withhold a definitive scaled integer granted
damage result. Exceptional levels remain separately gated.

### [AUD-005 — Enmity's Embrace](AUD-005.md)

Status: supported. It establishes an explicitly equipped, same-context,
integral manual isolated Enmity path and target reporting. Penalty derivation,
sheet-derived values, aggregation, enemy resistance, and damage remain gated.

### AUD-006 — Critical strikes

Audit attack and spell critical strikes separately after the Flame Link and
Enmity paths are established.
