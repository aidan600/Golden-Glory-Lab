# Open Questions

This is the initial unresolved-work backlog. Entries are not conclusions. Their
categories indicate planning priority, and dependencies identify work that
should inform or block the question.

The first-release evidence-integrity gate checks that the recorded contract is internally
consistent; it does not resolve, reprioritize, or close any question below.

| ID | Category | Status | Question | Dependencies |
| --- | --- | --- | --- | --- |
| OQ-001 | blocking | resolved | What PoB item-set structure permits reliable player/Mercenary mapping without relying on set order? | AUD-001; PROOF-001 adopted neutral importer; explicit user mapping remains outside imported facts |
| OQ-002 | blocking | open | What are the exact permanent-Mercenary field labels, units, capped/uncapped semantics, and Maximum Fire Resistance identity needed for a derived value? | AUD-002 `C03`; controlled 3.29.1 UI/data evidence |
| OQ-003 | proof required | open | Do relevant permanent-Mercenary fields include equipment, and what controlled measurement context makes them comparable? | AUD-002 `C04-C05`; controlled observation |
| OQ-004 | blocking | open | What complete current non-Default-tree source coverage and mechanics evidence are required before Light Radius/direct-Link records can support a calculation? | AUD-003 `C12`; versioned extraction and mechanics evidence |
| OQ-005 | blocking | open | What Golden Glory/direct-Link arithmetic and condition activation, plus Flame Link scaling and rounding, support a definitive scaled result? | AUD-003 `C08`, `C12`; AUD-004 `C09-C10` |
| OQ-006 | blocking | open | What are Enmity's penalty order/rounding, comparable-input derivation, and aggregation rules beyond its supported isolated manual formula? | AUD-005 `C05-C07`; AUD-002 `C03-C05` |
| OQ-007 | non-blocking | open | What copied-item parser scope preserves original material while producing a reviewable result? | AUD-001; fixture design |
| OQ-008 | proof required | open | Can a Windows-first offline package exercise the adopted importer through its existing public seam and a permanent synthetic fixture? | PROOF-001; `golden_glory_lab.pob_import`; no second importer or framework assumption |
| OQ-009 | deferred | open | How should attack and spell critical strikes be reconstructed across conditional, ability-dependent cases? | AUD-006; initial mechanics paths |
| OQ-010 | non-blocking | open | What goal-aware improvement-patch rules can make recommendations without rewarding already-satisfied objectives? | Confirmed initial calculations and data coverage |

Categories are blocking, proof required, non-blocking, and deferred. Status
moves only when a current audit, proof, or decision supplies sufficient
evidence.
