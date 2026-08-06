# BUILD-003 - Manual-First Flame Link Player Chain

Mode: BUILD

Date: 2026-08-05

Status: implemented (pending merge)

## Outcome

Golden Glory Lab now evaluates a manual-first player-side Flame Link chain:

- reviewed Light Radius → Golden Glory contribution when allocated to an active
  permanent Mercenary;
- reviewed direct Link Skill Buff Effect;
- explicitly active conditional Link Buff Effect sources only;
- base Flame Link level plus explicitly active additional Link gem levels;
- Luminary Maximum Life × 5% life component;
- modelled nearest-integer half-up granted Added Fire Damage range.

The output label is **Added Fire Damage granted to linked Mercenary**. It is
never DPS. Quality does not affect damage. Enmity remains a separate isolated
manual path and is unchanged.

## Mechanics contract (owner-approved product policy)

Exact Decimal arithmetic:

```
NetLinkSkillBuffEffectPct = GG + Direct + Conditional(active only)
LinkEffectMultiplier = 1 + Net/100
EffectiveFlameLinkLevel = Base + Additional(active only)
LifeComponent = LuminaryMaximumLife * 0.05
Unscaled = LevelFlat[Effective] + LifeComponent
PreRound = Unscaled * LinkEffectMultiplier
ModelledInteger = ROUND_HALF_UP(PreRound)
```

Unavailable / unsupported states fail closed without clamping:

- unknown allocation/target, unknown conditionals, or unknown additional levels;
- `unsupported-effect-multiplier` when multiplier **< 0**;
- exact multiplier **0** resolves to available modelled `0–0` with exact pre-round `0`;
- `unsupported-effective-level` outside levels 1–40;
- negative reviewed Maximum Life is rejected (`LUMINARY_MAXIMUM_LIFE_NEGATIVE`); zero life is valid.

Rounding is labelled modelled, not confirmed live client behavior.
Exact Decimal arithmetic uses `numeric_context_for` around Flame Link products and
half-up quantization so accepted 128-digit inputs remain exact.

## Recognition boundary

`player_chain_recognition` is advisory only until the user explicitly applies a
candidate. It separates Empowered Bond identity (`Empowered Bond` → +2) from
generic Link gem-level wording (preserves signed N). Powerful Bond is never a
level source. Applying Light Radius updates value/provenance/raw/recognitionSource
only — never Golden Glory allocation or Mercenary target eligibility.

## Build-state v3

Canonical schema/application contract version is `3.0.0`. New field
`flameLinkPlayerChain` carries strict exact-key input state including
`recognitionSource` (`none` / `advisory-text` / `pob-import` / `copied-text`).
codec_v2 remains intact; v2→v3 migration inserts catalog defaults (benchmark
base level 21, Powerful/Inspiring Bond at unknown, Empowered Bond +2 at unknown)
without fabricating recognized facts. Semantic invariants reject contradictory
provenance/review/catalog combinations. Benchmark provenance requires an
explicit level-21 benchmark selection — typing `21` alone does not invent it.

JSON Schema and codec validation agree for schema-expressible canonical record
semantics. The decoder additionally supports one explicit old-draft
compatibility normalization: injection of a wholly absent `recognitionSource`
property (`{kind:"none",digest:null}`), marked migrated/upgrade-pending.
Present partial or malformed `recognitionSource` values are rejected, not
repaired. Cross-record `contributionId` uniqueness and strict decoded integer
representation are codec/decoder invariants. Draft 2020-12 treats values such as
`2.0` as mathematical integers, while the canonical codec requires actual JSON
integer tokens. Scalar reviewed blocks disallow `catalog-default`; that
provenance is reserved for the protected Powerful Bond, Inspiring Bond, and
Empowered Bond templates.

Empowered Bond identity is always `levels == 2` regardless of provenance.
Powerful Bond and Inspiring Bond are never additional Link gem-level sources.
`catalog-default` Empowered Bond rows require empty raw text and
`recognitionSource` none/null. Direct domain evaluation fails closed for
malformed level identity, provenance, source identity, and numeric
representation.

## Desktop

ApplicationService loads the packaged Flame Link level table at startup and
fails closed for Flame Link only when missing. Apply is provenance-preserving
and transactional (validate → evaluate → commit). The Flame Link notebook tab
keeps catalog convenience controls and adds row editors for all conditionals and
additional levels, plus Recognize → select → Apply/Dismiss. Rejected edits
restore Flame Link widgets. Runtime table SHA-256 is pinned in packaging
validation.

## Validation

- `tests/test_flame_link_build003.py`
- `tests/test_build003_repair.py`
- `tests/test_build_state_v3.py`
- `tests/test_desktop_build003.py`
- `scripts/validate/run_build003_schema_validation.py`
- packaged self-test Flame Link round-trip
- packaging pin for `flame-link-level-table-v1.json`

## Known limitations

- Live-game rounding is unresolved.
- Powerful Bond / Inspiring Bond automatic activation is unresolved.
- Exhaustive player-chain recognition is deferred.
- No Mercenary-sheet automation, DPS, second importer, or Enmity behavior change.
- General contribution editors are compact Tk row editors, not a full spreadsheet.

## Related

- [DEC-004](../decisions/DEC-004-manual-first-flame-link-player-chain.md)
- [CURRENT_STATE.md](../CURRENT_STATE.md)
- AUD-003 / AUD-004 evidence pack claims (supporting, not a separate AUD-006)
