# Audit Index

Audit records are the durable evidence trail for bounded research. Start from
[the audit template](TEMPLATE.md), keep direct evidence separate from
inference, and register material sources before treating a conclusion as
current.

## Proposed initial order

| Order | Audit | Status | Dependency-aware intent |
| --- | --- | --- | --- |
| 1 | [AUD-001 — PoB item-set import contract](AUD-001.md) | supported | Establishes a pinned neutral import contract and explicit loadout mapping before a parser proof. |
| 2 | AUD-002 — Permanent Mercenary passive-sheet fields | planned | Can gather evidence alongside AUD-001; blocks reliable Mercenary instance inputs and may require human in-game evidence. |
| 3 | AUD-003 — Light Radius source coverage | planned | Establishes the versioned player-source catalog before a Flame Link calculation claim. |
| 4 | AUD-004 — Flame Link | planned | Depends on the relevant Light Radius and Link-effect evidence from AUD-003. |
| 5 | AUD-005 — Enmity's Embrace | planned | Uses the Mercenary-field contract from AUD-002; preserves arbitrary observed values and excludes Volatile crafting simulation. |
| 6 | AUD-006 — Critical strikes | planned | Deferred until the Flame Link and Enmity paths are established; remains a separate, ability-dependent audit. |

### [AUD-001 — PoB item-set import contract](AUD-001.md)

Status: supported. Current and historical source evidence establishes a pinned
contract for enumerating and preserving PoB item sets, item text, references,
alternate weapons, and relevant child sockets. A later PROOF must implement and
test the neutral loader. Player and Mercenary ownership always requires an
explicit user mapping; source order is never ownership evidence.

### AUD-002 — Permanent Mercenary passive-sheet fields

Determine exact displayed fields, units, whether equipment is included, whether
values are capped, uncapped, passive-only, or conditional, and which fields are
required by the initial release. Human in-game screenshots or transcriptions may
be required.

### AUD-003 — Light Radius source coverage

Generate and manually review the source catalog, including slot coverage,
conditions, conflicts, availability, and provenance.

### AUD-004 — Flame Link

Audit level data, Link-effect application, calculation order, and rounding.

### AUD-005 — Enmity's Embrace

Audit the natural range, arbitrary observed values, calculation order,
penetration cap, target gap, and surplus behavior. Volatile crafting simulation
is outside scope.

### AUD-006 — Critical strikes

Audit attack and spell critical strikes separately after the Flame Link and
Enmity paths are established.
