# BUILD-002 - Copied-Item Recognition and Isolated Enmity Reporting

Mode: BUILD

Date: 2026-08-04

Status: implemented and validated

## Outcome

Golden Glory Lab now accepts bounded Path of Exile copied-item text without
rewriting it, derives one provenance-aware review model across PoB, copied, and
opaque manual sources, evaluates exact machine-readable evidence gates, and
can report the manually supplied isolated `Enmity’s own Fire Penetration
contribution` with Enmity-only target comparisons.

The result is deliberately not total penetration. Derived permanent-Mercenary
values, equipment aggregation, Enmity's resistance-penalty reconstruction,
enemy resistance, Light Radius, Golden Glory, Flame Link, damage, DPS,
recommendations, critical strikes, and a combined score remain unavailable and
nonnumeric.

## Copied-item recognition boundary

`golden_glory_lab.item_review` is a deterministic, side-effect-free,
standard-library recognizer. It preserves the exact supplied Unicode string,
including LF or CRLF line endings, blank and separator lines, capitalization,
leading/trailing material, and unsupported content. SHA-256 is calculated from
strict UTF-8 bytes. Lone surrogates and over-limit input fail before parsing;
parsing uses only a transient normalized view, and every normalization is
reported against exact offsets and line locations in the retained source.

The v1 limits are 64 copied entries; 100,000 raw-text characters per entry;
80 characters each for entry ID, user label, and slot label; and 10,000 note
characters. No accepted input is silently truncated.

The recognizer understands a bounded English copied-item envelope, ordered
sections and separators, basic rarity/name/base identity, and exact Enmity's
Embrace identity plus reviewed natural-range metadata. It does not implement a
universal modifier grammar, localization, resistance or damage semantics,
requirements, sockets, stacking, corruption/influence, crafting, legacy
conversion, availability, ownership, or equipped-state inference. Unknown
property/modifier lines remain ordered raw material. Observed out-of-natural-
range text remains unchanged and is reported informationally, never clamped.

The tested state-aggregation order is:

1. `malformed` for a malformed supported envelope or required boundary;
2. `manually-required` when an identity decision cannot safely be made;
3. `partially-recognized` when supported facts coexist with ambiguous or
   unrecognized in-scope material;
4. `unrecognized` when no supported structure or identity was recognized;
5. `recognized` when every in-scope element was recognized or explicitly
   ignored as irrelevant.

Reports use `recognized`, `ignored as irrelevant`, `unrecognized`,
`ambiguous`, `manually required`, and `malformed`. An irrelevant report does
not reduce an otherwise recognized state, and ties select the less-confident
state.

This resolves OQ-007 only for exact-text preservation, bounded structural and
Enmity-identity recognition, deterministic locations, and explicit review
reports. General modifier semantics, broad localization, and broad catalog
parsing remain outside v1.

## Common item review and provenance

The common review is derived after open and is never persisted as a duplicate
projection. It adapts PoB item-pool occurrences with all explicit assignment
bindings, copied entries, and opaque manual Mercenary equipment. Every review
instance exposes a deterministic ID, canonical source/entry identity,
provenance (`pob-import`, `copied-text`, or `manual-entry`), exact raw text and
digest, typed source locator, zero or more explicit role bindings, binding
basis, slot/assignment labels, recognition state and reports, supported
identity, and the source-owned user note.

Copied-entry admission remains nonempty and at most 100,000 characters. PoB
retained item text is reviewed through a separate retained-source path that
accepts every strict-UTF-8 value already admitted by the neutral importer,
including empty text and text larger than the copied-entry limit. Empty PoB
text yields an explicit unrecognized/manually-required review report without
raising. Text above the copied-recognition analysis limit keeps the exact text
and digest, preserves provenance bindings, and returns one bounded
source-limit report instead of a line-by-line parse. This is a review state, not
an import rejection. Common review is therefore total over every accepted
canonical source.

A PoB source item stays one logical item even when multiple assignments bind
it. Roles come only from explicit Player/Mercenary occurrence mappings,
explicit copied metadata, or the manual-Mercenary entry path. Unmapped items
remain visible. Item-set order/title/active state, item names, recognized
Enmity identity, modifiers, and minion references never infer ownership or
equipped state.

