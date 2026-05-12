import zipfile

import build_backend


def test_build_backend_exposes_pep660_editable_wheel(tmp_path):
    wheel_name = build_backend.build_editable(str(tmp_path))
    wheel_path = tmp_path / wheel_name

    assert wheel_path.exists()
    with zipfile.ZipFile(wheel_path) as wheel_file:
        names = set(wheel_file.namelist())

    assert "pdf_transaction_scraper.pth" in names
    assert "pdf_transaction_scraper-0.1.0.dist-info/METADATA" in names
    assert "pdf_transaction_scraper-0.1.0.dist-info/entry_points.txt" in names


def test_build_backend_declares_no_build_requirements():
    assert build_backend.get_requires_for_build_editable() == []
    assert build_backend.get_requires_for_build_wheel() == []


def test_build_backend_writes_console_and_gui_entry_points(tmp_path):
    metadata_name = build_backend.prepare_metadata_for_build_wheel(str(tmp_path))
    entry_points = tmp_path / metadata_name / "entry_points.txt"

    text = entry_points.read_text(encoding="utf-8")

    assert "[console_scripts]" in text
    assert "pdf-txn-scraper = pdf_txn_scraper.cli:main" in text
    assert "[gui_scripts]" in text
    assert "pdf-txn-scraper-gui = pdf_txn_scraper.gui:main" in text


def test_build_backend_builds_sdist_without_repository_metadata(tmp_path):
    sdist_name = build_backend.build_sdist(str(tmp_path))

    assert sdist_name.endswith(".tar.gz")
    assert (tmp_path / sdist_name).exists()
