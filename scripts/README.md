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
claim inventory polarity, gate dependencies, corrected Enmity locators, and synthetic
formula/withheld-output fixtures. Use `--audit AUD-002` through `AUD-005` for a
focused audit check; schema validation still covers the full pack. It has no runtime
network access, aside from provisioning the existing pinned test-only package set in a
temporary directory.
`nRun the complete reusable PoB importer proof with:

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

Regenerate deterministic golden output with:

    py scripts/generate_pob_import_goldens.py

The generator reads only permanent synthetic fixtures, performs no network
access, and reports output bytes and SHA-256. After intentional regeneration,
review the changed artifact and rerun the generator followed by
`git diff --exit-code -- fixtures/pob/golden/comprehensive.raw.neutral-v1.json`
to prove a clean second regeneration.
