"""Build a Windows executable for the GUI with PyInstaller."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    """Run PyInstaller against the checked-in GUI spec file."""
    if sys.platform != "win32":
        print(
            "This script must be run on Windows to produce a Windows .exe. "
            "Use a Windows PC/VM or the GitHub Actions workflow.",
            file=sys.stderr,
        )
        return 1

    repo_root = Path(__file__).resolve().parents[1]
    spec_file = repo_root / "pdf-transaction-scraper-gui.spec"
    command = [sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm", str(spec_file)]
    return subprocess.call(command, cwd=repo_root)


if __name__ == "__main__":
    raise SystemExit(main())
