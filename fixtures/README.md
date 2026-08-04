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