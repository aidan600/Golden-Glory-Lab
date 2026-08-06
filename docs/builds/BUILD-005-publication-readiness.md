# BUILD-005 - Golden Glory Calculator v0.1.0 publication readiness

Mode: BUILD

Date: 2026-08-06

Status: implemented (pending merge)

## Outcome

The manual Golden Glory Calculator delivered by
[BUILD-004](BUILD-004-manual-calculator-reset.md) is now ready for its first
public release. This build does not change the accepted two-page UI, the
calculation domain, or the icon set. It makes the repository and the built
application understandable and installable by a stranger who has never seen
the project before:

- [README.md](../../README.md) is rewritten product-first: what the
  calculator does, how to download and install it, a walkthrough of both
  tabs, calculation notes/limitations, and informational external references.
  It no longer leads with repository architecture.
- [docs/INSTALL.md](../INSTALL.md) covers Setup EXE installation, portable EXE
  use, uninstall, the SmartScreen note, and the developer build path.
- [docs/RELEASE_CHECKLIST.md](../RELEASE_CHECKLIST.md) is the short, concrete
  checklist the owner follows to cut GitHub Release v0.1.0. This build does
  not publish that release.
- `docs/images/calculator.png` and `docs/images/light-radius-breakdown.png`
  are clean, synthetic-data screenshots of the current accepted UI, embedded
  in the README.
- A real Windows installer (`installer/GoldenGloryCalculator.iss`, Inno Setup
  7.0.2) packages the already-built portable EXE into
  `GoldenGloryCalculator-Setup.exe`.
- `scripts/build_release.ps1` is the single-command release builder: clean
  working tree check, git SHA, portable EXE build, a launch smoke check,
  Inno Setup compilation, and SHA-256 for both artifacts. It fails clearly if
  Inno Setup is not installed rather than downloading anything silently.

Neither artifact is committed. Both are written to the git-ignored `release/`
directory.

## Product name and version

User-facing product name: **Golden Glory Calculator** (already the window
title and installer display name). First public release version: **0.1.0**.
No disruptive internal package rename was made; `pyproject.toml`'s
`golden-glory-lab` package version is independent of the product release
version.

## What did not change

- The two-page UI (Calculator, Light Radius Breakdown), its layout, spacing,
  icons, fixed non-resizable window, and manual-first workflow.
- The Flame Link and Enmity calculation domain, including the BUILD-004
  PoB-modelled fractional Fire Resistance truncation.
- The experimental diagnostic desktop shell, PoB import, build mapping,
  evidence/provenance UI, and save/open. They remain in the repository as
  internal/experimental infrastructure, unchanged, and are not part of the
  ordinary product.

## Validation

- Focused calculator tests and the full unit test suite (see PR description
  for exact counts).
- Repository validation (`node scripts/validate/check_repository.mjs`).
- `git diff --check`.
- Built `GoldenGloryCalculator.exe` and `GoldenGloryCalculator-Setup.exe` via
  `scripts/build_release.ps1`.
- Installed via the Setup EXE, launched from the Start Menu, exercised both
  tabs, then uninstalled and confirmed removal.
- Launched the portable EXE directly and confirmed it opens outside the
  repository.

See the publication pull request for exact commands, output, and hashes.

## Related

- [CURRENT_STATE.md](../CURRENT_STATE.md)
- [BUILD-004](BUILD-004-manual-calculator-reset.md)
- [docs/INSTALL.md](../INSTALL.md)
- [docs/RELEASE_CHECKLIST.md](../RELEASE_CHECKLIST.md)
