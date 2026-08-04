# DEC-001 - Desktop UI toolkit for BUILD-001

## Status

accepted

## Context

BUILD-001 needs a packaged, offline Windows GUI around the adopted Python PoB
importer. The intake, canonical build state, explicit mapping, persistence,
session state, and presentation boundaries must remain testable without adding
a second importer or a second-process protocol.

## Options considered

- Standard-library tkinter and tkinter.ttk in the installed application.
- A third-party Python desktop toolkit.
- A browser or webview shell with a local service or Python sidecar.

## Decision

Use standard-library tkinter and tkinter.ttk for BUILD-001.

The GUI, application service, canonical state codec, and adopted importer run
in one installed Python process. This adds no PyPI production dependency and
no second-process or serialization boundary. PyInstaller 6.21.0 remains the
adopted one-directory Windows packager.

Tcl/Tk is nevertheless a bundled native runtime and licensing component. The
BUILD packaging gate must inspect and report the actual Tcl and Tk versions,
verify _tkinter and the Tcl/Tk resources were collected, and initialize the
copied package's Tk runtime.

## Consequences

- Controller, codec, and intake behavior remain independently unit-testable;
  widgets do not own canonical state or dirty/readiness rules.
- Appearance follows the platform theme and is less customizable than a
  dedicated design system.
- GUI automation and accessibility inspection are comparatively limited.
- Very large or highly interactive future workflows may outgrow this toolkit.
- The decision may be superseded by a later reviewed desktop-architecture
  decision. Switching toolkits is outside BUILD-001.
- If the host Python has no functional Tkinter/Tcl/Tk runtime, or the copied
  PyInstaller package cannot launch it after bounded diagnosis, BUILD-001
  stops rather than silently changing frameworks.

## Evidence or audit dependencies

- [PROOF-001](../proofs/PROOF-001-pob-importer.md) supplies the adopted
  in-process importer seam.
- [PROOF-002](../proofs/PROOF-002-desktop-packaging.md) supplies the adopted
  installed-wheel, copied-bundle PyInstaller approach.
- BUILD-001 records the concrete packaged Tcl/Tk inspection and walkthrough.

## Supersession details

Not superseded.
