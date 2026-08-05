# BUILD-001 - Desktop Intake, Mapping, and Persistence

Mode: BUILD

Date: 2026-08-04

Status: implemented and validated

## Outcome

Golden Glory Lab now has a packaged offline Windows desktop workflow. A user
can import Path of Building raw XML or a share code through the adopted
`golden_glory_lab.pob_import` seam, review every item-set occurrence without
ownership inference, explicitly map Player and permanent Mercenary roles, use
opaque manual Mercenary equipment instead, and save or reopen a local build.

All mechanics that remain below their evidence gates are displayed as
`unavailable-pending-evidence` with no numeric substitute.

## Scope and exclusions

BUILD-001 adds intake adapters, a canonical build-state contract, a session
service, Tkinter/ttk presentation, local persistence, committed fixtures,
tests, an isolated quality gate, and an installed-wheel PyInstaller runner.

It does not add or replace the importer, infer ownership, parse copied items
into recognized stats, derive permanent-Mercenary sheet values, implement
Golden Glory, Flame Link, Enmity, penetration, damage, or DPS formulas, add a
combined score, scrape the web, or add an application networking feature.
Later disposition of OQ-002 through OQ-007 is recorded in
[CURRENT_STATE.md](../CURRENT_STATE.md) and [OPEN_QUESTIONS.md](../OPEN_QUESTIONS.md);
AUD-006 was not created.

## Architecture and DEC-001

[DEC-001](../decisions/DEC-001-desktop-ui-toolkit.md) selects standard-library
Tkinter/ttk for this BUILD. The application remains one Python process and has
no PyPI production dependency or second local service.

The layers remain independent:

1. `pob_import` owns neutral PoB import and deterministic importer bytes.
2. `build_state` owns the versioned canonical document and atomic persistence.
3. `desktop.intake` applies desktop pre-invocation file/text boundaries.
4. `desktop.service` owns transient session state and user operations.
5. `desktop.app` owns presentation and prompts.
6. `desktop.self_test` exercises the installed packaged workflow.

No presentation code reproduces importer or mechanics formulas.

## Importer and packaging dependencies

The application project metadata retains `dependencies = []`. Tkinter,
Tcl/Tk, Expat, and zlib are interpreter components. The Windows package is a
PyInstaller 6.21.0 one-directory GUI bundle using the exact proof pins in
`requirements/desktop-packaging-proof.txt`.

The build runner creates a fresh virtual environment, builds and installs the
project wheel, freezes the installed launcher, verifies application module
origins from that installation, copies the package outside the repository, and
runs it from an empty working directory. Network access is used only for
proof/build dependency provisioning when a cache is unavailable.

Ruff 0.15.22 is an MIT-licensed proof/development dependency pinned in
`requirements/build-quality.txt`. Its source is the registered PyPI package
metadata. The reviewed correctness gate selects `E4`, `E7`, `E9`, and
`F` in `pyproject.toml`; no formatter was added.

## Canonical and session state

The canonical JSON document contains exactly:

- `documentType`;
- `schemaVersion`;
- `applicationDataContractVersion`;
- `importerContractVersion`;
- the complete successful `importedResult`;
- `importedResultSha256`, calculated from adopted importer canonical bytes;
- explicit Player and Mercenary occurrence references;
- `mercenarySourceMode`;
- opaque manual Mercenary equipment;
- user notes.

Volatile data remains session-only: current path, baseline bytes, dirty state,
readiness, the last failed import attempt, pending successful replacement,
selected UI rows/tabs, dialogs, and evidence presentation. It is never
serialized.

All four version markers are `1.0.0` where applicable. The runtime codec
rejects unknown or missing root fields, duplicate JSON keys, nonfinite numbers,
invalid UTF-8, wrong document/contract versions, bad digests, invalid mapping
references, a shared Player/Mercenary occurrence, invalid manual entries, and
inconsistent source-mode fields.

## Input limits

Desktop raw XML intake performs `stat` before opening the file, rejects a
size above 8,000,000 bytes, reads at most 8,000,001 bytes once, detects growth,
and decodes strict UTF-8 before calling `importPobRawXml`.

Pasted share-code input is type-checked and rejected above 4,000,000
characters before `importPobShareCode`. The adopted importer retains its
decoded/compressed/XML depth, element, attribute, text, numeric-lexeme, and
report limits.

The state contract permits at most 64 manual entries. Slot labels are limited
to 80 characters, exact raw text to 100,000, each manual note to 10,000, and
user notes to 100,000 characters. Observed raw values are preserved rather
than clamped to a natural range.

Saved-state open has a separately derived support envelope of 597,251,456
bytes. It consists of eight conservative retained or projected copies of the
8,000,000-byte XML envelope at six JSON bytes per source byte (384,000,000):
envelope input, decoded XML, source tree, item character projection, ordered
child material, classified unknown material, retained report material, and
metadata or attribute projection. The 4,000,000-character share-code envelope
is then included at the same conservative factor
(24,000,000), 50,000 elements by depth 64 at 32 structural bytes per pair
(102,400,000), all maximum manual and user strings at 12 JSON bytes per Python
character (85,802,880), and 1 MiB for fixed contract and report material
(1,048,576). Files above that producer-derived envelope are unsupported even
when externally authored content otherwise resembles the schema.

