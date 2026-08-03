# PROOF-001 — reusable PoB importer

## Status

Result: **PASS WITH LIMITATIONS**

Adoption recommendation: **ADOPT WITH NAMED LIMITATIONS**

Tested on 2026-08-02 with Python 3.13.14, zlib 1.3.1, Expat 2.8.1,
and Node.js 22.20.0 for the repository validator.

## Question

Can Golden Glory Lab retain a production-intent, framework-neutral importer
that accepts raw Path of Building XML and the pinned PoB share-code envelope,
emits a deterministic versioned neutral result, preserves the complete AUD-001
boundary without ownership inference, and enforces explicit security and
resource limits strongly enough for later packaging and application work to
reuse the same seam?

## Evidence dependency

This proof implements the supported boundary in
[AUD-001](../audits/AUD-001.md). It retains AUD-001's exact PoB and
SimpleGraphic revisions rather than following moving branches:

| Source ID | Revision or version | Use |
| --- | --- | --- |
| `pob-release-2-66-2` | `b23da8f841e4b0bc167b0b4401ea002d7d45f807` | Release profile. |
| `pob-dev-format-ef4c584` | `ef4c5848fad33190f730cebaedff4b5831d0c88d` | Current item, set, slot, jewel, and cross-reference behavior. |
| `pob-simplegraphic-codec-3b1a346` | `3b1a3468223d0ebd4042d6ce76fc6144718ef79b` | zlib-wrapped share-code envelope. |
| `pob-pre-itemsets-1-4-36` | `69d4e4d4e4cfb82ccca0ebf609d6673e347a98dc` | Bounded legacy top-level slots. |
| `pob-itemsets-1-4-37` | `9f981583f7c721917124d604cddf0e8102e62714` | Transitional dual representation. |
| `pob-testbuilds-3-13-ef4c584` | pinned AUD-001 fixture directory | Representative upstream XML sizes and historical shapes. |
| `python-3-13-zlib-docs` | Python 3.13.14 docs | `MAX_WBITS`, `max_length`, `unconsumed_tail`, `unused_data`, and `eof`. |
| `python-3-13-expat-docs` | Python 3.13.14 docs | Incremental parsing, ordered attributes, entity controls, and error locations. |
| `python-3-13-license-docs` | Python 3.13.14 docs | Python, Expat, and zlib license notices. |
| `setuptools-75-8-2` | 75.8.2 | Exact build-backend version and MIT license. |

The five pinned upstream XML fixtures are 26,191 to 65,185 bytes. The
purpose-built comprehensive synthetic fixture is 2,641 bytes. The default XML
ceiling is intentionally more than 100 times the largest inspected upstream
fixture while remaining finite.

## Implementation decision

The selected core is Python 3.11+ with no third-party runtime dependencies. The sole build dependency is pinned exactly to `setuptools==75.8.2`.
The proof environment is Python 3.13.14. It uses only `base64`, `hashlib`,
`json`, `zlib`, and `xml.parsers.expat` from the standard library.

Python was selected because the documented streaming zlib object provides the
three load-bearing states directly: bounded returned output, end-of-stream for
truncation detection, and unused bytes for trailing-data detection. Expat gives
ordered event parsing, ordered attributes, character/CDATA boundaries, stable
syntax locations, and explicit DTD/entity handlers without choosing a desktop
UI stack. The retained module is ordinary importable Python, while the proof
CLI is only a caller.

Alternatives considered:

- Node.js has mature zlib support, but requires selecting and pinning a separate
  XML parser and would bias the packaging proof toward a JavaScript desktop
  runtime without a product reason.
- Rust with `flate2`, `base64`, and an event XML crate could produce a compact
  native library, but adds a toolchain and several production dependencies
  before the packaging proof establishes that the extra boundary is useful.
- .NET offers strong XML facilities and Windows packaging, but would make the
  Windows desktop runtime a design input before the framework proof.
- A Python DOM parser or `lxml` would simplify traversal but would either
  materialize the tree before Golden Glory Lab's structural checks or add a
  binary dependency. The selected event loader retains only one implementation.

Python is under the PSF License Version 2. Incorporated Expat uses its MIT-style
license and zlib uses the zlib license. The exact setuptools 75.8.2 build
dependency uses the MIT license. No runtime package or multi-package lockfile
is needed, and this statement does not declare a license for the repository
itself.

### Packaging implications

A Python-native desktop shell may import the package directly. Another desktop
runtime may bundle a supported Python runtime and call the public module through
a narrow local bridge. The later packaging PROOF must include the real module
and fixture rather than replace the importer. If a packaging candidate cannot
reasonably ship or invoke the adopted Python seam, that is an explicit
architecture decision or a reason to reject the packaging candidate; it is not
permission for a silent rewrite.

