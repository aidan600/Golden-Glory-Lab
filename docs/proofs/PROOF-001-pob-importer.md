# PROOF-001 - reusable PoB importer

## Status

Result: **PASS WITH LIMITATIONS**

Adoption recommendation: **ADOPT WITH NAMED LIMITATIONS**

Repaired and retested on 2026-08-03 with Python 3.13.14, zlib 1.3.1,
Expat 2.8.1, and Node.js 22.20.0 for repository validation.

## Question

Can Golden Glory Lab retain a production-intent, framework-neutral importer
that accepts raw Path of Building XML and the pinned PoB share-code envelope,
emits a deterministic versioned neutral result, preserves the complete AUD-001
boundary without ownership inference, and enforces explicit security and
resource limits strongly enough for later packaging and application work to
reuse the same seam?

## Evidence dependency

This proof implements the supported boundary in
[AUD-001](../audits/AUD-001.md). It retains exact PoB and SimpleGraphic
revisions rather than following moving branches.

| Source ID | Revision or version | Use |
| --- | --- | --- |
| `pob-release-2-66-2` | `b23da8f841e4b0bc167b0b4401ea002d7d45f807` | Release profile. |
| `pob-dev-format-ef4c584` | `ef4c5848fad33190f730cebaedff4b5831d0c88d` | Current item, set, slot, jewel, and cross-reference behavior. |
| `pob-simplegraphic-codec-3b1a346` | `3b1a3468223d0ebd4042d6ce76fc6144718ef79b` | zlib-wrapped share-code envelope. |
| `pob-pre-itemsets-1-4-36` | `69d4e4d4e4cfb82ccca0ebf609d6673e347a98dc` | Bounded legacy top-level slots. |
| `pob-itemsets-1-4-37` | `9f981583f7c721917124d604cddf0e8102e62714` | Transitional dual representation. |
| `pob-testbuilds-3-13-ef4c584` | pinned AUD-001 fixture directory | Representative upstream XML sizes and historical shapes. |
| `python-3-13-zlib-docs` | Python 3.13.14 docs | `MAX_WBITS`, `max_length`, `unconsumed_tail`, `unused_data`, and `eof`. |
| `python-3-13-expat-docs` | Python 3.13.14 docs | Incremental parsing, ordered attributes, entity controls, and reparse deferral. |
| `python-3-13-xml-security` | Python 3.13.14 docs, accessed 2026-08-03 | Current XML-vulnerability guidance and reviewed Expat floor. |
| `python-3-13-license-docs` | Python 3.13.14 docs | Python, Expat, and zlib license notices. |
| `setuptools-75-8-2` | 75.8.2 | Exact build backend and MIT license. |
| `jsonschema-4-26-0` | 4.26.0 | Exact proof-only Draft 2020-12 validator and MIT license. |
| `attrs-26-1-0` | 26.1.0 | Exact proof-only transitive dependency and MIT license. |
| `jsonschema-specifications-2025-9-1` | 2025.9.1 | Exact proof-only metaschema dependency and MIT license. |
| `referencing-0-37-0` | 0.37.0 | Exact proof-only reference dependency and MIT license. |
| `rpds-py-2026-6-3` | 2026.6.3 | Exact proof-only data-structure dependency and MIT license. |

The five pinned upstream XML fixtures are 26,191 to 65,185 bytes. The
purpose-built comprehensive synthetic fixture is 2,641 bytes. The default XML
ceiling is intentionally more than 100 times the largest inspected upstream
fixture while remaining finite.

## Implementation decision

The selected core remains Python 3.11+ with no third-party production runtime
dependencies. The package declaration stays `>=3.11` because every parse is
guarded against the actual linked Expat version; admission is not inferred from
the Python version. The sole build dependency is pinned to
`setuptools==75.8.2`.

The proof-only validator set is pinned exactly in
`requirements/pob-import-proof.txt` and installed into an isolated target with
`--no-deps`:

- `jsonschema==4.26.0`;
- `attrs==26.1.0`;
- `jsonschema-specifications==2025.9.1`;
- `referencing==0.37.0`;
- `rpds-py==2026.6.3`.

All five declare the MIT license. They do not appear in production package
metadata. The production importer uses only standard-library modules.

Python was selected because streaming zlib directly exposes bounded output,
end-of-stream state, and trailing-data state. Expat supplies ordered events,
ordered attributes, explicit DTD/entity handlers, and stable syntax locations
without selecting a desktop UI stack. The retained module is ordinary
importable Python; the proof CLI remains only a caller.

