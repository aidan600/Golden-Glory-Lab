# PROOF-002 - Windows desktop packaging

## Status

Result: **PASS WITH LIMITATIONS**

Adoption recommendation: **ADOPT WITH NAMED LIMITATIONS**

Tested on 2026-08-03 on Windows 11 x64 with PyInstaller 6.21.0,
Python 3.13.14, Expat 2.8.1, and zlib 1.3.1. Two clean isolated builds
each ran the copied package three times.

## Question

Can a Windows-first offline package contain the adopted
`golden_glory_lab.pob_import` implementation, invoke its public
`importPobRawXml` seam against the permanent synthetic fixture inside the
artifact, and preserve the deterministic neutral contract without a source
checkout, ambient site-packages, or an externally configured Python runtime?

## Evidence dependency

This proof consumes [PROOF-001](PROOF-001-pob-importer.md) without changing
its importer, contract, fixture, golden, security admission boundary, or named
limitations.

Material packaging sources are registered in the
[source registry](../../data/sources/registry.json):

- `pyinstaller-6-21-0-metadata`, `pyinstaller-6-21-0-usage`, and
  `pyinstaller-6-21-0-license`;
- `nuitka-4-1-3-standalone` and
  `nuitka-4-1-3-runtime-license`;
- `tauri-2-sidecar-docs` and `tauri-dev-license`;
- the exact PyInstaller dependency records; and
- the existing Python, Expat, zlib, and setuptools records retained by
  PROOF-001.

The permanent fixture remains synthetic proof material. Neither it nor the
retained golden is mechanics or reference-catalog authority.

## Candidate criteria and bounded comparison

Only three candidates were assessed. No alternate implementation was left in
the repository.

| Criterion | PyInstaller 6.21.0 | Nuitka 4.1.3 | Tauri 2 plus Python sidecar |
| --- | --- | --- | --- |
| Direct adopted-importer reuse | Direct import from an installed wheel. | Direct import from an installed wheel. | Requires a separately packaged Python executable and process bridge. |
| Windows-first offline package | One-directory or one-file bundle includes CPython. | Standalone or one-file output includes the runtime. | Native shell can be offline, but the Python sidecar and WebView/runtime posture remain separate packaging concerns. |
| Bundled resources | Explicit `--add-data` mechanism and run-time `__file__` locator. | Explicit standalone data inclusion. | External-binary and shell resource configuration. |
| Future small desktop app | Python UI can be selected later without changing the importer seam. | Python UI can be compiled later. | Rich web UI shell, but it establishes Rust/web/process boundaries before they are needed. |
| Build complexity and maintenance | Mature analysis/freezing step; no C compiler required for the selected wheel. | Native compilation, compiler/toolchain selection, and longer diagnostic loop. | Rust, web frontend, WebView, sidecar packaging, and IPC lifecycle. |
| Runtime and package size | Small console proof: 60 files and 19,833,693 uncompressed bytes. | Expected native standalone output; not built because the extra toolchain did not answer an additional proof question. | Adds the native/web shell to the still-required Python package. |
| Licensing posture | GPL-2.0-or-later build tool with bootloader exception; Apache-2.0 runtime hooks. | AGPL-3.0 build tool with a runtime distribution exception. | MIT/Apache-2.0 shell plus every Python-sidecar obligation. |
| Reproducibility and validation | Exact pins, structured TOC, explicit resources, automated copied-bundle runs. | Reproducible pins are possible but compiler inputs broaden the matrix. | Reproducibility spans Rust/web/sidecar toolchains and the bridge. |
| Source/ambient isolation | TOC exposes collected module origins; frozen paths are observable. | Standalone origins can be audited. | Sidecar can be isolated, but the shell-to-sidecar boundary is an additional admission surface. |
| Semantic boundary | No new boundary: the probe calls the public Python function in-process. | No new boundary: the probe calls the public Python function in-process. | Adds request/response serialization and process failure semantics. |

## Selected approach

**PyInstaller 6.21.0, console, one-directory mode** was selected.

It answered the proof through the smallest production-credible path: the
runner built the current project wheel, installed it into a new environment,
and PyInstaller collected `golden_glory_lab.pob_import` from that installed
wheel. The public function remained an in-process Python call. The proof did
not select a UI toolkit, installer technology, update mechanism, or final
one-file versus one-directory release format.

