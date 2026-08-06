# DEC-004 — Manual-first Flame Link player chain

## Status

accepted

## Context

OQ-004 and OQ-005 asked what source and formula evidence are required for the
player-side Light Radius → Golden Glory / direct Link / Flame Link path.
Exhaustive catalog coverage and live-client rounding confirmation were not
available, but the owner approved a product policy for a labelled manual-first
BUILD that keeps uncertain components explicit and never invents automatic
activation.

## Options considered

- Wait for a separate AUD-006 and live rounding proof before any Flame Link UI.
- Ship modelled Flame Link granted damage from reviewed manual inputs with
  advisory recognition and explicit three-state conditionals.
- Auto-activate Powerful Bond / Inspiring Bond and clamp out-of-range levels.

## Decision

Implement BUILD-003 as a manual-first Flame Link player chain under product
policy, without creating a separate AUD-006.

- Reviewed Light Radius contributes only when Golden Glory is allocated and the
  Mercenary target is an active permanent Mercenary; otherwise 0 when explicitly
  not allocated, or unresolved when allocation/target is unknown.
- Direct and conditional Link Buff Effect percents are additive.
- Only explicitly active conditionals and additional Link gem levels count;
  unknown states block final resolution.
- Empowered Bond is +2 Link gem levels; Powerful Bond and Inspiring Bond are
  20% conditional buff-effect templates, never +2 levels.
- Base level defaults to 21 with provenance `manual-benchmark-default`.
- Life component is 5% of reviewed Luminary Maximum Life.
- Rounding is modelled nearest-integer half-up and must be labelled as such.
- Output is Added Fire Damage granted to linked Mercenary, never DPS.
- Quality does not affect damage.
- Do not clamp unsupported multipliers or effective levels.

## Consequences

- OQ-004 and OQ-005 are resolved for the manual-first path; live rounding and
  auto-activation remain open product/evidence gaps.
- Build-state advances to v3 with `flameLinkPlayerChain`.
- Evidence presentation stops listing Flame Link as wholly unavailable while
  preserving deferred live-rounding and exhaustive-recognition entries.
- Enmity isolation and BUILD-002 behavior remain unchanged.

## Revisit conditions

Revisit when live-client rounding is confirmed, when conditional auto-activation
rules are evidenced, or when exhaustive recognition becomes an ordinary product
requirement.
