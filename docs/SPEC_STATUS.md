# Specification Status and Authority

## Durable record

This repository is Golden Glory Lab's durable project record. A conversation,
chat transcript, or agent summary is noncanonical until a human-reviewed result
is recorded in the appropriate repository file and committed.

Files under docs/reference/ are historical or supporting material. They can
contain valuable leads, but they do not become specification merely by being
present or copied into a chat.

An audit is not confirmed merely because an agent wrote it. Its status must
match the direct evidence recorded in its audit record and source registry.
Provisional and unknown mechanics remain labelled as such.

## Authority order

When sources conflict, apply this order to the narrow question at hand:

1. The current task prompt for its stated outcome and constraints.
2. [AGENTS.md](../AGENTS.md), the standing repository policy.
3. Current documents under docs/, including reviewed audit and decision records.
4. Curated data under data/curated/, together with its provenance and
   verification status.
5. Historical and supporting material under docs/reference/.

The source registry records the evidence behind a claim; it does not by itself
override a higher-authority current decision or task constraint. An explicit
supersession record is required when a confirmed or supported conclusion is
replaced.

## Status discipline

Use the verification statuses defined in [SOURCE_POLICY.md](SOURCE_POLICY.md):
confirmed, supported, provisional, unknown, and superseded. Do not quietly
upgrade a status, collapse a disagreement, or turn an absence of public
evidence into a formula.

Current documentation deliberately records product direction separately from
unresolved mechanics. The initial calculation paths are product intent, not
confirmation of their final formulas, caps, rounding, or data coverage.
