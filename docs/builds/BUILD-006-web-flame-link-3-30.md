# BUILD-006 - Covens of Umbra web calculator

Mode: BUILD

Date: 2026-11-17

Mechanics verification: supported model for Path of Exile 1 3.30.0

## Outcome

The web calculator targets Covens of Umbra, which launched November 13, 2026
Pacific time. The browser loads the bundled 3.30.0 Flame Link data and uses it
for the damage grant and the Golden Glory contribution. The manual workflow
continues to take the caster's Maximum Life, signed net Light Radius modifier,
effective gem level, direct Link Skill Buff Effect, and explicitly active
conditional sources. [GGG launch announcement](https://www.pathofexile.com/forum/view-thread/4013711)

An optional Flame Link comparison shows the 3.29 pre-nerf and 3.30 post-nerf
Added Fire Damage ranges and the change at each end of the range.

## Evidence

| Source registry ID | What it establishes |
| --- | --- |
| `ggg-3-30-0-covens-of-umbra-patch-notes` | Flame Link's base damage is 36–54 at level 1 and 219–329 at level 20, with 3% of caster Maximum Life added to each bound. Golden Glory applies 50% of the caster's Light Radius increases and reductions to Link Skill Buff Effect on their Mercenary. [GGG patch notes](https://www.pathofexile.com/forum/view-thread/4013680) |
| `ggg-3-30-0-new-and-changed-gems` | The official level-20 preview at 20% quality corroborates the 219–329 base range and 3% life coefficient. [GGG gem changes](https://www.pathofexile.com/forum/view-thread/4013898) |
| `pob-release-2-68-0-flame-link` | The pinned `FlameLink` skill record and the accompanying PoB interpolation reproduce flat damage for all 40 modeled rows. The record also confirms the Maximum Life field and duration-only quality. [Skill record](https://github.com/PathOfBuildingCommunity/PathOfBuilding/blob/07fa089bf08f6a089004c5c39192d12d210a13ac/src/Data/Skills/act_str.lua#L4346-L4430) |
| `poedb-flame-link-3-30-0` | The displayed progression agrees with all 40 reproduced PoB rows, including 240–361 at level 21 and 823–1235 at level 40. [PoEDB progression](https://poedb.tw/us/Flame_Link) |
| `ggg-poe1-skilltree-export-3-30-0` | Node 31517 confirms Golden Glory's 50% conversion. Powerful Bond 46471 and Inspiring Bond 60781 each retain their 20% conditional effect. The three +5% direct-effect passives and Empowered Bond's +2 Link gem levels are present in the export. [GGG Default tree export](https://github.com/grindinggear/skilltree-export/blob/550fb34ae7fca9ec4d760a2ac845bb2ba1032ec3/data.json) |

## Web calculation contract

The inherited [manual-first model](BUILD-003-player-chain-flame-link.md) uses
additive Link Buff Effect percentages and exact decimal arithmetic. BUILD-006
applies the reviewed 3.30 values at the same calculation stages.

```text
Golden Glory contribution = signed net Light Radius modifier × 0.50 when allocated
Net Link Skill Buff Effect = Golden Glory contribution + direct modifiers + active conditionals
Link Effect Multiplier = 1 + Net Link Skill Buff Effect / 100
Life contribution = caster Maximum Life × 0.03
Granted damage bound = round_half_up((level's flat bound + Life contribution) × Link Effect Multiplier)
```

The calculator retains the granted damage label and models integer rounding at
the final stage. Standard quality changes duration only. Exceptional-level
values model a user-supplied effective gem level. Availability in a particular
build depends on its gem-level sources.

Powerful Bond applies its conditional +20% after half of the Link duration has
expired. Inspiring Bond applies +20% when the caster linked recently (past four
seconds). The user controls both states. The pinned tree retains Oath of
Fealty's infinite attachment duration, and the interaction with Powerful Bond
remains unverified. [GGG Default tree export](https://github.com/grindinggear/skilltree-export/blob/550fb34ae7fca9ec4d760a2ac845bb2ba1032ec3/data.json)

## 3.29 and 3.30 comparison

Both versions use the same Maximum Life, signed net Light Radius modifier,
Golden Glory allocation, effective gem level, direct Link Skill Buff Effect,
and active conditional states. The 3.29 model selects its own level progression,
5% Maximum Life coefficient, and 100% Golden Glory conversion. The comparison
isolates the formula changes for those inputs. Gear availability and item rolls
can differ by version.

Each signed change is the 3.30 rounded result minus the 3.29 rounded result for
the same bound. Percentage change divides that difference by the rounded 3.29
result and is unavailable when that baseline is zero. The comparison applies to
Flame Link only. Enmity is calculated separately.

At level 20 with 5,000 Maximum Life, +100% net Light Radius, allocated Golden
Glory, and no other modifiers, 3.30 yields +50% Effective Link Skill Buff Effect.
The damage comparison for those inputs is shown below.

| Added Fire Damage | Minimum | Maximum |
| --- | ---: | ---: |
| 3.29 pre-nerf | 838 | 1,008 |
| 3.30 post-nerf | 554 | 719 |
| Signed change | −284 (−33.9%) | −289 (−28.7%) |

## Related 3.30 changes

- Mercenaries receive −30% resistance in level 46–67 areas and −60% in level
  68+ areas and hideouts. Enmity's Embrace still grants Fire Penetration equal
  to overcapped Fire Resistance up to 200%. The manual web estimate uses gear,
  aura, and Enmity inputs and excludes the area penalty. Automatic
  Mercenary-sheet derivation is deferred.
  [GGG patch notes](https://www.pathofexile.com/forum/view-thread/4013680),
  [PoEDB Enmity's Embrace](https://poedb.tw/us/Enmitys_Embrace)
- The 3.30 natural Light Radius ranges include 25–35% for The Hallowed Monarch
  and 20–40% for The Rotmother's Mutiny. Rare Light Radius modifiers on weapons,
  helmets, and rings now reach 30% at the highest tier. The manual breakdown
  uses actual modifiers from the loadout, including legacy values.
  [GGG patch notes](https://www.pathofexile.com/forum/view-thread/4013680)

## Supersession and limits

The default 3.30 web model supersedes the numerical 3.29 Flame Link and Golden
Glory values recorded in [AUD-003](../audits/AUD-003.md),
[AUD-004](../audits/AUD-004.md), and [BUILD-003](BUILD-003-player-chain-flame-link.md)
for that web target. The optional comparison retains those 3.29 inputs as its
versioned baseline. The historical records retain their evidence and claim
statuses. Live integer rounding and automatic conditional activation
remain unresolved. The supported scope is modeled Added Fire Damage granted to
the linked Mercenary. It covers neither total combat damage nor DPS.

## Validation

Run `node web/scripts/refresh-flame-link-table.mjs` to compare the bundled
table with the pinned PoB inputs. Use `--write` to regenerate the asset from
those inputs. The update changed all 40 flat ranges, retained all rows and
their requirement levels, and changed the two mechanics values. All 40 PoB
rows matched the current PoEDB display. The official notes and pinned tree
confirm the endpoints and changed coefficients. The source registry retains
the versioned locators needed to repeat the cross-check.

- `node --test web/tests/calculator.test.mjs` passed all 23 tests, including
  decreases, increases, zero baselines, and unavailable historical results.
- `node web/scripts/smoke-interactions.mjs` passed in Edge, including opening
  the comparison, recalculating both patches, and closing it. The open
  comparison was visually reviewed at desktop and mobile widths.
- `node scripts/validate/check_repository.mjs` and
  `node scripts/validate/check_first_release_evidence_pack.mjs` passed.
- `python -m unittest discover -s tests` passed all 248 tests with Python
  3.13 and Expat 2.8.1.
