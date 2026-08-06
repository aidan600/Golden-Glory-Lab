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
- `unsupported-effect-multiplier` when multiplier ≤ 0;
- `unsupported-effective-level` outside levels 1–40.

Rounding is labelled modelled, not confirmed live client behavior.

## Recognition boundary

`player_chain_recognition` is advisory only. It recognizes bounded English
Light Radius and Link Buff Effect lines plus Empowered/Powerful/Inspiring Bond
candidates. It does not infer ownership, equipped state, or Mercenary targeting.
Powerful Bond is never treated as +2 gem levels. Reviewed manual totals remain
authoritative when the user applies them.

## Build-state v3

Canonical schema/application contract version is `3.0.0`. New field
`flameLinkPlayerChain` carries strict exact-key input state. codec_v2 remains
intact; v2→v3 migration inserts catalog defaults (benchmark base level 21,
Powerful/Inspiring Bond at unknown, Empowered Bond +2 at unknown) without
fabricating recognized facts. v1 migrates through v2 then v3.

## Desktop

ApplicationService loads the packaged Flame Link level table at startup and
fails closed for Flame Link only when missing. The Flame Link notebook tab
provides scrollable compact input and shows exact pre-round plus modelled
integer outputs. Evidence tab text no longer lists Flame Link as wholly
unavailable; live rounding, auto-activation, and exhaustive recognition remain
deferred.

## Validation

- `tests/test_flame_link_build003.py`
- `tests/test_build_state_v3.py`
- `tests/test_desktop_build003.py`
- `scripts/validate/run_build003_schema_validation.py`
- packaged self-test Flame Link round-trip

## Known limitations

- Live-game rounding is unresolved.
- Powerful Bond / Inspiring Bond automatic activation is unresolved.
- Exhaustive player-chain recognition is deferred.
- No Mercenary-sheet automation, DPS, second importer, or Enmity behavior change.

## Related

- [DEC-004](../decisions/DEC-004-manual-first-flame-link-player-chain.md)
- [CURRENT_STATE.md](../CURRENT_STATE.md)
- AUD-003 / AUD-004 evidence pack claims (supporting, not a separate AUD-006)
