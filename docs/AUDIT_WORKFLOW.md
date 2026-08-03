# Audit Workflow

## Task modes

Every substantial task declares exactly one mode.

| Mode | Purpose |
| --- | --- |
| AUDIT | Research a bounded question, record evidence, and reach a narrow conclusion or an explicit unresolved result. |
| PROOF | Test one technical or mechanics uncertainty with a bounded prototype, experiment, parser, packaging attempt, or fixture. |
| BUILD | Deliver a coherent user-facing, data-pipeline, or repository-workflow outcome. |
| REPAIR | Correct a documented defect and add an appropriate regression guard. |

## Substantial-task contract

All substantial tasks state:

    Mode:
    Outcome:
    Constraints:
    Deliverables:
    Verification:

AUDIT tasks additionally state:

    Question:
    Product impact:
    Scope:
    Source plan:
    Dataset impact:

## AUDIT procedure

1. Start from [the audit template](audits/TEMPLATE.md) and choose the next
   appropriate ID from [the audit index](audits/INDEX.md).
2. Register each material source in
   [the source registry](../data/sources/registry.json), including version,
   supported claims, verification status, and limitations.
3. Put direct evidence in the Evidence section. Put deductions, calculation
   choices, and uncertainty in Analysis. A reader must be able to separate what
   a source says from what the audit infers.
4. Record disagreements, patch/game-data/software version mismatches, and
   missing evidence in Conflicts and gaps. Do not quietly select the most
   convenient result.
5. Limit the conclusion to the evidence. Record meaningful non-conclusions
   explicitly and leave them provisional or unknown.
6. State whether the result changes curated data, generated data, fixtures, or
   none of them. An audit never changes a fixture's status into general
   reference authority.
7. If public evidence is inadequate, state precisely what human in-game
   screenshot, transcription, controlled observation, or permission is needed.

## Curated data, fixtures, and supersession

Curated data changes require an audit or other recorded evidence trail and
stable provenance. Generated data must retain a reproducible source procedure.
Fixtures may be added to demonstrate a parser or calculation case, but they
remain build-instance or synthetic test material.

To supersede an audit, create or update the newer evidence record, link the
prior audit and affected registry records through a superseded-by relationship
or explicit notes, change the prior audit status to superseded, and explain the
reason. Never overwrite a conclusion without preserving its evidence trail.

## PROOF, BUILD, and REPAIR

PROOF work records the bounded experiment, result, what it does not prove, and
an adoption recommendation. BUILD and REPAIR work record the implementation
outcome, validation, manual inspection, known limitations, and relevant
evidence or decision dependencies.

## Evidence units and PR units

Different evidence questions may share one PR when they collectively establish
one named downstream product contract. Each audit remains independently
identifiable, evidenced, validated, and repairable.

The complete PR outcome is the review unit. Individual audit reports are
evidence units. Each audit retains its own identifier, status, evidence,
conclusion, non-conclusions, and implementation contract. Individually
reviewable commits are preferred where practical. A repair may target one
affected audit without reopening unrelated supported evidence.

Every audit implementation contract identifies:

- required inputs;
- established rules;
- unsupported, provisional, or manually required behavior;
- machine-readable tables or fixtures established by evidence; and
- the expected downstream module or user flow.

## Proof adoption and downstream consumption

Every PROOF identifies its intended downstream consumer, production-facing
interface or artifact, retained implementation/fixtures/tests, next integrated
exercise, and adopt, repair, reject, or follow-up recommendation.

Adopted implementations and regression tests are reused through the established
seam. Replacing an adopted proof artifact requires explicit technical rationale
and review. A proof harness may be disposable; the adopted core, contracts,
fixtures, and tests are production-intent artifacts.
