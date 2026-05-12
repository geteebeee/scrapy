import json
from decimal import Decimal

from pdf_txn_scraper.export import active_transactions, export_json
from pdf_txn_scraper.models import Transaction


def test_active_transactions_excludes_ignored_rows(tmp_path):
    rows = [
        Transaction("01/01", "Kept", Decimal("1.00"), "01/01 Kept 1.00"),
        Transaction("01/02", "Ignored", Decimal("2.00"), "01/02 Ignored 2.00", ignored=True),
    ]

    assert [row.description for row in active_transactions(rows)] == ["Kept"]


def test_export_json_serializes_decimals(tmp_path):
    output = tmp_path / "transactions.json"
    rows = [Transaction("01/01", "Coffee", Decimal("-3.25"), "01/01 Coffee -3.25")]

    export_json(rows, output)

    assert json.loads(output.read_text(encoding="utf-8"))[0]["amount"] == "-3.25"