The current Python XML security documentation says Expat versions before 2.7.2
may be vulnerable to denial-of-service and disproportionate-memory issues. The
importer therefore requires parsed `pyexpat.EXPAT_VERSION >= 2.7.2` before it
constructs or feeds the parser. Unsupported or unparseable metadata returns
`XML_RUNTIME_UNSUPPORTED` at stage `xml`. Every envelope reports detected,
parsed, minimum, and status values. The parser explicitly keeps reparse
deferral enabled where that API is exposed. The proof runtime is Expat 2.8.1.

This floor is a reviewed admission boundary for the documented known risks,
not a promise that it covers every future Expat issue. Packaging must report
and retest its exact runtime.

### Packaging implications

A Python-native desktop shell may import the package directly. Another desktop
runtime may bundle a supported Python runtime and call the public module through
a narrow local bridge. The packaging proof must include the real module and
fixture rather than replace the importer. A candidate that cannot consume the
adopted seam requires an explicit architecture decision or rejection, not a
silent rewrite.

## Public production interface

| Artifact | Retained path or value |
| --- | --- |
| Importer package | `src/golden_glory_lab/pob_import/` |
| Raw XML entry point | `importPobRawXml(input, options)` |
| Share-code entry point | `importPobShareCode(input, options)` |
| Shared XML loader | `xml_tree.load_xml_tree`, called by the one semantic projector in `importer.py` |
| Deterministic serializer | `deterministic_json` and `deterministic_json_bytes` |
| Neutral contract | `data/schemas/pob-neutral-import-v1.schema.json` |
| Contract version | `1.0.0` |
| Implementation version | `pob-importer-python/0.1.1` |
| Limits | `ImportLimits` and `DEFAULT_IMPORT_LIMITS` in `limits.py` |
| Thin proof CLI | `proofs/pob_import_cli.py` |

The contract is a neutral intake result. It is not saved-build state,
ownership mapping, mechanics, catalog data, or persistence. Expected envelope,
decompression, runtime, and XML failures return stable public results.

## Limits and bounded processing

Every effective value is copied into each result envelope. Tests use smaller
overrides to exercise boundaries without committing large attack payloads.

| Limit | Proof default | Rationale and behavior |
| --- | ---: | --- |
| `maxShareCodeCharacters` | 4,000,000 characters | Checks the exact supplied string before trimming or UTF-8 work. |
| `maxDecodedCompressedBytes` | 3,000,000 bytes | Calculated from strict Base64 length before allocation, then checked after decode. |
| `maxDecompressedXmlBytes` | 8,000,000 bytes | Streaming zlib stops after at most one over-limit proof byte without retaining a complete oversized output. |
| `maxRawXmlBytes` | 8,000,000 UTF-8 bytes | Incremental strict UTF-8 observation discards retained bytes immediately after crossing the limit. |
| `maxXmlDepth` | 64 elements | Checked before retaining the next element. |
| `maxXmlElements` | 50,000 elements | Checked before retaining the next neutral node. |
| `maxAttributesPerElement` | 64 attributes | Checked before retaining the element; the whole-XML ceiling bounds the token first. |
| `maxTextBytesPerElement` | 1,000,000 normalized UTF-8 bytes | Incremented once per callback and checked before retaining an over-limit chunk. |
| `maxNumericLexemeDigits` | 128 digits | Rejects semantic decimal conversion before `int()` can reach protected large-integer behavior. |
| `maxReportEntries` | 256 entries | Later entries yield deterministic `REPORT_LIMIT_REACHED` metadata. |
| `inputEncodingChunkCharacters` | 4,096 characters | Bounds each strict UTF-8 encoding allocation used for counts and hashes. |
| `decompressionChunkBytes` | 16,384 bytes | Keeps decompression incremental and testable. |

Raw input is observed and hashed in bounded character chunks. The importer
retains at most one bounded accepted XML bytearray and reuses its count and hash
in the envelope. Once an oversized raw input crosses the limit, its retained
bytes are discarded while bounded chunks finish the count/hash observation.
The exact original Python string is preserved by reference. A share input that
already exceeds the character limit is rejected before UTF-8 encoding; its
byte state is `not-scanned-input-limit`.

The caller must still materialize the complete Python string before either
entry point is called. This proof bounds additional importer allocations; it
does not provide a streaming public input API.

