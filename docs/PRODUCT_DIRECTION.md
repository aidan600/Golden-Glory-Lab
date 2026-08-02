# Product Direction

This is Golden Glory Lab's single current product-definition document. It
states product intent and scope; it does not confirm unresolved mechanics
formulas, source coverage, stacking, calculation order, rounding, display
precision, or conditional behavior.

## Product intent

Golden Glory Lab is a lightweight, standalone, offline desktop loadout-audit
and improvement planner for a Path of Exile Luminary and one active permanent
Mercenary.

It carries forward the core workflow historically served by a purpose-built
spreadsheet: make relevant inputs visible, reduce missed sources, explain the
calculation chain, identify unfinished goals and capped goals, reveal surplus
investment, and show practical paths toward improvement.

It is not intended to replace Path of Building, calculate every Path of Exile
mechanic, generate theoretical showcase builds, calculate general Mercenary DPS
in the first release, or produce a combined build score. Flame Link damage
granted is not labelled as DPS without a later audited combat model.

## Intended product flows

The initial player path is:

    Luminary equipment, passives, ascendancy, and conditions
        -> increased and reduced Light Radius
        -> Golden Glory contribution
        -> direct Link Skill Buff Effect
        -> Flame Link damage granted to the Mercenary

The initial Mercenary path is:

    Permanent Mercenary passive-sheet stats and equipment
        -> Uncapped Fire Resistance
        -> Enmity's Embrace
        -> Overcapped Fire Resistance
        -> Fire Penetration, capped at 200%

These arrows describe intended product scope and information flow. They do not
confirm exact formulas, valid source coverage, stacking rules, calculation
order, rounding, display precision, conditional behavior, or the mechanics
basis for the intended 200% presentation cap. Those questions remain governed
by the distinct Light Radius, Flame Link, and Enmity's Embrace audits.

Golden Glory contribution and direct Link Skill Buff Effect remain separately
visible inputs. Critical-strike reconstruction is a separate later audit and
panel, not a prerequisite for this path.

## First-release user workflow

1. Open Golden Glory Lab locally.
2. Import a Path of Building (PoB) share code or raw XML.
3. Enumerate every PoB item set.
4. Explicitly map one item set to the player.
5. Optionally map one different item set to the Mercenary.
6. If no Mercenary item set is selected, enter Mercenary equipment manually.
7. Enter relevant permanent Mercenary passive-sheet values manually.
8. Review imported items.
9. Paste copied item text or enter unsupported items manually as needed.
10. Review Light Radius and Link Skill Buff Effect contributions.
11. Review Flame Link damage granted.
12. Review Uncapped Fire Resistance, Enmity overcap, and Fire Penetration.
13. Configure useful targets.
14. Review gaps, caps, surplus, and unfinished or unreviewed sources.
15. Save and reopen the combined local build state.

## PoB import boundary

PoB is an import container and supporting source, not authority for permanent
Mercenary calculations. In accordance with the supported AUD-001 PoB item-set
import contract, Golden Glory Lab should accept raw XML and PoB share-code input;
enumerate every item set; preserve names, IDs, each item's complete XML
character value, slots, weapon-set state, relevant child sockets, and
recoverable unsupported material; and produce transparent recognition and
warning reports.

The user must confirm the player mapping by import-local item-set occurrence.
The user may map a different Mercenary set occurrence or choose no Mercenary
item set. Names may support a clearly labelled suggestion, but ownership must
never be inferred from item-set order, active state, item-set name alone,
minion references, Enmity's Embrace, or any other item contents. See
[AUD-001](audits/AUD-001.md) for the supported boundary.

## Item input and data boundaries

Four input paths create one canonical item instance:

1. Known catalog item or modifier selection.
2. Copied Path of Exile item text.
3. A selected PoB item-set import.
4. Manual entry.

Observed values are authoritative for the imported or entered item instance.
Natural ranges are reference metadata, so the application accepts observed
out-of-range values caused by corruption, Volatile Vaal modification, legacy
behavior, or another valid item history. It preserves original item text where
practical and reports a range difference informationally. Volatile crafting
simulation and crafting odds are not product scope.

The product keeps four layers distinct:

1. Reference data - what can exist.
2. Mechanics rules - how recognized inputs calculate.
3. Imported or manually entered build state - what this loadout has.
4. Evidence and test fixtures - why a rule or reference record is believed.

User PoBs, copied items, screenshots, spreadsheets, and Mercenary passive-sheet
values are build-instance material or fixtures, never general reference
authority.

## Improvement philosophy

Golden Glory Lab is a loadout audit and improvement planner, not a
maximum-number optimizer. It emphasizes completeness, target gaps, caps,
surplus investment, locked requirements, and practical improvement paths. A
stat increase is not called an improvement when its configured objective is
already satisfied.

### First usable BUILD

The first usable application reports current values, configured targets, gaps,
caps, surplus, and unreviewed or missing information. It need not generate
sophisticated change recommendations.

### Later completeness and improvement phase

A later phase may add constraint-aware slot review, one-slot suggestions, and
small multi-slot improvement patches while preserving locked items, sockets,
availability, and user requirements.

## First-release scope and deferrals

The first release includes a standalone offline desktop application; one active
permanent Mercenary; raw XML and PoB share-code import; explicit player
item-set mapping and optional Mercenary mapping; manual Mercenary passive-sheet
entry; catalog, copied-item, PoB, and manual item input; Light Radius;
separate Golden Glory and direct Link Skill Buff Effect contributions; Flame
Link granted-damage calculation; Uncapped Fire Resistance input and equipment
handling; Enmity overcap and Fire Penetration calculation; basic target, gap,
cap, and surplus reporting; review state for relevant inputs; local versioned
save/open; and transparent recognition and warning reports.

Deferred work includes general Mercenary DPS, full spell-Mercenary modeling,
every Link skill, market pricing, live trade integration, account
authentication, runtime scraping, temporary Mercenaries, Volatile crafting
simulation, global theoretical best-build search, a combined build score, and
critical-strike reconstruction until its separate audit supports it.