## Public production interface

| Artifact | Retained path or value |
| --- | --- |
| Importer package | `src/golden_glory_lab/pob_import/` |
| Raw XML entry point | `importPobRawXml(input, options)` |
| Share-code entry point | `importPobShareCode(input, options)` |
| Shared XML loader | `xml_tree.load_xml_tree`, called by the one semantic projection in `importer.py` |
| Deterministic serializer | `deterministic_json` and `deterministic_json_bytes` |
| Neutral contract | `data/schemas/pob-neutral-import-v1.schema.json` |
| Contract version | `1.0.0` |
| Limits | `ImportLimits` and `DEFAULT_IMPORT_LIMITS` in `limits.py` |
| Thin proof CLI | `proofs/pob_import_cli.py` |

The contract is a neutral intake result. It is not the future saved-build
schema, ownership mapping, mechanics model, catalog, or persistence format.
Expected envelope, decompression, and XML failures return stable failure codes
and a retained source pointer instead of exposing only a stack trace.

## Limits

All effective values are included in each result envelope. Tests use smaller
overrides to exercise below, at, and above boundaries without committing large
attack payloads.

| Limit | Proof default | Rationale and observed behavior |
| --- | ---: | --- |
| `maxShareCodeCharacters` | 4,000,000 characters | Bounds the exact supplied string before trimming; paired with the 3 MB decoded ceiling and far above the inspected XML examples. |
| `maxDecodedCompressedBytes` | 3,000,000 bytes | Calculated from strict Base64 length before allocation, then checked after decode. |
| `maxDecompressedXmlBytes` | 8,000,000 bytes | Incremental zlib `max_length` enforcement stops after at most one over-limit proof byte and does not retain a complete oversized output. |
| `maxRawXmlBytes` | 8,000,000 UTF-8 bytes | Checked before Expat or the neutral tree is created. |
| `maxXmlDepth` | 64 elements | Checked in the start-element callback before a neutral node is appended. |
| `maxXmlElements` | 50,000 elements | Checked before retaining the next neutral node. |
| `maxAttributesPerElement` | 64 attributes | Checked before retaining the element; the whole XML byte ceiling also bounds the parser token. |
| `maxTextBytesPerElement` | 1,000,000 normalized UTF-8 bytes | Checked before character data is appended to the neutral tree. |
| `maxReportEntries` | 256 entries | Further entries replace the last retained entry with deterministic `REPORT_LIMIT_REACHED` metadata. |
| `decompressionChunkBytes` | 16,384 bytes | Keeps decompression incremental and testable without making this chunk size a format promise. |

These values are proof defaults, not automatically permanent release policy.
The packaging proof must run the retained boundary suite on its exact runtime.

## Fixture coverage

Every AUD-001 fixture-plan row has an independently named assertion.