For XML character data, each Expat callback is encoded once, added to an
incremental per-element byte count, and appended as a chunk only if within the
limit. Chunks are consolidated at structural or CDATA boundaries. Arbitrary
callback fragmentation is coalesced, while logical CDATA sections remain
distinct. The loader does not rescan retained text.

The adversarial regression produces more than 2,000 character callbacks with
2,000 repeated predefined entities. Instrumentation records one UTF-8 encoding
per callback and zero retained-text rescans. A 4,000-byte logical value succeeds
at the exact limit; 3,999 fails with `XML_TEXT_LIMIT`; repeated public imports
are byte-identical.

The oversized-allocation regression patches the single chunk-encoding seam.
A 4,000-byte multibyte raw string under a 10-byte XML limit is processed only
in chunks no larger than 28 bytes and never as a 4,000-byte encoded copy. A
2,000-character share code under a 10-character share limit invokes the encoder
zero times. Both preserve the original string object in their failure envelope.

## Hostile semantic input behavior

Decimal lexemes shorter than or equal to the configured digit limit are parsed.
Longer lexemes retain their raw value, produce `parsedId: null`, and resolve as
malformed semantic material without throwing. Remaining conversion failures
are caught through the same parser seam. Below, exact, above, and 5,000-digit
protected-conversion cases pass.

Python strings containing lone surrogates are also contained by the public
contract:

- raw XML returns `RAW_XML_UTF8_INVALID` at stage `xml`;
- share input returns `SHARE_CODE_UTF8_INVALID` at stage `envelope`.

Deterministic JSON uses ASCII escaping, so even these failure results serialize
without leaking `UnicodeEncodeError`.

## Reference semantics

`Items/@activeItemSet` has explicit context-specific states:

- absent attribute: `missing`;
- present empty, nonnumeric, or over digit limit: `malformed`;
- valid number with no declaration, including zero when undeclared: `unresolved`;
- valid number matching duplicate declarations: `ambiguous`;
- valid number matching one declaration: `resolved`.

There is no fallback to the first set. Zero is not shared across resolvers:
equipment slots and audited passive jewels retain their evidenced
`empty-reference` behavior, while active-set zero and item-set cross-reference
zero are ordinary numeric references.

Projection is structural and occurrence-aware. Passive jewels are recognized
only at `Tree/Spec/Sockets/Socket`. Item-set cross-references are recognized
only at `Skills/SkillSet/Skill/Gem`. Off-path `Tree/Future/Socket` and
`Skills/Future/Gem` nodes remain in the source tree and are not projected as
supported references.

## Fixture coverage

Every AUD-001 fixture-plan row names the actual fixture and assertion.

