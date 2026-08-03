# First-release evidence-pack status

## Task status

The first-release evidence-pack task covers [AUD-002](AUD-002.md),
[AUD-003](AUD-003.md), [AUD-004](AUD-004.md), and
[AUD-005](AUD-005.md). Each audit now has a versioned claim contract, material
sources in the [source registry](../../data/sources/registry.json), minimal
curated reference and/or synthetic gate material where appropriate, and
repository validation coverage. This is a structural completion of the bounded
AUDIT task, not an implementation approval.

The evidence pack is structurally complete, but it does not yet authorize the affected BUILD calculation.

## Phase-exit status

Phase 1 exit is **not achieved**. A supported audit headline does not promote
its unknown, provisional, superseded, or version-mismatched load-bearing
claims to supported mechanics. A downstream consumer must inspect the exact
claim and contract-version dependencies recorded by each audit.

| Audit | Record status | Narrowly supported | Load-bearing gate that remains |
| --- | --- | --- | --- |
| [AUD-002](AUD-002.md) | blocked | Permanent-Mercenary/info-sheet scope and a manual-final-value safety contract. | `C03-C05` block derived sheet or sheet-plus-equipment values. `C06` permits only manual final values with explicit context and inclusion state. |
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

The narrow AUD-005 manual formula remains a future consumer contract only. It
requires manual, integral, same-state final values and
`enmity.equipped-state=equipped`; it is not a license to infer the values from
a sheet or item text.

## Evidence still required

The next human or bounded-proof evidence requests are:

- controlled PoE1 3.29.1 permanent-Mercenary sheet captures identifying field
  labels, capped/uncapped semantics, Maximum Fire Resistance, equipment
  inclusion, and comparable context;
- controlled Golden Glory and direct-Link-effect arithmetic, condition, and
  activation evidence, including the Powerful Bond interaction when relevant;
- Flame Link observations that establish source Maximum Life handling and
  effect/rounding behavior at deliberately nontrivial values; and
- Enmity-equipped before/after observations that establish resistance-penalty
  order, display precision, and rounding without treating a personal build as
  general reference data.

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

## Next packaging-proof boundary

The next PROOF may package and exercise the adopted
`golden_glory_lab.pob_import` module by calling the same public
`importPobRawXml` or `importPobShareCode` entry point against a permanent
synthetic fixture, then verify the retained importer regression behavior from
the packaged runtime. It must not introduce a second importer, infer ownership,
or implement a blocked mechanics calculation. If a packaging proof includes a
UI surface, it must render the contract's unavailable/review state rather
than manufacture a Flame Link or Enmity result.
