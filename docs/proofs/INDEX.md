# Proof Index

Proofs are bounded technical exercises. An adopted proof retains its
production-facing seam, contract, fixtures, and regression tests for downstream
consumers.

| Proof | Result | Adoption | Intended consumers |
| --- | --- | --- | --- |
| [PROOF-001 — reusable PoB importer](PROOF-001-pob-importer.md) | PASS WITH LIMITATIONS | ADOPT WITH NAMED LIMITATIONS | Desktop packaging PROOF; first usable desktop BUILD |
| [PROOF-002 — Windows desktop packaging](PROOF-002-desktop-packaging.md) | PASS WITH LIMITATIONS | ADOPT WITH NAMED LIMITATIONS | First usable desktop BUILD |
| [PROOF-003 — Mercenary sheet observation](PROOF-003-mercenary-sheet-observation.md) | NOT RUN — DEFERRED BEFORE OBSERVATION | NONE | Future automatic Mercenary-sheet derivation only; not a first-release blocker |

PROOF-003 remains deferred before observation. Unmerged local scaffolding
existed but was not adopted or imported. See
[DEC-003](../decisions/DEC-003-manual-first-input-boundaries.md).
Canonical status does not depend on a local-only branch continuing to exist.
