# Scripts

This directory contains understandable extraction and validation tools used to
make data and documentation work reproducible. Scripts must describe their
inputs, outputs, network use, and verification limits.

Do not place downloaded executable code here without inspection. Runtime
application code must remain offline; research and data-generation scripts may
use public network sources under [the source policy](../docs/SOURCE_POLICY.md).

Run the baseline repository validation with:

    node scripts/validate/check_repository.mjs
