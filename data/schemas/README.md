# Data Schemas

This directory holds versioned contracts for curated, generated, and import
data. Keep each schema separate from individual source records and from future
saved-build state.

The source registry schema lives beside its registry in `data/sources/` because
it is that registry's immediate contract.

`pob-neutral-import-v1.schema.json` is the complete Draft 2020-12 contract for
neutral PoB import result `1.0.0`. It closes stable production-facing objects,
including success/failure invariants, envelope/runtime metadata, source tree,
document events, occurrence records, references, resolutions, provenance, and
reports. Recursive retained source nodes have closed node kinds. Only the value
of `report[].retainedMaterial` is intentionally permissive because it may carry
arbitrary source material already bounded by the importer.

The real schema is exercised by `tests/test_pob_importer.py` with the exact
proof-only validator set in `requirements/pob-import-proof.txt`. The production
package does not depend on that validator.

`audit-evidence-artifact-v1.schema.json` is the closed Draft 2020-12 contract
for the ten first-release AUD-002 through AUD-005 evidence artifacts. It fixes
the approved artifact IDs, types, audit IDs, record-data shapes, dependency-object
fields, result-state enums, Enmity formula strings, and corrected Enmity source
locators. `scripts/validate/run_evidence_pack_schema_validation.py` provisions the
existing exact proof-only validator pins in a temporary target, runs its child with
`python -I -S`, validates all ten artifacts, and rejects representative invalid
mutations. `check_first_release_evidence_pack.mjs` adds cross-document semantic
checks; neither script is production runtime code.
