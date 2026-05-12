from decimal import Decimal

import pytest

from pdf_txn_scraper.models import Transaction
from pdf_txn_scraper.review import ReviewError, TransactionReviewSession


def test_review_session_edits_adds_merges_and_deletes_rows(tmp_path):
    session = TransactionReviewSession(
        [Transaction("01/01", "Original", Decimal("1.00"), "01/01 Original 1.00")]
    )

    session.edit(0, "description", "Updated")
    session.split_after(0, "01/02", "Second", "-2.50")
    session.merge(0, 1)
    ignored = session.toggle_ignore(0)
    deleted = session.delete(0)

    assert ignored is True
    assert deleted.description == "Updated Second"
    assert session.transactions == []


def test_review_session_exports_active_rows(tmp_path):
    session = TransactionReviewSession(
        [
            Transaction("01/01", "Kept", Decimal("1.00"), "01/01 Kept 1.00"),
            Transaction("01/02", "Ignored", Decimal("2.00"), "01/02 Ignored 2.00", ignored=True),
        ]
    )
    output = tmp_path / "rows.csv"

    count = session.export(output, "csv")

    assert count == 1
    assert "Kept" in output.read_text(encoding="utf-8")
    assert "Ignored" not in output.read_text(encoding="utf-8")


def test_review_session_validates_amounts():
    session = TransactionReviewSession(
        [Transaction("01/01", "Original", Decimal("1.00"), "01/01 Original 1.00")]
    )

    with pytest.raises(ReviewError, match="Invalid decimal amount"):
        session.edit(0, "amount", "oops")
