"""PyInstaller launcher using only the normal installed-package import."""

from golden_glory_lab.desktop.main import main


if __name__ == "__main__":
    raise SystemExit(main())
