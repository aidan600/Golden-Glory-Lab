# Product Direction

This document records only the direction currently agreed for Golden Glory Lab.
It does not confirm unresolved mechanics formulas.

## Product intent

Golden Glory Lab is an offline desktop application for describing a real Path
of Exile loadout, identifying missed sources and unfinished objectives, showing
caps and surplus investment, and offering comprehensible improvement paths.

The initial release concerns one player Luminary and one active permanent
Mercenary. Player and Mercenary loadouts are separate. The product will not
produce a combined build score and is not focused on theoretical maximum-build
showcases.

## Initial loadout and import direction

- Path of Building item sets are loadout containers. The application should
  enumerate them and let the user explicitly designate one player loadout and
  one Mercenary loadout; set order is not ownership.
- A user may have sets such as Player — Current, Mercenary — Current, and
  Mercenary — Candidate.
- PoB is not assumed to contain individually rolled permanent Mercenary
  passive-sheet statistics. Those are manually entered build-instance data
  unless a later integration proof establishes otherwise.
- User PoBs, copied items, screenshots, and Mercenary values are fixtures or
  build data, not general reference data.

## Initial mechanics paths

The intended initial player path is:

    Luminary equipment, passives, and conditions
        -> Light Radius
        -> Golden Glory and direct Link buff effect
        -> Flame Link damage granted

The intended initial Mercenary path is:

    Permanent Mercenary passive-sheet stats and equipment
        -> Uncapped Fire Resistance
        -> Enmity's Embrace
        -> Overcapped Fire Resistance
        -> Fire Penetration, capped at 200%

Enmity's Embrace must accept observed values outside its natural modifier range,
including Volatile-modified values. This is an input-preservation requirement;
calculation order, rounding, and its other mechanics remain unresolved until
audited.

Critical-strike reconstruction is a separate, optional later panel and audit.
It is expected to be more conditional and ability-dependent than the initial
paths.

## Decision boundaries

The product is oriented around goals, gaps, caps, surplus, completeness, and
improvement paths. It should not label an increase as an improvement when the
relevant objective is already satisfied. It must preserve unknowns and clearly
show what needs manual input or further evidence.