The desktop adds copied-item paste/edit/delete, confirmation when deleting a
referenced source, filters for provenance/role/recognition, exact selectable
raw material, ordered report detail, and retained neutral-import detail. The
optional observed Enmity item uses a typed canonical source locator, not a
widget row ID. Confirmed deletion or successful import replacement atomically
clears a reference and changes its source; cancellation preserves both.
Rejected Enmity form edits leave canonical state unchanged and restore U, M,
target, equipped/inclusion/acknowledgement controls, measurement-context
fields, observed-item selection, result/target panels, exact gate detail,
status, title, dirty state, and migration state from canonical service state.

## Runtime evidence manifest and exact gates

The packaged resources are:

- `golden_glory_lab.runtime_data/enmity-reference-v1.json`;
- `golden_glory_lab.runtime_data/enmity-manual-gate-v1.json`;
- `data/schemas/runtime-evidence-gate-v1.schema.json`.

Canonical evidence bytes are the Git blob bytes under an explicit
`.gitattributes` LF checkout policy for the five pinned sources and packaged
runtime JSON resources. The build-time validator proves each pinned path is
tracked, its canonical tracked bytes use LF, the manifest hash equals SHA-256 of
those canonical bytes, and a conforming working tree matches those bytes. It
does not silently normalize arbitrary bytes after reading them.

The runtime manifest is version `1.0.0`, loaded only through package-resource
APIs. It does not read Markdown, the repository root, the current working
directory, or a development path. Its pinned manifest SHA-256 is
`ba1886d67324c75a40997cbd761a81424247ba6995f45898b2b627117190528d`;
the packaged Enmity reference SHA-256 is
`949b75154049bb4d1fb0ea55c6f640a43d95f09da26fd4deabf5b51e2303ce19`.

The build-time validator hashes tracked file bytes and compares exact audit,
contract, claim, status, polarity, policy, target-version, output, source, and
consumer contracts. The manifest pins these source bytes:

- `docs/audits/AUD-002.md`:
  `711568e6036ae4a8168ba69516bd20c43cf0d00d5debf2bbc3e7342df39a6779`;
- `docs/audits/AUD-005.md`:
  `5d1206af0199d34502f75e3a0e3d4ceb9a6fe67b51217cbee890d896128edfb2`;
- `data/curated/aud-002-mercenary-input-contract-v1.json`:
  `513c04020776a06447ca42a2d2f0a1eafd59ff111169510315a536ddf1cd78b1`;
- `data/curated/aud-005-enmitys-embrace-reference-v1.json`:
  `de4a2ba40b1512705536172e0777048777df6b68bb8d3571690d1a667d901c2d`;
- `fixtures/mechanics/aud-005-enmitys-embrace-gates-v1.json`:
  `72d6316c8a1ec8e006a3bedae11b26aa0568390f68fa02ff4ee40ea61ab46b89`.

The isolated contribution requires AUD-005 contract `1.0.0`, positive-
capability claims `AUD-005-C03` and `AUD-005-C04` at a `supported` minimum,
AUD-002 contract `1.0.0`, and policy `AUD-002-C06` in its explicit adopted/
supported mode. Enmity-only target reporting additionally requires policy
`AUD-005-C10`. `confirmed` satisfies a supported minimum; supported does not
satisfy a confirmed minimum. Policy gates have no ordinal `minimumStatus`.
Unknown, provisional, superseded, absent, polarity-mismatched, policy-mode-
mismatched, contract-mismatched, and target-version-mismatched inputs fail.

Every failure has typed reasons and claim/source references, returns null
rather than zero, and withdraws only its smallest dependent output. A missing,
malformed, stale, or inconsistent packaged resource fails closed for
recognition or the relevant Enmity output while leaving intake, review, and
save/open usable. JSON formula strings are never evaluated, and `jsonschema`
is not a production dependency.

## Manual isolated Enmity contract

The persisted inputs are bounded decimal text for final Uncapped Fire
Resistance `U`, Maximum Fire Resistance `M`, and optional isolated target `T`;
equipped state; explicitly recorded equipment-inclusion state; six authored
measurement-context fields; target-version acknowledgement; and an optional
typed observed-item locator. Maximum Fire Resistance has no default. Context,
ownership, inclusion, equipped state, and target version are never inferred.

One shared parser accepts exactly `^-?[0-9]+(?:\.[0-9]+)?$`, permits at most
128 digits, constructs `decimal.Decimal` only after the bound, and preserves
the accepted lexeme. It rejects whitespace, plus signs, exponent notation,
incomplete decimals, non-ASCII digits, NaN, and Infinity. Observed negative or
out-of-range inputs remain unclamped. Fractional U or M is preserved but
returns `rounding-evidence-required`; fractional T affects only target
comparison and cannot withdraw an eligible contribution.

