import csv

from pdf_txn_scraper.cli import main


def test_cli_exports_plain_text_non_interactively(tmp_path):
    source = tmp_path / "statement.txt"
    output = tmp_path / "transactions.csv"
    source.write_text("01/02 Coffee -4.50\n", encoding="utf-8")

    exit_code = main([str(source), "--text", "--non-interactive", "--output", str(output)])

    assert exit_code == 0
    with output.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["description"] == "Coffee"
    assert rows[0]["amount"] == "-4,50"
