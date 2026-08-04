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

`audit-evidence-artifact-v1.schema.json` is the deeply closed Draft 2020-12 contract for the ten first-release AUD-002 through AUD-005 evidence artifacts. It fixes each artifact envelope, record count/order/ID, and every nested `record.data` object; rejects unknown nested fields and missing required fields; constrains numeric and result-state fields; fixes canonical Enmity formulas and locators; and separates ordinal positive-capability dependencies (`supported`/`confirmed`) from non-ordinal adopted-policy prerequisites. `scripts/validate/run_evidence_pack_schema_validation.py` provisions the existing exact proof-only validator pins in a temporary target, runs its child with `python -I -S`, validates all ten artifacts, and rejects in-memory schema mutations through the real validator. `check_first_release_evidence_pack.mjs` adds reusable cross-document semantic validation and real in-memory negative mutations; neither script is production runtime code.
`build-state-v1.schema.json` is the closed Draft 2020-12 saved-build contract
for BUILD-001. It composes the complete neutral import schema by relative
`$ref`, closes the canonical root and manual-entry records, fixes all contract
versions, and constrains explicit mapping/source-mode combinations. Runtime
code performs only the typed and semantic checks BUILD-001 consumes; tests use
the schema for complete contract parity without adding a production validator
dependency.