The canonical result precedence is invalid persisted structure; not-equipped;
unknown equipped state; evidence/contract/policy/acknowledged-version failure;
missing U or M; incomplete context or unrecorded inclusion; fractional U or M;
then formula evaluation. Only explicit `confirmed-3.29.1` authorizes the
contract target `Path of Exile 1 3.29.1`.

For eligible integral inputs the sole canonical domain implementation converts
admitted integral Decimal values to Python integers before arithmetic:

```text
u = int(U)
m = int(M)
O = max(0, u - m)
P_enmity = min(200, O)
inputBeyondCap = max(0, O - 200)
```

Integral subtraction does not run under the process-global Decimal context, so
30-digit and 128-digit inputs remain exact regardless of Decimal precision.
Fractional U or M still preserve lexemes, return `rounding-evidence-required`,
and produce no numeric contribution. It returns overcap, `Enmity’s own Fire
Penetration contribution`, the item-specific cap 200, and input beyond that
cap. Available zero is a computed number; unavailable, missing, manually
required, rounding-evidence-required, version-mismatched, and not-applicable
states have null values.

For integral target `T`, a value below zero is `invalid-target`, a value above
200 is `unreachable-by-Enmity`, and a value in 0 through 200 reports
`gap=max(0,T-P_enmity)`, `surplus=max(0,P_enmity-T)`, and
`capHeadroom=max(0,200-P_enmity)`. These comparisons are explicitly isolated
to Enmity's contribution and do not describe aggregate penetration or an
enemy.

## Build-state v2 and migration

`build-state-v2.schema.json` retains every BUILD-001 field and uses document
type `golden-glory-lab-build-state`, schema/application contract `2.0.0`, and
importer contract `1.0.0`. It persists only copied entries and the authored
Enmity inputs/locator in addition to v1. Recognition, review projections,
gate decisions, results, comparisons, file/session/migration/UI state, runtime
versions, and generated timestamps are derived or transient.

Opening v1 performs bounded read, strict v1 decode/validation, in-memory
migration, complete v2 validation, deterministic v2 serialization, and only
then session replacement. It preserves import bytes/digest, mappings, manual
equipment, and notes; initializes copied/Enmity state; writes nothing; reports
upgrade pending; and triggers ordinary unsaved-close protection. Failed open
preserves the complete prior session. Only explicit successful atomic save
writes v2 and clears migration pending. Future versions and dangling observed-
item locators are rejected transactionally.

The v2 consumer boundary enforces strict UTF-8 for every BUILD-002 review-
consumed string, including copied/manual identifiers and raw text, imported
occurrence IDs, source paths, item text, warnings, assignment paths, and present
original-slot values. Lone-surrogate mutations become stable `BuildStateError`
before session replacement. Deep-copy recursion in migration, decode, open, and
pre-commit presentation validation becomes stable nesting `BuildStateError`
codes rather than escaped `RecursionError`. Before session replacement, open
preflights common review derivation, source-locator resolution, and Enmity
evaluation with the current runtime resource state; unavailable runtime
evidence fails closed only for dependent outputs.

The saved-state limit is 682,649,696 bytes. It preserves BUILD-001's derived
597,251,456-byte envelope, then adds all maximum copied canonical strings and
all maximum Enmity-authored strings at the existing conservative 12 JSON bytes
per Python character. The added character envelope includes 64 sets of entry
ID/raw/role/slot/label/note plus three 130-character decimal lexemes, the
longest enums, six 10,000-character context fields, and the longest typed
locator. Fixed v2 keys fit the retained 1 MiB fixed-contract allowance. Pre-
read `stat`, limit-plus-one read, and growth checks remain enforced.

## Automated and packaged validation

The focused runtime manifest validator, Draft 2020-12 schema validator,
fixture generator, common-review/recognizer/domain/state/UI tests, and package
self-test cover the acceptance boundary and negative mutations. The package
self-test imports the permanent PoB fixture, makes explicit mappings, adds a
synthetic copied Enmity item, proves raw/provenance/identity behavior without
inference, validates gates, calculates U=300/M=75 as O=225,
P_enmity=200/inputBeyondCap=25, saves/reopens v2 deterministically, and keeps
all prohibited outputs unavailable.

The complete final gate passed with:

- 149 Python unit tests;
- isolated Ruff `0.15.22` with no findings and a complete `compileall` pass;
- 27 repository JSON documents plus Markdown links and agent-guide references;
- 10 evidence artifacts, 22 semantic mutations, and 12 schema mutations;
- six self-checked BUILD-002 schemas, four v1-to-v2 migrations, two v2
  fixtures, and three schema-negative mutations;