Nuitka was discarded before implementation because its native compiler
toolchain and licensing/maintenance surface did not establish an additional
fact for this dependency-free importer. Tauri was discarded because its own
documentation treats packaged Python as a sidecar, so it would preserve the
Python packager while adding a second process and semantic boundary.

## Dependency and licensing record

All Python packaging dependencies are exact pins in
[`requirements/desktop-packaging-proof.txt`](../../requirements/desktop-packaging-proof.txt).

| Dependency | Purpose | License record | In packaged artifact | Production runtime dependency |
| --- | --- | --- | --- | --- |
| PyInstaller 6.21.0 | Analyze and freeze the probe and installed wheel. | GPL-2.0-or-later with bootloader exception; core run-time hooks are Apache-2.0. | Bootloader and one core run-time hook are retained. | Packaging approach/runtime shell, not imported application metadata. |
| altgraph 0.17.5 | Build-time module graph. | MIT. | No. | No. |
| packaging 26.2 | Build-time version/metadata utilities. | Apache-2.0 OR BSD-2-Clause. | No. | No. |
| pefile 2024.8.26 | Windows PE inspection and modification. | MIT. | No. | No. |
| pyinstaller-hooks-contrib 2026.6 | Exact PyInstaller hook dependency. | GPL-2.0-or-later standard hooks; Apache-2.0 run-time hooks. | No contrib run-time hook was retained by this analysis. | No. |
| pywin32-ctypes 0.2.3 | Windows resource handling during build. | BSD-3-Clause. | No. | No. |
| setuptools 75.8.2 | Existing wheel backend and PyInstaller requirement. | MIT. | No. | No. |
| CPython 3.13.14 | Frozen interpreter and standard library. | PSF-2.0 and incorporated-software notices. | Yes. | Yes for this shell. |
| Expat 2.8.1 | Adopted XML parser runtime. | Expat license through Python notices. | Yes, including `pyexpat`. | Yes. |
| zlib 1.3.1 | Share-code/standard-library runtime. | zlib license through Python notices. | Yes. | Yes. |

This is a technical risk and provenance record, not legal advice. A
distributed BUILD must include the applicable Python, Expat, zlib, Microsoft
runtime, and other third-party notices. This proof published no artifact. Its
executable is unsigned; code signing, SmartScreen reputation, installer
licenses, and production notice assembly remain release-hardening work.

## Build design

[`run_desktop_packaging_proof.py`](../../scripts/validate/run_desktop_packaging_proof.py)
performs these stages with argument arrays:

1. create a fresh temporary virtual environment outside the repository;
2. build the current project wheel through its exact setuptools backend;
3. install that wheel with `--no-deps`;
4. install all exact packaging dependencies with `--no-deps` and run
   `pip check`;
5. run PyInstaller with `-I`, one-directory mode, UPX disabled, and two
   explicit `--add-data` inputs;
6. parse `Analysis-00.toc` to prove the importer originated under the
   temporary environment's `site-packages`, not `src/`;
7. verify the packaged fixture and golden byte-for-byte;
8. create a ZIP distributable, copy only that ZIP to a separate temporary run
   directory, and extract it there;
9. launch the executable directly from an empty working directory under a
   sanitized environment; and
10. compare the temporary full result, precise stable projection, probe
    summary, runtime facts, and repeated runs before removing every temporary
    output.

The runner performs no runtime download or network request from the packaged
program. Network access is used only by build-time pip provisioning.

## Packaged public seam

[`desktop_packaging_probe.py`](../../proofs/desktop_packaging_probe.py)
imports these names only through the public package interface:

- `CONTRACT_VERSION`;
- `IMPLEMENTATION_VERSION`;
- `importPobRawXml`; and
- `deterministic_json_bytes`.

It contains no PoB XML parsing or semantic projection logic and does not parse
the fixture itself. A fresh empty Expat parser verifies only reparse-deferral
state. The probe does not import from `src/` or insert a repository path into
`sys.path`. The selected invocation is
`importPobRawXml(fixture_text)`.

The observed frozen module locator in the second clean build was:

`C:\tmp\ggl-desktop-packaging-proof-511p5qln\isolated-run\distribution\GoldenGloryLabPackagingProbe\_internal\golden_glory_lab\pob_import\__init__.py`

The observed executable path was:

