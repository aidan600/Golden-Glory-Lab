# Fixtures

Fixtures are synthetic test material or permissioned build-instance material:
PoB exports, copied items, screenshots, manual-field transcriptions, and
mechanics test cases. They prove importer or calculator handling for their
specific cases, not general game rules.

Do not treat any fixture as reference catalog data. Keep private, changing, or
unpermissioned player information out of this repository.

PROOF-002 includes `pob/proof/comprehensive.xml` and its retained golden in
the temporary PyInstaller artifact through explicit data-resource arguments.
They are not duplicated in repository source, and packaged execution does not
promote either file into reference authority.
`fixtures/build_state/` contains deterministic synthetic empty, imported,
mapped, and manual BUILD-001 documents. Regenerate them with
`scripts/generate_build_state_fixtures.py --write`, review the reported
added/removed/changed/review sets, and rerun without `--write` to prove the
committed bytes are current. They are build-instance fixtures, never reference
authority.

BUILD-002 adds deterministic v2 empty-migration and copied-Enmity build-state
fixtures in `fixtures/build_state/`. The same generator validates/regenerates
both retained v1 and current v2 documents; v1 bytes remain unchanged.

`fixtures/item_review/copied-items-v1.json` is a small synthetic copied-text
matrix covering recognizable Enmity, generic/partial/malformed/localized/
ambiguous structures, exact LF/CRLF and boundary preservation, reviewed-range
differences, and accepted/rejected limits. These cases establish recognizer
behavior only; they are not reference data or evidence of general game rules.
