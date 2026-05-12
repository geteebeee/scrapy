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
        ("1.000.000,00-", Decimal("-1000000.00")),
        ("24.954,10+", Decimal("24954.10")),
    ],
)
def test_parse_amount(raw, expected):
    assert parse_amount(raw) == expected


def test_parse_amount_reports_invalid_values():
    with pytest.raises(ValueError, match="Could not parse amount"):
        parse_amount("not-money")


def test_parse_transactions_finds_nordea_statement_blocks():
    text = """
    Kausi
    01.12.2025 - 31.12.2025
    Arkistointitunnus
    Saajan tilinumero
    Maksup
    Arvop
    Saaja / Maksaja
    Viesti
    Tap.
    nro
    Määrä
    Kirjauspäivä 02.12.
    2512022584SM100261

    02.12.
    02.12.
    EQT VIII FC Cooperatief UA
    710 Maksumääräys
    2584SMM0191458
    /ROC/CL6132024///URI/EQT VIII FC CO
    OP U.A.
    1 24.954,10+
    2512022584SM100262

    02.12.
    02.12.
    Nordea Bank Oyj
    730 Palvelumaksu ALV 0%
    2584SMM0191458
    2 7,00-
    """

    transactions = parse_transactions([(1, text)])

    assert [transaction.date for transaction in transactions] == ["02.12.2025", "02.12.2025"]
    assert transactions[0].description.startswith("EQT VIII FC Cooperatief UA")
    assert transactions[0].amount == Decimal("24954.10")
    assert transactions[0].metadata["archive_id"] == "2512022584SM100261"
    assert transactions[0].metadata["transaction_number"] == 1
    assert transactions[1].description == "Nordea Bank Oyj 730 Palvelumaksu ALV 0% 2584SMM0191458"
    assert transactions[1].amount == Decimal("-7.00")


def test_parse_transactions_skips_nordea_service_fee_detail_sums():
    text = """
    Kausi
    01.06.2025 - 30.06.2025
    Kirjauspäivä 04.06.
    250604258883D98891

    04.06.
    04.06.
    NORDEA
    730 Palvelumaksu
    01.05.-31.05.2025
    1 16,74-
    250604258883D98891

    04.06. NORDEA
    730 Palvelumaksu
    Konttoripalvelut
    Viitteettömät panot              *)
          1 kpl a    0,580 e       0,58
    *) alv rek. 0%
    10,58-
    """

    transactions = parse_transactions([(1, text)])

    assert [transaction.amount for transaction in transactions] == [Decimal("-16.74")]