Open stats before reading, rejects an already oversized file without opening
it, reads at most the limit plus one byte, and rejects growth during the read.
Stable failures distinguish file access, initial size, growth, invalid UTF-8,
JSON syntax, excessive JSON nesting, and Python's integer-string conversion
limit. Only expected boundary failures are contained; resource exhaustion such
as `MemoryError` is deliberately not converted into an ordinary validation
result.

## Import attempts

A failed desktop boundary check or importer result is transient. It preserves
the current canonical document, mappings, manual entries, notes, baseline,
dirty state, and readiness while exposing the failed attempt for review.

A successful import is staged when it would replace an imported document.
After explicit confirmation it replaces the embedded import, clears both
occurrence mappings, returns Mercenary source mode to not-yet-selected, and
preserves manual entries and notes. The user must map again.

## Item-set review and mapping

All importer occurrences are enumerated in source order with their occurrence
ID, source ID/title states, active/weapon-set states, assignments, warnings,
ambiguity, and retained raw material. Duplicate source IDs or titles do not
collapse occurrences.

Player ownership is always a selected occurrence ID. A mapped Mercenary also
requires a selected occurrence ID distinct from the Player's. The third
permanent-fixture occurrence remains visible when Player and Mercenary consume
the first two. Switching to manual mode deactivates but does not delete manual
entries; selecting mapped mode likewise preserves them.

Opaque manual equipment has explicit add, edit, and confirmed-delete actions.
Its exact raw/descriptive text remains unparsed and is marked
`unparsed-manual`. The packaged walkthrough found and repaired an Enter-key
propagation defect so multiline raw item text now remains in the text widget
instead of activating the dialog's OK action.

## Persistence

Serialization is strict UTF-8 JSON with fixed root/manual key order, two-space
indentation, no nonfinite values, ASCII escapes, and one terminal newline. The
embedded importer result retains its original key order so its adopted digest
survives enclosure.

Save serializes and validates completely, writes a temporary file in the
destination directory, flushes and fsyncs it, and atomically replaces the
destination with `os.replace`. A failed replacement preserves the prior file
and cleans the temporary file. Open validates fully before replacing the
session. Repeated save/open produces identical bytes.

The runtime codec intentionally validates only the neutral structures consumed
by BUILD-001 and preserves other importer-owned material. The Draft 2020-12
schema provides the complete test-time composition with
`pob-neutral-import-v1.schema.json`; it is not a production dependency or a
duplicate runtime schema engine.

The consumed imported-item boundary requires nonempty globally unique item
occurrence IDs; nonnegative, non-boolean source occurrence indices; raw ID
state/value shape; exact raw character value; ordered child material; a usage
object whose displayed state is `unused` or `referenced`; and string warnings.
The complete importer-produced `rawId` and `usage` objects, source order, raw
text, and child material survive deterministic save/reopen. Other
importer-owned item fields remain opaque and preserved.

Item-set occurrence IDs are nonempty and globally unique, item-set source
indices are nonnegative integers excluding booleans, and assignment IDs are
nonempty and unique within their item set. Resolution candidate cardinality
must match the resolution state; an equipment assignment cannot claim
`missing`. All ten report fields are required, report IDs are nonempty and
unique, category and stage use the adopted enum values, and candidate targets
are strings. `retainedMaterial` remains intentionally opaque and survives
round trips. Runtime-only Treeview identifier uniqueness is tested alongside
shared runtime/schema parity; assignment IDs may repeat across different item
sets because selection is occurrence-scoped.

Serialization, digesting, and defensive copying translate deterministic
recursion failures into stable build-state errors. Open remains transactional:
size, growth, numeric, nesting, imported-item, report, ID, source-index,
resolution, and serialization failures leave the current document, baseline,
path, dirty state, readiness, mappings, manual equipment, and notes unchanged.

## Evidence states

Seven outputs are explicit nonnumeric unavailable states:

- derived permanent-Mercenary sheet values;
- complete Light Radius/direct-Link calculation;
- Golden Glory arithmetic;
- definitive Flame Link granted damage;
- sheet-derived or aggregate Enmity;
- total penetration;
- damage and DPS.

Each status is `unavailable-pending-evidence`, has `value: null`, explains
the missing evidence, and references the relevant AUD-002 through AUD-005
claim IDs. Unavailable is never represented as zero, and none of these fields
is persisted in the canonical document.

## Packaged validation

Final validation built the installed wheel in a disposable environment and
copied a PyInstaller one-directory Windows GUI application outside the
repository. The repaired result contained 989 files and 27,862,679 bytes. The
GUI executable SHA-256 was
`26d74815009bc13c4537eb985ab529a07883c4dc802fee7632f252ff43cc55bb`;
the bundle tree SHA-256 was
`e4bebca15a64ab5459a06c1e66a55e179aa4282b8df3f9782d7ca7ca7a120609`.
The installed wheel SHA-256 was
`1d4be92e9c4481f44da6c3093b7719f27f9fc35079ebf660ec958ccc637d48fb`.

