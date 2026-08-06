# Open Questions

This is the initial unresolved-work backlog. Entries are not conclusions. Their
categories indicate planning priority, and dependencies identify work that
should inform or block the question.

The first-release evidence-integrity gate checks that the recorded contract is
internally consistent; it does not resolve, reprioritize, or close any question
below. Operational disposition for the first release is summarized in
[CURRENT_STATE.md](CURRENT_STATE.md) and
[DEC-003](decisions/DEC-003-manual-first-input-boundaries.md).

| ID | Category | Status | Question | Dependencies |
| --- | --- | --- | --- | --- |
| OQ-001 | blocking | resolved | What PoB item-set structure permits reliable player/Mercenary mapping without relying on set order? | AUD-001; PROOF-001 adopted neutral importer; explicit user mapping remains outside imported facts |
| OQ-002 | non-blocking | deferred | What exact permanent-Mercenary sheet field labels, units, capped/uncapped semantics, and Maximum Fire Resistance identity are required for future automatic derivation only? Manual Enmity final values remain available; this question does not block the first-release manual path. | AUD-002 `C03`; controlled 3.29.1 UI/data evidence; PROOF-003 deferred before observation |
| OQ-003 | non-blocking | deferred | For future automatic derivation only, do relevant permanent-Mercenary fields include equipment, and what controlled measurement context makes them comparable? Manual Enmity remains available without resolving this. | AUD-002 `C04-C05`; controlled observation; PROOF-003 deferred before observation |
| OQ-004 | non-blocking | resolved (manual-first) | Superseded for the first-release manual path by DEC-004 / BUILD-003: bounded advisory recognition plus reviewed manual Light Radius / Link Buff Effect totals. Exhaustive catalog coverage remains deferred and does not block the labelled manual workflow. | AUD-003 `C12`; DEC-004; BUILD-003 |
| OQ-005 | non-blocking | resolved (manual-first) | Superseded for the first-release manual path by DEC-004 / BUILD-003 modelled Flame Link formula. Live-game rounding confirmation and Powerful Bond auto-activation remain open product/evidence gaps and are labelled accordingly. | AUD-003 `C08`, `C12`; AUD-004 `C09-C10`; DEC-004; BUILD-003 |
| OQ-006 | non-blocking | deferred | What remains for automatic or aggregate Enmity work: penalty order/rounding, comparable-input derivation from the Mercenary sheet or equipment, and aggregation beyond the isolated item contribution? BUILD-002 already implements the isolated manual Enmity contribution and Enmity-only target reporting. | AUD-005 `C05-C07`; AUD-002 `C03-C05`; BUILD-002 |
| OQ-007 | non-blocking | resolved | BUILD-002 preserves exact copied text and supplies bounded structural/Enmity-identity recognition with explicit ordered reports; general modifier semantics, localization coverage, and broad catalog parsing remain outside the v1 contract. | AUD-001; BUILD-002 synthetic fixture matrix and recognition tests |
| OQ-008 | proof required | resolved | Can a Windows-first offline package exercise the adopted importer through its existing public seam and a permanent synthetic fixture? | PROOF-002 passed with named clean-machine and egress-isolation limitations; PyInstaller 6.21.0 packaged the adopted public seam without a second importer |
| OQ-009 | deferred | open | How should attack and spell critical strikes be reconstructed across conditional, ability-dependent cases? | AUD-006; initial mechanics paths |
| OQ-010 | non-blocking | open | What goal-aware improvement-patch rules can make recommendations without rewarding already-satisfied objectives? | Confirmed initial calculations and data coverage |

Categories are blocking, proof required, non-blocking, and deferred. Status
moves only when a current audit, proof, or decision supplies sufficient
evidence. The former `active` first-release mechanics focus for OQ-004/OQ-005
is superseded by the manual-first DEC-004 / BUILD-003 path; remaining live
rounding and exhaustive-recognition gaps are labelled in BUILD-003 evidence
presentation. `deferred` marks work that remains open without blocking the
named manual-first path.