- byte-identical dry-run regeneration of all six build-state fixtures;
- runtime manifest status `PASS` with four claims, two outputs, and five
  pinned source artifacts on both fresh `core.autocrlf=false` and
  `core.autocrlf=true` checkouts;
- passing isolated PoB-import and desktop-packaging proofs.

The final isolated package runner built
`golden_glory_lab-0.2.0-py3-none-any.whl` with SHA-256
`5b9de1c544523875437343640f4cdf9918bc73cd131148db2a59fe7d9c8155db`.
The retained walkthrough bundle contained 992 files and 27,961,556 bytes;
its executable SHA-256 was
`bdc2b4c68af02a2f2f1ee70a26b155c482306a49f15e3d3d02a0a3682a37facf`
and complete tree SHA-256 was
`4b040f4cc6ca7f2df762ba3516b72987c10c58c79923110960030ce37e0d027f`.
It used Windows GUI subsystem 2, included the four required fixtures/runtime
resources, and had no production `Requires-Dist` entries or source network-
client imports.

Three packaged self-tests passed with byte-identical output SHA-256
`ff2df31a5c7f4b3a4715479f2e07d93136f8eae3caed21792eb71656ae7add71`.
Each exercised ten common-review items (eight PoB, one copied, one manual),
explicit role mapping, exact copied-text preservation, Enmity identity without
owner/equipped inference, U=300/M=75 overcap 225, contribution 200, input
beyond cap 25, deterministic v2 save/reopen, runtime evidence gates, and all
seven prohibited output groups remaining unavailable. No generated package or
binary is tracked, uploaded, attached, or released.

## Manual Windows walkthrough

The Windows walkthrough used an isolated one-directory package and unobstructed
window captures. The final packaged window was inspected at 1236 by 859, and
the source UI regression additionally exercised the supported 980 by 700
minimum. The eight main tabs remain distinct (`Mapping`, `PoB review`,
`Common review`, `Copied`, `Manual gear`, `Enmity`, `Evidence`, and `Notes`).
The Enmity page now uses compact `Numbers`, `States`, and `Context` sub-tabs;
every visible entry/combobox is at least 120 pixels wide, the Apply control is
above the output boundary, and the result is at least 400 by 180 pixels. This
guard specifically prevents the overlap and clipping found during manual use.

The native Windows clipboard path was manually exercised with a 334-character
synthetic CRLF item after its final implementation. Review preserved the exact
raw string, reported `observedLineEndings` as `["\r\n"]` and
`retainedRawTextChanged` as `false`, retained explicit Mercenary/`Ring 1`
metadata and the authored label/note, recognized Enmity identity only, and did
not infer owner or equipped state. The final revision also carries a native
`CF_UNICODETEXT` integration regression for that exact CRLF boundary.

In the final package, explicit U=300, M=75, target=200, equipped/included/
confirmed-3.29.1 states, and all six measurement-context fields produced
`AVAILABLE NUMERIC VALUE: 200`. A fractional U produced unavailable/null
rather than rounding, and explicit not-equipped produced unavailable/null
rather than zero. Restoring the valid case returned 200. Saving persisted the
exact `"300"`, `"75"`, and `"200"` lexemes and explicit enum/context values;
opening that v2 file again immediately reconstructed the same 200 result.

A v1 fixture was also opened through the packaged UI as upgrade-pending and
dirty without an implicit write; explicit save/reopen produced v2. The common
review and evidence views were inspected for provenance/role/recognition,
structured gate references, unchanged blocked outputs, and the absence of
ownership/equipped inference. Temporary validation packages and walkthrough
state are not product artifacts.

## Limitations and next Phase 3 slice

This remains a Windows-first Tkinter/ttk one-directory package, not an
installer, signed release, or release-ready artifact. Python-free clean-machine
execution and enforced outbound denial remain unproven. PROOF-002's ordinary-
user DPI, accessibility, broader multi-monitor, firewall/VM, and egress
limitations remain unchanged.

Phase 3 remains in progress. OQ-002 through OQ-006 remain open, so derived
Mercenary inputs, component addition, penalty reconstruction, aggregate
penetration, Light Radius, Golden Glory, and Flame Link are still blocked. The
next Phase 3 slice should resolve a separately audited exact mechanics/source
boundary and then enable only its smallest evidence-gated user result; it must
not widen copied-item semantics or begin completeness recommendations.