`C:\tmp\ggl-desktop-packaging-proof-511p5qln\isolated-run\distribution\GoldenGloryLabPackagingProbe\GoldenGloryLabPackagingProbe.exe`

Both temporary paths were removed after validation.

## Fixture and expected result

PyInstaller's explicit data mechanism includes the existing files at these
bundle-relative locations:

- `_internal/ggl_proof_resources/pob/proof/comprehensive.xml`;
- `_internal/ggl_proof_resources/pob/golden/comprehensive.raw.neutral-v1.json`.

The probe locates them relative to its frozen `__file__`, reads both as strict
UTF-8, and fails with a machine-readable code when either is absent.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `comprehensive.xml` | 2,641 | `94d7f233b338455ff186fc109a5a073426c58f68672180ec7b73f3e38e8b8417` |
| Retained full golden | 87,288 | `a1dc0f9fd312b82ab05307e1112906525fa75fab0e8f3c06265094f804da0429` |
| Expected stable projection | derived | `f97ad1fbd3eeda279efc8027000900fdaf4b5023e7736eef07f1eed3d1d1022a` |
| Actual packaged full result | 87,288 | `a1dc0f9fd312b82ab05307e1112906525fa75fab0e8f3c06265094f804da0429` |
| Actual packaged stable projection | derived | `f97ad1fbd3eeda279efc8027000900fdaf4b5023e7736eef07f1eed3d1d1022a` |

Full byte equality passed because packaged and retained
`envelope.runtimeSecurity` objects were identical. The recursively computed
full difference set was empty. The stable projection removes only
`envelope.runtimeSecurity`; no other key, value, array entry, or ordering is
normalized or ignored.

## Runtime isolation

The copied executable ran from `C:\tmp`, outside the repository, with:

- no `PYTHONPATH`, `PYTHONHOME`, or `PYTHONUSERBASE`;
- `PYTHONNOUSERSITE=1`;
- no ambient `site-packages` or `dist-packages` in frozen `sys.path`;
- a minimal Windows `PATH`;
- the repository root passed only as a forbidden path assertion;
- a module locator under the copied bundle; and
- no repository source path in the frozen runtime or PyInstaller importer
  origins.

Windows Sandbox was not installed and no clean Windows VM was available. This
is strong local process and filesystem isolation, not a Python-free
clean-machine test.

No OS firewall, VM, or sandbox egress denial was available. The runner instead
AST-inspected the complete retained probe and production package for networking
imports and found none. The lack of directly enforced outbound denial remains a
named limitation; this proof does not claim egress-isolated execution.

## Runtime versions

| Runtime fact | Packaged observation | Validation |
| --- | --- | --- |
| Python | 3.13.14 | Reported by frozen runtime. |
| Python executable | Copied `GoldenGloryLabPackagingProbe.exe` | Equal to the directly launched path. |
| Expat | `expat_2.8.1` | Independently parsed as `[2, 8, 1]`. |
| Required Expat floor | 2.7.2 | Independently compared. |
| Importer admission | `supported` | Reported object exactly equaled independent observation. |
| Reparse deferral | API/getter available; configured and enabled | Fresh packaged parser set and read back `true`. |
| zlib | 1.3.1 | Independently reported by packaged standard library. |
| Importer contract | 1.0.0 | Public package constant and result match. |
| Importer implementation | `pob-importer-python/0.1.1` | Public package constant and envelope match. |

The current runtime satisfied admission, so the package produced a success.
PROOF-001 retains the deterministic below-floor and unparseable-version failure
tests. This proof did not replace the packaged interpreter with a deliberately
unsafe Expat build.

## Artifact details

The final recorded local artifact was a ZIP containing a PyInstaller
one-directory bundle:

| Detail | Value |
| --- | --- |
| File count | 60 |
| Uncompressed size | 19,833,693 bytes |
| ZIP size | 8,848,135 bytes |
| ZIP SHA-256 | `c46eec321b3f621164e611b2a4ea8e977f095b161b7bea1e777bc5061657c1da` |
| Primary executable size | 2,063,435 bytes |
| Primary executable SHA-256 | `e51573f8acbf5ae99e8a1ed42ffc02996bae5f8701ff4a8a013e553476c8799f` |
| Native `.exe`/`.dll`/`.pyd` file count | 57 |
| Build duration | 7.842 seconds |
| Startup durations | 0.525, 0.117, and 0.114 seconds |
| Copied and run elsewhere | Yes |

