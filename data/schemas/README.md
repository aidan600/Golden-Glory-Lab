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
