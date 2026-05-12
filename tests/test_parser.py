from decimal import Decimal

import pytest

from pdf_txn_scraper.parser import parse_amount, parse_transactions


def test_parse_transactions_finds_common_statement_rows():
    text = """
    Statement Period January
    01/02 Coffee Shop -4.50
    extra memo line
    2026-01-03 Payroll Deposit $1,250.00
    1/4/26 Card Payment (35.12)
    """

    transactions = parse_transactions([(1, text)])

    assert [transaction.date for transaction in transactions] == ["01/02", "2026-01-03", "1/4/26"]
    assert transactions[0].description == "Coffee Shop extra memo line"
    assert transactions[0].amount == Decimal("-4.50")
    assert transactions[1].amount == Decimal("1250.00")
    assert transactions[2].amount == Decimal("-35.12")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("$1,234.56", Decimal("1234.56")),
        ("-$10.00", Decimal("-10.00")),
        ("(42.99)", Decimal("-42.99")),
    ],
)
def test_parse_amount(raw, expected):
    assert parse_amount(raw) == expected


def test_parse_amount_reports_invalid_values():
    with pytest.raises(ValueError, match="Could not parse amount"):
        parse_amount("not-money")
