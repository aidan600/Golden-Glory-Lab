# Scripts

This directory contains reproducible extraction and validation tools. Scripts
must state their inputs, outputs, network use, and verification limits. Runtime
application code remains offline; research scripts may use public sources under
[the source policy](../docs/SOURCE_POLICY.md).

Run baseline repository validation with:

    node scripts/validate/check_repository.mjs


Run the first-release evidence-integrity gate with:

    node scripts/validate/check_first_release_evidence_pack.mjs

It invokes the isolated, pinned Draft 2020-12 validator for all ten evidence
artifacts, then verifies selected-artifact completeness, source-manifest containment,
claim inventory polarity, separate adopted-policy prerequisites, ordinal capability thresholds and ranks, corrected Enmity locators, canonical source/fixture facts, and real semantic/schema negative mutations. Use `--audit AUD-002` through `AUD-005` for a
focused audit check; schema validation still covers the full pack. It has no runtime
network access, aside from provisioning the existing pinned test-only package set in a
temporary directory.
Run the complete reusable PoB importer proof with:

    py scripts/validate/run_pob_import_proof.py

The proof gate reports Python, zlib, and Expat versions; compiles the Python
sources; builds and installs the wheel into an isolated target; imports the
installed production package; installs every exact proof-only validator pin
from `requirements/pob-import-proof.txt` into a separate isolated target with
`--no-deps`; runs the full suite; validates repository JSON, the source
registry, links, and agent references; and runs `git diff --check`.

Production smoke and proof dependency/test processes use `python -I -S`. Their
bootstrap paths contain only the isolated production install or repository
source, the isolated proof-dependency target, the test directory, and the
interpreter standard library. The runner removes `PYTHONPATH`, rejects a
current-working-directory path or any ambient `site-packages`/`dist-packages`
path, and verifies every proof package's exact version and module location. On
Python below 3.13 it also hides `typing_extensions` temporarily and proves the
same isolated dependency check fails without that conditional pin.

Run the complete Windows desktop packaging proof with:

    py scripts/validate/run_desktop_packaging_proof.py

The Windows-only runner creates a fresh temporary build environment, builds and
installs the current wheel, installs every exact pin in
`requirements/desktop-packaging-proof.txt`, and freezes the console probe with
PyInstaller's explicit fixture/golden data inputs. It parses the build analysis
to reject a `src/` importer, creates and copies a ZIP/one-directory
distributable, sanitizes Python environment variables, runs the executable at
least three times outside the repository, and independently checks the full
golden, precise runtime-security-free projection, packaged runtime admission,
resource hashes, source-network boundary, and deterministic summaries. Build
provisioning may use the network; the packaged probe has no networking
behavior. Windows Sandbox/VM and enforced-egress absence are reported rather
than inferred. All temporary binaries and environments are removed.


Regenerate deterministic golden output with:

    py scripts/generate_pob_import_goldens.py

The generator reads only permanent synthetic fixtures, performs no network
access, and reports output bytes and SHA-256. After intentional regeneration,
review the changed artifact and rerun the generator followed by
`git diff --exit-code -- fixtures/pob/golden/comprehensive.raw.neutral-v1.json`
to prove a clean second regeneration.
Run the BUILD-002 focused Windows package gate with:

    py scripts/validate/run_desktop_build.py

The runner creates a fresh virtual environment, installs the exact packaging
pins, builds and installs the current wheel, verifies a real build-interpreter
Tk root, freezes the installed launcher as a PyInstaller one-directory Windows
GUI application, and rejects repository-source module origins. It verifies the
GUI subsystem, `_tkinter`, Tcl/Tk scripts, bundled permanent/copied fixtures,
packaged runtime Enmity reference and gate manifest, production metadata, and
source networking imports. It copies the package outside the repository, runs
the 17-step BUILD-002 self-test at least three times from an empty directory
with a sanitized environment, compares deterministic output bytes, reports
hashes/inventory/runtime versions, and removes disposable build material. Use
`--copy-output` only with a nonexistent path outside the repository when a
validated bundle is needed for manual inspection.

Build the ordinary-user one-file calculator executable with:

    py -3.13 scripts/build_calculator_exe.py --output "$env:USERPROFILE\Desktop\GoldenGloryCalculator.exe"

The builder uses the same pinned packaging environment, freezes a windowed
one-file `GoldenGloryCalculator.exe`, bundles the Flame Link level table, and
prints path, size, SHA-256, and source git SHA. It refuses to overwrite an
existing output unless `--overwrite` is supplied. Do not commit the executable.

Build both public release artifacts (portable EXE and Windows Setup EXE) with
one command:

    powershell -File scripts/build_release.ps1

This verifies a clean git working tree, records the source git SHA, builds
the portable executable above, launches it briefly as a smoke check, then
compiles `installer/GoldenGloryCalculator.iss` with Inno Setup (`ISCC.exe`)
into `GoldenGloryCalculator-Setup.exe`. It fails clearly, without downloading
anything, if Inno Setup is not installed; see
[docs/INSTALL.md](../docs/INSTALL.md). Both artifacts are written to the
git-ignored `release/` directory and are never committed.

Validate the exact tracked-source/runtime evidence manifest contract with:

    py scripts/validate/run_runtime_evidence_manifest.py

The validator hashes tracked bytes, checks the current AUD-002/AUD-005 claim
inventories and machine-readable artifacts, loads the packaged-form manifest
and reference through their typed loaders, and exercises gate/status/polarity/
policy/source mutations. It performs no network access.

Run BUILD-002 Draft 2020-12 schema self-checks, v1/v2 fixtures and migrations,
typed resource validation, and negative parity mutations with:

    py scripts/validate/run_build002_schema_validation.py

Run BUILD-003 Draft 2020-12 schema self-checks, v1/v2/v3 fixtures and
migrations, Flame Link table load, and negative parity mutations with:

    py scripts/validate/run_build003_schema_validation.py

Regenerate and compare the deterministic BUILD-001/v2/v3 state fixtures with:

    py scripts/generate_build_state_fixtures.py
    py scripts/generate_build_state_fixtures.py --write

The generator has no network behavior. It reports added, removed, changed, and
human-review records; `--write` is required for intentional updates.

Run the exact isolated BUILD-002 Ruff gate with:

    py scripts/validate/run_build_quality.py

That runner creates a disposable virtual environment, installs only the exact
`requirements/build-quality.txt` pin with `--no-deps`, verifies the executable
version and location, runs the repository-local `pyproject.toml` rule set with
no cache, and removes the environment. Do not substitute an ambient Ruff.
