# Scripts

This directory contains reproducible extraction and validation tools. Scripts
must state their inputs, outputs, network use, and verification limits. Runtime
application code remains offline; research scripts may use public sources under
[the source policy](../docs/SOURCE_POLICY.md).

Run baseline repository validation with:

    node scripts/validate/check_repository.mjs

Run the complete reusable PoB importer proof with:

    py scripts/validate/run_pob_import_proof.py

The proof gate reports Python, zlib, and Expat versions; compiles the Python
sources; builds and installs the wheel into an isolated target; imports the
installed production package; installs every exact proof-only validator pin
from `requirements/pob-import-proof.txt` into a separate isolated target with
`--no-deps`; runs the full suite; validates repository JSON, the source
registry, links, and agent references; and runs `git diff --check`.

Regenerate deterministic golden output with:

    py scripts/generate_pob_import_goldens.py

The generator reads only permanent synthetic fixtures, performs no network
access, and reports output bytes and SHA-256. After intentional regeneration,
review the changed artifact and rerun the generator followed by
`git diff --exit-code -- fixtures/pob/golden/comprehensive.raw.neutral-v1.json`
to prove a clean second regeneration.