| AUD-001 row | Fixture or generated case | Test | Expected behavior | Result |
| --- | --- | --- | --- | --- |
| one set | `equivalent.xml` | `test_matrix_01_one_set_and_empty_slot` | One set and `itemId="0"` retained. | pass |
| explicit player and Mercenary candidates | `comprehensive.xml` | `test_matrix_02_explicit_player_and_mercenary_candidates_have_no_owner` | Both candidates retained with no owner field. | pass |
| multiple mapping candidates | `comprehensive.xml` | `test_matrix_03_multiple_mapping_candidates_are_manually_required` | All occurrence IDs reported for manual mapping. | pass |
| unnamed or generic sets | `duplicates-and-malformed.xml` | `test_matrix_04_title_states_and_duplicate_generic_titles` | Missing, empty, and duplicated generic titles remain distinct. | pass |
| alternate weapons | `comprehensive.xml` | `test_matrix_05_primary_and_alternate_weapons_are_all_retained` | Primary/swap assignments and boolean state retained. | pass |
| shield and quiver | `comprehensive.xml` | `test_matrix_06_shield_and_quiver_remain_weapon_2_assignments` | Item text distinguishes them; XML remains `Weapon 2`. | pass |
| Abyssal children | `comprehensive.xml` | `test_matrix_07_abyssal_children_include_empty_and_missing_parent_states` | Base, empty, multi-child, and missing-parent cases retained. | pass |
| passive jewels | `comprehensive.xml` | `test_matrix_08_passive_jewels_remain_separate_from_equipment` | Specs and zero reference remain separate from equipment. | pass |
| unused pool item | `comprehensive.xml` | `test_matrix_09_unused_pool_item_is_retained` | Retained and marked unused. | pass |
| reused and duplicate references | `duplicates-and-malformed.xml` | `test_matrix_10_reused_and_duplicate_references_never_last_write_win` | Ambiguous candidates and duplicate occurrences retained. | pass |
| observed out-of-range text | `comprehensive.xml` | `test_matrix_11_observed_out_of_range_text_is_opaque_and_unclamped` | `+999%` text retained without mechanics or clamping. | pass |
| XML text fidelity | `text-fidelity.xml`, generated endings, `preservation-events.xml` | `test_matrix_12_xml_entities_cdata_boundaries_and_line_endings`; `test_adjacent_cdata_and_document_level_events_are_preserved` | Exact envelope plus normalized character value; adjacent CDATA and surrounding events retained. | pass |
| malformed references | `duplicates-and-malformed.xml`, `active-set-states.xml` | `test_matrix_13_malformed_references_unknown_slots_attributes_and_elements`; `test_complete_active_item_set_state_matrix` | Malformed, unresolved, and ambiguous states are distinct; explicit unresolved active set is present. | pass |
| reimport candidates | reordered `reimport-before.xml` and `reimport-after.xml` | `test_matrix_14_reimport_candidates_expose_evidence_without_merge` | IDs `[1,2]` become `[2,1]`; hashes, Unique ID, titles, and order exposed with no merge. | pass |
| legacy and transitional | `legacy.xml`, `transitional.xml` | `test_matrix_15_legacy_synthesizes_once_and_transitional_does_not_double_count` | One synthesized legacy set; nested transitional set counted once. | pass |
| equivalent envelopes | `equivalent.xml`, `equivalent.share.txt` | `test_matrix_16_equivalent_raw_and_share_envelopes_have_same_semantics` | Document, source metadata, and report equal. | pass |
| fatal syntax | generated Base64/zlib/XML cases | `test_matrix_17_fatal_syntax_stops_without_partial_tree` | Stable stages, exact envelope, no partial document. | pass |
| hostile bounds | generated DTD/entity and structural cases | `test_matrix_18_hostile_bounds_and_all_limit_boundaries` | DTD and external entity rejected; load limits fail at intended stage. | pass |
| deterministic output | `comprehensive.xml` repeated three times | `test_matrix_19_deterministic_repetition_and_golden_output` | Byte-identical output and exact committed size/hash. | pass |

Supplementary repair fixtures and tests establish the full active-set matrix,
per-context zero behavior, audited structural paths, off-path retention,
fragmented-character behavior, allocation bounds, runtime guard, numeric limits,
lone-surrogate failures, document events, adjacent CDATA, schema conformance,
and deep result isolation. The complete suite contains 39 tests.

## Complete neutral-result schema

The Draft 2020-12 schema constrains success/failure invariants and every stable
production-facing nested structure: envelope, hashes, sizes, normalizations,
limits, runtime metadata, evidence, source metadata, game-target state,
document inventory, recursive ordered source nodes, document events, items,
sets, assignments, SocketIdURL records, active/passive/cross references, raw and
parsed states, candidate lists, usage, warnings, reports, and legacy or
transitional provenance. Stable objects use `additionalProperties: false`.
Arbitrary report-retained source material is the one intentional permissive
value; recursive source-tree node kinds remain closed and machine-checkable.

The real `Draft202012Validator` checks a representative success, envelope
failure, decompression failure, XML failure, malformed-but-readable success,
and committed golden. Negative checks remove a required document field and
replace a nested integer with a string; both must fail validation.

## Preservation observations

Byte-exact within the public string boundary:

- the exact caller-supplied string object;
- for successful share input, the strict-UTF-8 decoded XML string;
- SHA-256 digests over explicitly named byte domains.

Structurally retained:

- one root element and its complete ordered neutral event tree;
- elements, ordered attributes, text, logical CDATA sections, comments, and
  processing instructions inside the root;
- ordered document-level comments and processing instructions before and after
  the root, with one root marker in `documentEvents`;
- every item/set occurrence, assignment, audited reference, unknown source
  element/attribute, legacy occurrence, and report pointer.

Adjacent CDATA sections remain two nodes. Text adjacent to CDATA remains text.
Arbitrary Expat callback fragmentation is coalesced and is not represented as
a source boundary.

Normalized or derived:

- `xmlCharacterValue` follows XML-required entity and line-ending
  normalization and concatenates text/CDATA character values;
