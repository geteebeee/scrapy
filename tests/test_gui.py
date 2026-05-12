from pathlib import Path

import pytest

from pdf_txn_scraper.cli import build_parser


def test_gui_module_exposes_main_without_starting_tk():
    pytest.importorskip("tkinter")
    from pdf_txn_scraper import gui

    assert callable(gui.main)
    assert gui.TransactionScraperApp.columns[:3] == ("ignored", "date", "description")
    assert callable(gui.TransactionScraperApp.export_accounting_rows)


def test_cli_accepts_gui_without_input():
    args = build_parser().parse_args(["--gui"])

    assert args.gui is True
    assert args.input is None


def test_pyinstaller_spec_and_build_script_are_present():
    assert Path("pdf-transaction-scraper-gui.spec").read_text(encoding="utf-8").find("console=False") > -1
    assert Path("scripts/build_exe.py").read_text(encoding="utf-8").find("PyInstaller") > -1
