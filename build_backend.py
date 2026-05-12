"""Tiny PEP 517/660 build backend for this pure-Python project.

The project intentionally avoids relying on a globally installed setuptools for
editable installs. Some user environments reported setuptools without the
``build_editable`` hook, so this backend builds a minimal wheel/editable wheel
from the metadata in ``pyproject.toml``.
"""

from __future__ import annotations

import base64
import csv
import hashlib
import io
import os
import re
import tarfile
import tomllib
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parent.resolve()
SRC = ROOT / "src"
PYPROJECT = ROOT / "pyproject.toml"


def _pyproject() -> dict[str, Any]:
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))


def _project() -> dict[str, Any]:
    return _pyproject()["project"]


def _distribution_name() -> str:
    return _project()["name"]


def _normalized_name() -> str:
    return re.sub(r"[-_.]+", "_", _distribution_name()).lower()


def _version() -> str:
    return _project()["version"]


def _dist_info() -> str:
    return f"{_normalized_name()}-{_version()}.dist-info"


def _wheel_name() -> str:
    return f"{_normalized_name()}-{_version()}-py3-none-any.whl"


def _metadata() -> str:
    project = _project()
    lines = [
        "Metadata-Version: 2.3",
        f"Name: {_distribution_name()}",
        f"Version: {_version()}",
        f"Summary: {project.get('description', '')}",
    ]
    requires_python = project.get("requires-python")
    if requires_python:
        lines.append(f"Requires-Python: {requires_python}")
    for author in project.get("authors", []):
        name = author.get("name")
        email = author.get("email")
        if name and email:
            lines.append(f"Author-email: {name} <{email}>")
        elif name:
            lines.append(f"Author: {name}")
    license_data = project.get("license")
    if isinstance(license_data, dict) and license_data.get("text"):
        lines.append(f"License: {license_data['text']}")
    for dependency in project.get("dependencies", []):
        lines.append(f"Requires-Dist: {dependency}")
    for extra, dependencies in project.get("optional-dependencies", {}).items():
        lines.append(f"Provides-Extra: {extra}")
        for dependency in dependencies:
            lines.append(f"Requires-Dist: {dependency}; extra == '{extra}'")
    readme = project.get("readme")
    if readme:
        lines.append("Description-Content-Type: text/markdown")
        description = (ROOT / readme).read_text(encoding="utf-8")
        lines.extend(["", description])
    else:
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _wheel() -> str:
    return "\n".join(
        [
            "Wheel-Version: 1.0",
            "Generator: pdf-transaction-scraper-build-backend",
            "Root-Is-Purelib: true",
            "Tag: py3-none-any",
            "",
        ]
    )


def _entry_points() -> str:
    scripts = _project().get("scripts", {})
    if not scripts:
        return ""
    lines = ["[console_scripts]"]
    for name, target in sorted(scripts.items()):
        lines.append(f"{name} = {target}")
    return "\n".join(lines) + "\n"


def _hash(data: bytes) -> tuple[str, str]:
    digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode("ascii")
    return f"sha256={digest}", str(len(data))


def _write_wheel(path: Path, files: dict[str, bytes]) -> None:
    record_path = f"{_dist_info()}/RECORD"
    rows = []
    for file_path, data in sorted(files.items()):
        digest, size = _hash(data)
        rows.append((file_path, digest, size))
    rows.append((record_path, "", ""))

    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerows(rows)
    files[record_path] = output.getvalue().encode("utf-8")

    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as wheel_file:
        for file_path, data in sorted(files.items()):
            wheel_file.writestr(file_path, data)


def _base_dist_info_files() -> dict[str, bytes]:
    files = {
        f"{_dist_info()}/METADATA": _metadata().encode("utf-8"),
        f"{_dist_info()}/WHEEL": _wheel().encode("utf-8"),
    }
    entry_points = _entry_points()
    if entry_points:
        files[f"{_dist_info()}/entry_points.txt"] = entry_points.encode("utf-8")
    return files


def _package_files() -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    for path in SRC.rglob("*"):
        if path.is_file() and path.suffix in {".py", ".pyi"}:
            files[path.relative_to(SRC).as_posix()] = path.read_bytes()
    return files


def get_requires_for_build_wheel(config_settings: dict[str, Any] | None = None) -> list[str]:
    return []


def get_requires_for_build_editable(config_settings: dict[str, Any] | None = None) -> list[str]:
    return []


def prepare_metadata_for_build_wheel(
    metadata_directory: str,
    config_settings: dict[str, Any] | None = None,
) -> str:
    dist_info = Path(metadata_directory) / _dist_info()
    dist_info.mkdir(parents=True, exist_ok=True)
    for relative_path, data in _base_dist_info_files().items():
        target = Path(metadata_directory) / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return _dist_info()


def prepare_metadata_for_build_editable(
    metadata_directory: str,
    config_settings: dict[str, Any] | None = None,
) -> str:
    return prepare_metadata_for_build_wheel(metadata_directory, config_settings)


def build_wheel(
    wheel_directory: str,
    config_settings: dict[str, Any] | None = None,
    metadata_directory: str | None = None,
) -> str:
    files = _package_files()
    files.update(_base_dist_info_files())
    wheel_path = Path(wheel_directory) / _wheel_name()
    _write_wheel(wheel_path, files)
    return wheel_path.name


def build_editable(
    wheel_directory: str,
    config_settings: dict[str, Any] | None = None,
    metadata_directory: str | None = None,
) -> str:
    files = _base_dist_info_files()
    files[f"{_normalized_name()}.pth"] = (str(SRC) + os.linesep).encode("utf-8")
    wheel_path = Path(wheel_directory) / _wheel_name()
    _write_wheel(wheel_path, files)
    return wheel_path.name


def build_sdist(
    sdist_directory: str,
    config_settings: dict[str, Any] | None = None,
) -> str:
    base_name = f"{_normalized_name()}-{_version()}"
    archive_name = f"{base_name}.tar.gz"
    archive_path = Path(sdist_directory) / archive_name
    include = [
        "pyproject.toml",
        "README.md",
        "LICENSE",
        "build_backend.py",
        "pdf-transaction-scraper-gui.spec",
        "src",
        "scripts",
        "tests",
        ".github",
    ]
    with tarfile.open(archive_path, "w:gz") as tar:
        for item in include:
            path = ROOT / item
            if path.exists():
                tar.add(path, arcname=f"{base_name}/{item}")
    return archive_name
