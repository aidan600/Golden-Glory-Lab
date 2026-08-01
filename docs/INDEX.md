# Documentation Index

This is a navigation map, not a duplicate specification. The repository is the
durable project record; read the current documents below before relying on a
chat summary.

## Read before a substantial task

1. [Repository agent guide](../AGENTS.md)
2. [Specification status and authority](SPEC_STATUS.md)
3. [Current product direction](PRODUCT_DIRECTION.md)
4. The mode-specific route below

## Task-mode routes

| Mode | Read next | Produce or update |
| --- | --- | --- |
| AUDIT | [Source policy](SOURCE_POLICY.md), [Audit workflow](AUDIT_WORKFLOW.md), [audit index](audits/INDEX.md) | An audit record and any justified source-registry updates |
| PROOF | [Audit workflow](AUDIT_WORKFLOW.md), relevant open question, fixtures and scripts guidance | A bounded proof, its evidence, and stated non-proof |
| BUILD | [Product direction](PRODUCT_DIRECTION.md), [Audit workflow](AUDIT_WORKFLOW.md), relevant decisions and data docs | A coherent user-facing, data-pipeline, or repository outcome |
| REPAIR | [Audit workflow](AUDIT_WORKFLOW.md), relevant defect context, fixtures and scripts guidance | The correction and an appropriate regression guard |

## Records and backlogs

- [Open questions](OPEN_QUESTIONS.md) — unresolved product, evidence, proof,
  and implementation work.
- [Audit index](audits/INDEX.md) — ordered mechanics and import audit backlog.
- [Audit template](audits/TEMPLATE.md) — required evidence-aware audit record.
- [Decision index](decisions/INDEX.md) — current decision records.
- [Decision template](decisions/TEMPLATE.md) — format for a reviewed decision.

## Data, fixtures, and tools

- [Source registry](../data/sources/registry.json) and
  [registry schema](../data/sources/registry.schema.json)
- [Curated data guidance](../data/curated/README.md)
- [Generated data guidance](../data/generated/README.md)
- [Schema guidance](../data/schemas/README.md)
- [Fixture guidance](../fixtures/README.md)
- [Script guidance](../scripts/README.md)

## Current versus historical material

The documents in this index, current curated data, and reviewed records are
current repository material subject to the authority order in
[SPEC_STATUS.md](SPEC_STATUS.md). Everything under
[docs/reference/](reference/README.md) is historical or supporting material:
use it for leads, then verify the underlying source and record any current
conclusion through the workflow.
