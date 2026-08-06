# Installing and Building Golden Glory Calculator

The [README](../README.md) has enough instructions for an ordinary user to
download, install, and run the application. This document adds detail for
users who want more control, and for developers who want to build the
executables from source.

## For users

### Setup EXE installation

1. Download `GoldenGloryCalculator-Setup.exe` from the
   [latest GitHub Release](https://github.com/aidan600/Golden-Glory-Lab/releases/latest).
2. Run it. It installs per-user (no administrator prompt in the normal case),
   creates a Start Menu shortcut, and offers an optional desktop shortcut.
3. Launch **Golden Glory Calculator** from the Start Menu.

The installer does not add a startup task, register a file association,
modify your `PATH`, install a background service, or access the network.

### Portable EXE usage

Download `GoldenGloryCalculator.exe` from the same release and run it
directly. Nothing is installed; you can move or delete the file at any time.

### Uninstalling

If you used the Setup EXE, uninstall the normal Windows way: **Settings ->
Apps -> Installed apps -> Golden Glory Calculator -> Uninstall**, or via
**Add or Remove Programs**. This removes the installed files and the Start
Menu / desktop shortcuts.

If you used the portable EXE, just delete the file.

### SmartScreen warning

Both executables are currently unsigned. Windows SmartScreen may show
"Windows protected your PC" the first time you run either one. Select
**More info**, then **Run anyway**, if you trust the download. Code signing
is not part of this release.

## For developers

### Requirements

- Windows 10 or later
- Python 3.13 (the packaging pins in `requirements/desktop-packaging-proof.txt`
  target this version)
- [Inno Setup](https://jrsoftware.org/isinfo.php) 7.0.2, only if you want to
  build the Setup EXE

### Building the portable EXE only

    py -3.13 scripts/build_calculator_exe.py --output "$env:USERPROFILE\Desktop\GoldenGloryCalculator.exe"

This creates a disposable virtual environment, installs the pinned packaging
dependencies, builds a one-file, windowed PyInstaller executable, bundles the
Flame Link level table and slot/jewel icons, and prints the output path,
file size, SHA-256, and source git SHA. It refuses to overwrite an existing
output file unless `--overwrite` is supplied. The executable is never
committed to the repository.

### Installing Inno Setup

Download and install Inno Setup 7.0.2 from <https://jrsoftware.org/>, or, if
you use `winget`:

    winget install --id JRSoftware.InnoSetup.7 --version 7.0.2

This installs `ISCC.exe` (the Inno Setup command-line compiler), typically at
`%LOCALAPPDATA%\Programs\Inno Setup 7\ISCC.exe`.

### Building both release artifacts

    powershell -File scripts/build_release.ps1

This single command:

1. verifies the git working tree is clean (pass `-SkipCleanCheck` to bypass
   during local iteration);
2. records the current git SHA;
3. builds `GoldenGloryCalculator.exe` (the portable one-file build);
4. launches it briefly as a smoke check to confirm it starts without
   crashing, then closes it;
5. locates `ISCC.exe` and fails clearly, with a link to
   <https://jrsoftware.org/>, if Inno Setup is not installed;
6. compiles `installer/GoldenGloryCalculator.iss` into
   `GoldenGloryCalculator-Setup.exe`;
7. prints the path, size, and SHA-256 of both artifacts.

Both artifacts are written to the ignored `release/` directory at the
repository root; neither is committed.

### Verification / hash commands

    Get-FileHash release\GoldenGloryCalculator.exe -Algorithm SHA256
    Get-FileHash release\GoldenGloryCalculator-Setup.exe -Algorithm SHA256

Compare the printed hash against the one recorded for the release you are
verifying.

### Where outputs are placed

    release/GoldenGloryCalculator.exe
    release/GoldenGloryCalculator-Setup.exe

Both are ignored by `.gitignore` and are only ever attached to a GitHub
Release manually by the project owner; see
[docs/RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md).