The executable uses Windows GUI subsystem 2 and therefore has no console
window. The bundle contains `_tkinter.pyd`, Tcl and Tk initializer trees, and
the permanent proof fixture. Its runtime was Python 3.13.14, Tcl 8.6.15,
Tk 8.6.15, Expat 2.8.1, and zlib 1.3.1.

Three copied-package self-tests passed from an empty working directory with
sanitized Python variables. Their JSON bytes were identical, with SHA-256
`596e1c1e5ca0f97925c3b62b9d421bd342b26e44789312febfd93e35ce1781b5`.
The test imported all three occurrences, mapped the Player, selected manual
mode, added opaque equipment, saved/reopened deterministically, verified the
import digest, kept seven mechanics unavailable, and found no invented
ownership or mechanics field.

Static source inspection found no network-client imports and project metadata
had no `Requires-Dist`. This establishes no intended runtime networking; it
does not enforce outbound denial. PROOF-002's firewall/VM limitation remains.

## Manual Windows walkthrough

The copied corrected package was walked through on Windows 11 Home
10.0.26200 (build 26200) at 100% scaling:

1. normal GUI launch produced no console;
2. the permanent raw XML fixture imported through the native file dialog;
3. all three distinct occurrences were visible in source order;
4. Player mapped explicitly to `item-set-0001`;
5. Mercenary mapped explicitly and distinctly to `item-set-0002`;
6. assignment slots, raw item JSON/text, and importer warnings were reviewable;
7. `item-set-0003` remained visible and unmapped;
8. Mercenary switched back to opaque manual mode without deleting entries;
9. a five-line Body Armour entry containing
   `Fire Resistance 250 out of natural range` was added;
10. Save As wrote a canonical local file and displayed atomic-save confirmation;
11. the clean window closed normally;
12. the copied application relaunched and opened the saved file;
13. Player mapping, manual mode, complete imported content, digest, multiline
    raw text, and note survived;
14. all seven mechanics remained unavailable and nonnumeric.

The focused repair was then exercised in the repaired package against a saved
mapped state. Attempting to map Player to the selected Mercenary occurrence
showed `SAME_OCCURRENCE_MAPPING` and restored Player to `item-set-0001` while
Mercenary remained `item-set-0002`. Attempting the reverse mapping showed the
same stable error and restored the same visible selections. Notes accepted and
saved exactly 100,000 characters. A 100,001st character showed
`USER_NOTES_LIMIT`; after dismissal the visible editor again contained exactly
the prior 100,000 characters, the title had no dirty marker, and status remained
saved and intake-ready. The application then closed normally.

At 1220 by 820 the main split view, tab labels, tree headers, and scrollbars
were readable with no application clipping. Focus behavior was normal in the
application. The automation host had unrelated always-on-top and multi-monitor
windows, so captures temporarily raised and repositioned the app; this was an
inspection-environment limitation, not an application focus defect. The
minimum 980 by 700 content size retains the item-table scrollbars, but the
crowded right-notebook tab captions truncate. The content remains
keyboard-accessible, but clearer compact captions are a named hardening item.
Broader DPI and multi-monitor ordinary-user testing also remains.

## Verification

The final 85-test suite covers empty/imported/mapped/manual round trips, strict
and unknown-version failures, digest/order preservation, runtime/schema parity,
fixture validity, atomic failure safety, transient attempt preservation,
replacement confirmation, exact and over-limit saved-state boundaries, file
growth, numeric and nesting containment, deterministic recursion failures,
complete consumed-item/report/occurrence validation, transactional malformed
open, both adopted importer calls, occurrence-scoped mapping, rejected-edit UI
restoration, manual mode, evidence states, and multiline dialog input. The
imported-item matrix sends malformed raw IDs, usage values, and source indices
through a real saved `ApplicationService.open`; shared schema/runtime parity
rejects every candidate, and a headless item-review rebuild proves rejected
material cannot reach a row or detail while valid source-order items still
render.

The fixture generator dry run, Draft 2020-12 schema self-check and fixture gate,
focused negative corpus, Ruff, compileall, diff whitespace check, evidence gate,
repository gate, installed-wheel package build, and three copied-package
self-tests are rerun for the repaired boundary. Generated wheels, executables,
virtual environments, PyInstaller work/spec trees, screenshots, and walkthrough
state remain outside the repository and are not committed.

## Limitations and next BUILD slice

This is a Windows-first BUILD using Tkinter/ttk. The package is not an
installer or signed release. Python-free Windows Sandbox/VM execution and
enforced outbound denial remain unproven. Ordinary-user DPI, accessibility,
and broader multi-monitor hardening are still needed.

Phase 3 is in progress, not complete. The exact next BUILD slice is a
recognized copied-item/manual-input parser and evidence-aware calculation
enablement for only those mechanics whose exact claim/version gates are
satisfied. It must continue to preserve original item text and out-of-natural-
range observed values, and it must not turn blocked mechanics into zero.
