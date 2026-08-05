# Documentation Index

This is a navigation map, not a duplicate specification. The repository is the
durable project record; read the current documents below before relying on a
chat summary.

## Read before a substantial task

1. [Repository agent guide](../AGENTS.md)
2. [Specification status and authority](SPEC_STATUS.md)
3. [Current state](CURRENT_STATE.md) — what is implemented, what is active, and
   what is deferred now?
4. [Current product direction](PRODUCT_DIRECTION.md)
5. [Product roadmap](PRODUCT_ROADMAP.md)
6. The mode-specific route below

## Task-mode routes

| Mode | Read next | Produce or update |
| --- | --- | --- |
| AUDIT | [Source policy](SOURCE_POLICY.md), [Audit workflow](AUDIT_WORKFLOW.md), [audit index](audits/INDEX.md) | An audit record and any justified source-registry updates |
| PROOF | [Audit workflow](AUDIT_WORKFLOW.md), relevant open question, fixtures and scripts guidance | A bounded proof, its evidence, and stated non-proof |
| BUILD | [Product direction](PRODUCT_DIRECTION.md), [product roadmap](PRODUCT_ROADMAP.md), [Audit workflow](AUDIT_WORKFLOW.md), relevant decisions and data docs | A coherent user-facing, data-pipeline, or repository outcome |
| REPAIR | [Audit workflow](AUDIT_WORKFLOW.md), relevant defect context, fixtures and scripts guidance | The correction and an appropriate regression guard |

## Records and backlogs

- [Open questions](OPEN_QUESTIONS.md) — unresolved product, evidence, proof,
  and implementation work.
- [Audit index](audits/INDEX.md) — ordered mechanics and import audit backlog.
- [First-release evidence-pack status](audits/FIRST_RELEASE_EVIDENCE_PACK.md) —
  task-completion, phase-exit, claim-gate, and evidence-integrity boundary for AUD-002 through AUD-005.
- [Proof index](proofs/INDEX.md) — bounded technical results, adoption status,
  and downstream consumers.
- [Build index](builds/INDEX.md) — implemented user-facing outcomes, including
  BUILD-002 copied-item recognition and isolated Enmity reporting, validation,
  limitations, and next slices.
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
conclusion through the workflow. External project-source packs, exported chat
plans, prompt attachments, detached roadmap files, and local unmerged branches
are noncanonical snapshots; see [CURRENT_STATE.md](CURRENT_STATE.md).
