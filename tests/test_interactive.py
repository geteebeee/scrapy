from decimal import Decimal

from pdf_txn_scraper.interactive import TransactionShell, _split_command
from pdf_txn_scraper.models import Transaction


def test_shell_edit_split_merge_and_ignore():
    rows = [Transaction("01/01", "Original", Decimal("1.00"), "01/01 Original 1.00")]
    shell = TransactionShell(rows)

    shell.onecmd('edit 0 description "Updated merchant"')
    shell.onecmd('split 0 01/02 "Second row" -2.50')
    shell.onecmd("merge 0 1")
    shell.onecmd("ignore 0")

    assert len(rows) == 1
    assert rows[0].description == "Updated merchant Second row"
    assert rows[0].ignored is True


def test_shell_command_split_preserves_windows_paths():
    parts = _split_command(r'"C:\Users\Grego\my rows.csv" --format json --all', windows=True)

    assert parts == [r"C:\Users\Grego\my rows.csv", "--format", "json", "--all"]
