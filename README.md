# Golden Glory Lab

Golden Glory Lab is a planned offline desktop loadout-audit and
improvement-planning tool for a Path of Exile Luminary and one active permanent
Mercenary. This repository currently contains the durable workflow,
documentation, data-boundary, and evidence policy for that project; it does not
yet contain application code.

Start with [the documentation index](docs/INDEX.md) and
[the repository agent guide](AGENTS.md). The current product direction is
recorded in [docs/PRODUCT_DIRECTION.md](docs/PRODUCT_DIRECTION.md); unresolved
work is tracked in [docs/OPEN_QUESTIONS.md](docs/OPEN_QUESTIONS.md).

## Repository map

- docs/ holds current operating documents, audit and decision records, and
  clearly separated historical reference material.
- data/ holds the source registry plus future curated, generated, and schema
  data.
- fixtures/ holds build-instance and synthetic test material, never general
  reference authority.
- scripts/ holds small, documented extraction and validation tools.
- .cursor/ contains a scoped project rule and a reusable audit-start command.

Run the repository checks with:

    node scripts/validate/check_repository.mjs

The check parses every JSON file, validates the source registry against its
repository schema, checks repository-relative Markdown links, and confirms the
files referenced from AGENTS.md exist.