The first clean passing build produced a different ZIP and executable hash,
while its file count, uncompressed size, runtime facts, neutral-result hashes,
and three packaged summaries were identical. PyInstaller binary
byte-reproducibility is not claimed or required.

The artifact includes the PyInstaller bootloader, CPython DLL/runtime files,
standard-library/native extension modules, `pyexpat`, and the two explicit
data resources. No generated executable, DLL, ZIP, build environment, spec
file, cache, or staging directory is retained in Git.

## Verification

The following passed:

```powershell
py scripts/validate/run_pob_import_proof.py
py scripts/validate/run_desktop_packaging_proof.py
py scripts/validate/run_desktop_packaging_proof.py
py -m compileall -q proofs/desktop_packaging_probe.py scripts/validate/run_desktop_packaging_proof.py
py -m ruff check proofs/desktop_packaging_probe.py scripts/validate/run_desktop_packaging_proof.py
node scripts/validate/check_first_release_evidence_pack.mjs
node scripts/validate/check_repository.mjs
git diff --check origin/main...HEAD
```

PROOF-001 passed all 42 tests on Python 3.13.14, zlib 1.3.1, and Expat
2.8.1. Each clean packaging-proof execution built a new wheel and distributable
and then performed three copied-package runs. Across the two complete
executions, all six importer result byte streams matched the full golden and
all six proof summaries were byte-identical within their build. Repository JSON,
source registry, schema, and repository-relative link validation passed.

The console-only proof has no UI surface, so manual UI inspection is not
applicable.

## Result

**PASS WITH LIMITATIONS**

The real installed importer was frozen, its existing synthetic fixture and
golden were bundled, the public raw-XML entry point executed successfully, the
full result exactly matched the retained golden, the precise stable projection
matched, and packaged runtime-security facts were independently validated.
Repeated copied-package executions were deterministic.

## Limitations

- No Python-free clean Windows machine, VM, or Windows Sandbox run was
  available.
- Outbound network denial was not directly enforced; source inspection found no
  networking behavior.
- The proof is a console executable and does not choose or validate the BUILD
  UI toolkit.
- The executable is unsigned and is not an installer or release artifact.
- Binary package bytes were not reproducible across clean builds; importer
  results and proof summaries were deterministic.
- A deliberately unsafe packaged Expat interpreter was not constructed; the
  retained PROOF-001 runtime-guard regression remains the failure-path evidence.
- Every named PROOF-001 importer limitation remains in force.

## Non-proofs

This proof does not establish a usable desktop workflow, UI framework,
installer, code signing, updater, clean-machine compatibility, egress
isolation, release readiness, ownership mapping, copied-item parsing,
persistence, item semantics, Path of Exile mechanics, Flame Link, Golden Glory,
Light Radius, Enmity, resistance, penetration, damage, DPS, or a combined
score.

## Dataset impact

No mechanics reference data, curated data, generated game data, or imported
build data changed. The fixture and golden remain synthetic proof artifacts.

## Intended downstream consumer

The intended consumer is the first usable desktop BUILD. It may extend this
packaged Python seam, but explicit player/optional Mercenary mapping,
persistence, UI, and evidence-gated mechanics remain separate application
concerns.

## Retained artifacts

- `proofs/desktop_packaging_probe.py`;
- `scripts/validate/run_desktop_packaging_proof.py`;
- `requirements/desktop-packaging-proof.txt`;
- the existing `src/golden_glory_lab/pob_import/` package;
- the existing `fixtures/pob/proof/comprehensive.xml`;
- the existing retained golden; and
- this proof and its source-registry records.

No generated binary is retained.

## Adoption recommendation

**ADOPT WITH NAMED LIMITATIONS**

Retain PyInstaller 6.21.0 as the proven Windows packaging approach and retain
the installed-wheel, explicit-resource, copied-bundle, runtime-security, and
deterministic-result gates. The final UI toolkit and release distribution
shape remain BUILD/release decisions.

## Next integrated exercise

After human review and merge, the next integrated exercise is the first usable
desktop BUILD. It should consume the same public importer and packaged-resource
seam, add explicit item-set mapping and local state outside imported facts, and
render evidence-gated mechanics as unavailable/review states. This proof does
not start that BUILD.