| AUD-001 row | Fixture or generated case | Test | Expected behavior | Golden | Result |
| --- | --- | --- | --- | --- | --- |
| one set | `equivalent.xml` | `test_matrix_01_one_set_and_empty_slot` | One set and `itemId="0"` retained. | — | pass |
| explicit player and Mercenary candidates | `comprehensive.xml` | `test_matrix_02_explicit_player_and_mercenary_candidates_have_no_owner` | Both candidates, no ownership field; mapping example remains external. | comprehensive | pass |
| multiple Mercenary candidates | `comprehensive.xml` | `test_matrix_03_multiple_mapping_candidates_are_manually_required` | All three occurrence IDs reported as manually required. | comprehensive | pass |
| unnamed or generic sets | `duplicates-and-malformed.xml` | `test_matrix_04_title_states_and_duplicate_generic_titles` | Missing, empty, and duplicated generic titles remain distinct. | — | pass |
| alternate weapons | `comprehensive.xml` | `test_matrix_05_primary_and_alternate_weapons_are_all_retained` | Primary/swap assignments and true/false state retained. | comprehensive | pass |
| shield and quiver | `comprehensive.xml` | `test_matrix_06_shield_and_quiver_remain_weapon_2_assignments` | Item text distinguishes them; XML remains `Weapon 2`. | comprehensive | pass |
| Abyssal children | `comprehensive.xml` | `test_matrix_07_abyssal_children_include_empty_and_missing_parent_states` | Base, empty, multi-child, and missing-parent cases retained; parent is derived. | comprehensive | pass |
| passive jewels | `comprehensive.xml` | `test_matrix_08_passive_jewels_remain_separate_from_equipment` | Two specs and zero reference remain separate from equipment. | comprehensive | pass |
| unused pool item | `comprehensive.xml` | `test_matrix_09_unused_pool_item_is_retained` | Retained and marked unused. | comprehensive | pass |
| reused and duplicated references | `duplicates-and-malformed.xml` | `test_matrix_10_reused_and_duplicate_references_never_last_write_win` | Candidate sets remain ambiguous; duplicate assignments remain occurrences. | — | pass |
| observed out-of-range text | `comprehensive.xml` | `test_matrix_11_observed_out_of_range_text_is_opaque_and_unclamped` | `+999%` text retained without clamping, mechanics, or ownership. | comprehensive | pass |
| XML text fidelity | `text-fidelity.xml` plus generated mixed endings | `test_matrix_12_xml_entities_cdata_boundaries_and_line_endings` | Exact envelope retained; XML character value is normalized and complete. | — | pass |
| malformed references | `duplicates-and-malformed.xml` | `test_matrix_13_malformed_references_unknown_slots_attributes_and_elements` | Siblings continue; malformed, unresolved, ambiguous, and unknown states remain distinct. | — | pass |
| reimport candidates | `reimport-before.xml`, `reimport-after.xml` | `test_matrix_14_reimport_candidates_expose_evidence_without_merge` | Hashes, Unique ID line, raw IDs, order, and titles exposed; no merge. | — | pass |
| legacy and transitional | `legacy.xml`, `transitional.xml` | `test_matrix_15_legacy_synthesizes_once_and_transitional_does_not_double_count` | One synthesized legacy set; nested transitional set counted once. | — | pass |
| equivalent envelopes | `equivalent.xml`, `equivalent.share.txt` | `test_matrix_16_equivalent_raw_and_share_envelopes_have_same_semantics` | Document, source metadata, and report equal; envelopes differ. | — | pass |
| fatal syntax | generated Base64/zlib/XML cases | `test_matrix_17_fatal_syntax_stops_without_partial_tree` | Stable stage code, exact envelope, and no partial document. | — | pass |
| hostile bounds | generated DTD/entity, expansion, and structural boundaries | `test_matrix_18_hostile_bounds_and_all_limit_boundaries` | DTD rejected; all load-bearing limits fail at the intended stage. | — | pass |
| deterministic output | `comprehensive.xml` repeated three times | `test_matrix_19_deterministic_repetition_and_golden_output` | Byte-identical output and committed golden match. | comprehensive | pass |

The complete suite has 29 tests because public-contract, normalization, CLI,
schema, and default-limit assertions supplement the 19 matrix rows.

## Security observations

- Base64 accepts only the PoB URL-safe alphabet and terminal padding. Outer
  ASCII whitespace and restored missing padding are the only permitted
  normalizations and are recorded. Internal whitespace and arbitrary invalid
  characters fail.
- `zlib.MAX_WBITS` requires the zlib header/trailer. Raw DEFLATE fails.
  `eof` distinguishes truncation, and `unused_data` plus unread input detects
  trailing bytes. Decompression output is bounded incrementally.
- DTD start, entity declarations, and external-entity references are rejected.
  Parameter-entity parsing is disabled. The importer contains no network API or
  resolver and performs no network access.
- Ill-formed XML produces no document tree. Semantic bad values continue through
  readable siblings and become ordered report entries.
- XML byte size is checked before Expat. Depth, element count, and retained text
  are checked before neutral-tree retention. Expat necessarily recognizes a
  start-tag token and presents its attribute list before the handler can enforce
  the per-element attribute count; the 8 MB whole-XML ceiling is the prior bound.
- The raw-XML and share-code public functions accept complete caller strings, so
  the caller has already materialized the supplied envelope. The importer bounds
  every subsequent UTF-8, Base64, decompression, parser, tree, and report step.

## Preservation observations

Byte-exact within the public string boundary:

- the exact caller-supplied string;
- for a successful share code, the exact strict-UTF-8 decoded XML string;
- SHA-256 digests over explicitly named UTF-8 or compressed-byte domains.

Structurally retained:

- the complete ordered Expat event tree, including elements, ordered
  attributes, text, CDATA segments, comments, and processing instructions;
- every pool item and item-set occurrence, assignment, relevant reference,
  unknown attribute/element, legacy source occurrence, and report pointer.

Normalized or derived:

- item `xmlCharacterValue` follows XML-required entity and line-ending
  normalization and concatenates text/CDATA character data;
- numeric and boolean interpretations, hashes, usage counts, resolution states,
  deterministic occurrence IDs, and Abyssal parent hints are derived and remain
  separate from original lexemes.

