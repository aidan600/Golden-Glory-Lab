# PoB Fixtures

These minimal, permissioned fixtures test enumeration, mapping candidates,
sockets, preservation, unknown content, and reviewable reimport behavior. They
are importer fixtures, never mechanics or general-reference authority. Item-set
order is not ownership.

`proof/` contains permanent synthetic inputs for the reusable importer proof:

- `comprehensive.xml`, `duplicates-and-malformed.xml`, `legacy.xml`, and
  `transitional.xml` cover the AUD-001 occurrence and provenance matrix;
- `equivalent.xml` and `equivalent.share.txt` cover raw/share equivalence;
- `text-fidelity.xml` covers XML normalization boundaries;
- `active-set-states.xml` covers absent, malformed, unresolved, ambiguous, and
  resolved active-set states, including ordinary numeric zero;
- `reference-paths.xml` distinguishes audited Socket/Gem paths and per-context
  zero behavior from retained off-path lookalikes;
- `preservation-events.xml` covers adjacent CDATA and ordered document-level
  comments and processing instructions;
- reordered `reimport-before.xml` and `reimport-after.xml` expose changed order,
  titles, IDs, raw text, and comparison evidence without performing a merge.

`golden/comprehensive.raw.neutral-v1.json` is deterministic contract output:
87,288 bytes, SHA-256
`a1dc0f9fd312b82ab05307e1112906525fa75fab0e8f3c06265094f804da0429`.