- numeric and boolean interpretations, hashes, usage counts, resolution states,
  occurrence IDs, and Abyssal parent hints remain separate from raw lexemes.

Unavailable from the selected dependency:

- trustworthy byte-exact per-element or per-item inner spans;
- original entity-reference spelling inside normalized values;
- pre-normalization per-item line endings.

The full original/decoded XML remains the only byte-fidelity authority. The
importer never reconstructs normalized XML and labels it original.

## Result isolation and determinism

Internal evidence metadata is a tuple of scalar pairs. Each result receives
fresh evidence dictionaries, limits, runtime metadata, codec steps, and
normalization arrays. A regression deeply mutates one result, then proves a
later result equals and serializes byte-identically to a pristine import;
default limits remain unchanged.

Three consecutive comprehensive-fixture runs produce identical bytes. The
regenerated committed golden is 87,288 bytes with SHA-256
`a1dc0f9fd312b82ab05307e1112906525fa75fab0e8f3c06265094f804da0429`.
Equivalent raw and share inputs produce identical `document`,
`sourceMetadata`, and `report` objects while retaining different envelope
metadata.

## Result

**PASS WITH LIMITATIONS**

The repaired proof satisfies the accepted production seam, resource, runtime,
preservation, isolation, ambiguity, ownership, schema, deterministic-output,
fixture, and CLI acceptance points. The result does not depend on timing-only
claims: instrumentation checks linear character handling and bounded encoding
allocations directly.

## Adoption recommendation

**ADOPT WITH NAMED LIMITATIONS**

Retain and reuse the importer package, versioned neutral contract, public entry
points, guarded limits, fixtures, golden, and tests. A packaged runtime must run
this boundary suite on its exact Python, zlib, and Expat versions and consume
the actual module.

## Named limitations

- Public entry points still receive a caller-materialized complete Python
  string; the importer bounds only its additional work and allocations.
- Expat recognizes a start-tag token before the handler can apply the
  per-element attribute-count limit; the whole-XML byte limit is the prior
  bound.
- The Expat 2.7.2 admission floor follows current official guidance and cannot
  pre-adjudicate future vulnerabilities.
- XML input is strict UTF-8; unrepresentable Python strings return stable
  failures rather than being repaired.
- Per-element byte spans, entity spelling, and pre-normalization inner line
  endings are unavailable; the complete input remains the byte authority.
- The suite runs on Python 3.13.14/Expat 2.8.1, while package metadata admits
  Python 3.11+ only when its linked Expat passes the runtime guard.
- The schema intentionally leaves only `report[].retainedMaterial` value
  content open because it can carry arbitrary preserved source material.

## Proof adoption and downstream consumption contract

The intended consumers are the desktop packaging proof and the first usable
desktop build. They must retain `src/golden_glory_lab/pob_import/`, contract
`1.0.0`, both public functions, limits, fixtures, golden, and regression tests.

The packaging proof must include this module, call one public entry point, and
parse a permanent synthetic fixture from inside the package. The first usable
build must extend that packaged shell, consume the neutral result, and add
explicit player/optional Mercenary mapping outside imported facts. Neither may
add a second importer. The proof CLI is disposable; the core and contract are
production-intent.

## Non-proofs

This proof does not establish a formal PoB schema, arbitrary historical or
future compatibility, item-modifier semantics, Path of Exile mechanics,
copied-item semantic parsing, permanent Mercenary stats, ownership inference,
reimport merging, saved-build persistence, desktop-framework suitability, UI,
or release readiness.

## Verification

One command reports the runtime, compiles sources, builds and installs an
isolated wheel, imports the installed package, installs the exact proof-only
validator set into a separate isolated target, runs all 39 tests, validates the
repository/schema/source registry/links, and checks whitespace:

```powershell
py scripts/validate/run_pob_import_proof.py
```

Additional checks:

```powershell
py -m ruff check src tests proofs scripts/generate_pob_import_goldens.py scripts/validate/run_pob_import_proof.py
node scripts/validate/check_repository.mjs
git diff --check origin/main...HEAD
```

The full proof gate passed twice on the runtime recorded above. The golden
generator reproduced the committed 87,288-byte artifact and recorded SHA-256.

## Recommended next action

After human review and merge of this draft proof, deliver AUD-002 through
AUD-005 as separately evidenced records in the planned first-release evidence
pack. Do not begin mechanics implementation until the relevant audit contracts
support it.
