# Release Checklist

This document is a short, practical checklist for cutting a GitHub Release.
It is not a packaging thesis. See [docs/INSTALL.md](INSTALL.md) for build
detail.

This repository does not publish releases automatically. Publishing remains a
human decision by the project owner.

## Checklist for v0.1.0

- [ ] Merge the publication pull request into `main`.
- [ ] `git checkout main && git pull origin main` on a clean local clone.
- [ ] Run the full test suite: `py -3.13 -m unittest discover -s tests`.
- [ ] Run `powershell -File scripts/build_release.ps1` to build both release artifacts.
- [ ] Manually launch the **installed** version (run the Setup EXE first):
  - [ ] Install via `GoldenGloryCalculator-Setup.exe`.
  - [ ] Launch **Golden Glory Calculator** from the Start Menu.
  - [ ] Exercise the **Calculator** tab: enter values, confirm all four
        results update live.
  - [ ] Exercise the **Light Radius Breakdown** tab: enter slot/jewel values,
        press **Apply Total to Calculator**, confirm the total lands on the
        Calculator tab and switches tabs.
  - [ ] Uninstall via **Settings -> Apps** and confirm the install directory
        and shortcuts are gone.
- [ ] Launch the **portable** `GoldenGloryCalculator.exe` directly (outside
      the repository) and confirm it starts and both tabs work.
- [ ] Record the SHA-256 of both artifacts (printed by
      `scripts/build_release.ps1`).
- [ ] Create tag `v0.1.0` on the merged `main` commit.
- [ ] Create the GitHub Release from that tag.
- [ ] Attach both artifacts:
  - `GoldenGloryCalculator-Setup.exe`
  - `GoldenGloryCalculator.exe`
- [ ] Publish the release notes (see proposed draft below).

## Proposed release title

    Golden Glory Calculator v0.1.0

## Proposed release notes

    First public release of Golden Glory Calculator: a manual-first Windows
    planning calculator for Path of Exile Luminary/Mercenary Golden Glory,
    Flame Link, and Enmity's Embrace setups.

    Download GoldenGloryCalculator-Setup.exe (recommended) or the portable
    GoldenGloryCalculator.exe. No Path of Building import is required, no
    Python installation is required, and the application runs fully offline.

    What it does:
    - Effective Link Skill Buff Effect (Golden Glory, Light Radius, other
      Link Buff Effect, Powerful Bond, Inspiring Bond)
    - Flame Link Added Fire Damage granted to the linked Mercenary (modelled,
      not DPS)
    - Enmity's Embrace Fire Penetration from overcapped Fire Resistance,
      capped at 200%
    - Optional slot-by-slot Light Radius breakdown

    Known limitations:
    - Windows SmartScreen may warn on first run because both binaries are
      unsigned.
    - The Flame Link integer result is modelled and not independently
      confirmed against live-client rounding.
    - Mechanics target is Path of Exile 1 patch 3.29.x.
    - No Path of Building import and no DPS calculation in this release.

Adjust wording only if the owner wants a different tone; keep the content
accurate to what shipped.
