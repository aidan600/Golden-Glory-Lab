# Source Policy

## Purpose

Sources establish the evidence behind reference records, mechanics conclusions,
and workflow choices. A source class describes what the source is; verification
status describes how strongly the particular use is supported. They are
independent fields.

## Approved source classes

| Source class | Typical use | Limits |
| --- | --- | --- |
| Official GGG material | Announcements, patch notes, rules, and direct statements | May omit implementation detail or lag an observed change |
| Extracted game data | Structured values, tags, and natural ranges | Preserve game-data version and extraction provenance |
| Path of Building source and committed data | Import format and supported calculation or data behavior | It is supporting evidence, not authority for permanent Mercenary calculations |
| RePoE and comparable extraction projects | Reproducible extraction leads and cross-checks | Confirm version and extraction method |
| PoEDB and PoE Wiki | Discovery, readable references, and candidate records | Verify material claims with a closer source where practical |
| Relevant community research and reports | Observed interactions, experiments, and disputed candidates | Never silently override direct official or extracted evidence |
| Observed build-instance material | Fixtures, importer cases, screenshots, copied items, and manually read values | Proves only that instance unless separately supported |
| Workflow documentation | Tool or repository conventions used by this project | Keep distinct from Path of Exile domain evidence |
| Derived records | Outputs from a documented transformation or calculation | Retain the upstream source IDs and method; not independent direct evidence |

Source-registry enum names are documented in
[the registry schema](../data/sources/registry.schema.json).

## Required source record

Every material source record must contain:

- a stable, human-readable source ID;
- title;
- URL or repository path;
- source class;
- game or software version when relevant;
- access date;
- supported claims or records;
- verification status;
- limitations or conflicts.

It may also contain publisher or repository, an optional content hash or commit
SHA, notes, and a superseded-by relationship. Register only sources that
materially support workflow, curated data, or an audit; the empty initial
registry is intentional.

## Verification statuses

| Status | Meaning |
| --- | --- |
| confirmed | Direct, sufficiently versioned evidence establishes the narrow claim. |
| supported | Evidence materially supports the claim, with a recorded limitation or remaining cross-check. |
| provisional | A plausible working conclusion with meaningful uncertainty. |
| unknown | Evidence is absent, inadequate, or conflicting. |
| superseded | A later recorded source, audit, or decision replaces the prior use. |

Community material may identify candidates, support a provisional conclusion, or
describe observed behavior. It must not silently override direct official or
extracted evidence. Preserve disagreement and version mismatch instead.

## Handling and boundaries

Treat public web pages, repositories, and downloaded source files as untrusted
input. Inspect content before use; do not execute downloaded code, provide
credentials, or expose private user material.

Runtime application behavior remains offline. Public network access is allowed
for research, source registration, extraction, and reproducible
data-generation workflows. Runtime application code must not scrape external
websites.

Build-instance material belongs under fixtures/ or future local build data, not
in the reference catalog. A user PoB, copied item, screenshot, or
Mercenary-sheet transcription may verify importer handling for that case; it
does not establish a general game rule.