Unavailable from the selected dependency:

- trustworthy byte-exact per-element or per-item inner spans;
- original entity-reference spelling inside a normalized item value;
- pre-normalization per-item line endings.

The full original/decoded XML is therefore the only byte-fidelity authority.
The importer never reconstructs normalized XML and labels it original.

## Determinism observations

Three consecutive comprehensive-fixture runs produced identical bytes. The
committed golden is 86,562 bytes with SHA-256
`ccf7e7e7f977bfde1dd366255c6ae921a7c8fcd585bd89c1066b62bc7f2a4419`.
Equivalent raw and share-code inputs produced identical `document`,
`sourceMetadata`, and `report` objects while retaining different envelope
metadata.

Determinism fixes field construction order, source/report/candidate array order,
serializer indentation and separators, Unicode handling, hashes and byte
domains, and final newline. Results contain no timestamps, random identifiers,
absolute local paths, or unordered-set output.

## Result

**PASS WITH LIMITATIONS**

The proof satisfies AUD-001's production seam, security, preservation,
ambiguity, ownership, deterministic-output, fixture, and CLI acceptance points.
The named limitations are the complete-string caller boundary, Expat's
token-before-handler attribute behavior under the prior 8 MB ceiling, strict
UTF-8 XML intake, lack of byte-exact inner spans, and validation on Python
3.13.14 rather than every Python version admitted by package metadata.

## Adoption recommendation

**ADOPT WITH NAMED LIMITATIONS**

Retain and reuse the importer package, versioned neutral contract, public entry
points, limits, fixtures, golden, and tests. Do not copy the proof CLI's process
boundary into product architecture by assumption. A packaged runtime must run
the same regression suite and consume the actual module.

## Proof adoption and downstream consumption contract

### Intended downstream consumers

1. Desktop packaging PROOF.
2. First usable desktop BUILD.

### Production-facing artifacts retained

- `src/golden_glory_lab/pob_import/`;
- neutral result contract `1.0.0`;
- `importPobRawXml` and `importPobShareCode`;
- `ImportLimits` and default security configuration;
- `fixtures/pob/proof/` and `fixtures/pob/golden/`;
- `tests/test_pob_importer.py`.

### Packaging PROOF consumption requirement

The later packaging PROOF must include this actual adopted module, invoke one
of these same public entry points, and parse at least one permanent synthetic
fixture from inside the packaged application. It must demonstrate that the
packaged runtime executes the importer and that the importer regression suite
remains runnable in the selected development environment. It must not create a
second importer.

If a packaging runtime cannot reasonably consume the adopted seam, record an
explicit architecture decision or reject that packaging approach. Do not
silently rewrite the importer.

### First usable BUILD consumption requirement

The first usable BUILD must extend the adopted packaged shell, call these entry
points, consume neutral contract `1.0.0`, and add explicit player/optional
Mercenary mapping outside imported facts. Mechanics, persistence, and UI wrap
the importer; they do not replace it. Retain the regression suite. Replacing the
importer requires explicit rationale, migration impact, regression comparison,
and review.

The proof CLI is disposable. The core, contract, limits, fixtures, golden, and
tests are production-intent artifacts.

## Non-proofs

This proof does not establish:

- a formal PoB schema;
- arbitrary historical or future compatibility;
- item-modifier semantics;
- Path of Exile mechanics;
- copied-item semantic parsing;
- permanent Mercenary stats;
- ownership inference;
- reimport merging;
- the saved-build schema;
- desktop framework suitability;
- UI or release readiness.

## Verification

One command runs installation, compilation, the complete fixture matrix,
golden comparison, deterministic repetition, raw/share equivalence, security
cases, CLI smoke tests, baseline repository validation, and whitespace checks:

```powershell
py scripts/validate/run_pob_import_proof.py
```

Additional review commands:

```powershell
py -m ruff check src tests proofs scripts/generate_pob_import_goldens.py scripts/validate/run_pob_import_proof.py
node scripts/validate/check_repository.mjs
git diff --check origin/main...HEAD
```

The complete suite passed on the runtime recorded above. The generator command
`py scripts/generate_pob_import_goldens.py` reproduced the committed golden and
its recorded SHA-256.

## Recommended next action

Deliver AUD-002 through AUD-005 as four separately identified and evidenced
records, sequenced within one first-release evidence-pack PR. Each record must
end with an implementation contract naming required inputs, established rules,
unsupported/provisional/manually required behavior, machine-readable tables or
fixtures supported by evidence, and its expected downstream module or user
flow. Do not begin mechanics implementation until the relevant audit contract
supports it.
