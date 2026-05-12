"""Export helpers for reviewed transactions."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable

from .models import Transaction


def active_transactions(transactions: Iterable[Transaction]) -> list[Transaction]:
    """Return transactions not marked ignored."""
    return [transaction for transaction in transactions if not transaction.ignored]


def export_csv(transactions: Iterable[Transaction], path: str | Path) -> None:
    """Write transactions to CSV."""
    rows = [transaction.as_dict() for transaction in transactions]
    _write_csv_rows(rows, path)


def export_accounting_csv(transactions: Iterable[Transaction], path: str | Path) -> None:
    """Write transactions, then mirrored debit/credit rows with inverted amounts."""
    transaction_rows = list(transactions)
    rows = []
    for transaction in transaction_rows:
        rows.append(transaction.as_dict())
        row = transaction.as_dict()
        row["amount"] = str(-transaction.amount)
        rows.append(row)
    _write_csv_rows(rows, path)


def _write_csv_rows(rows: list[dict[str, Any]], path: str | Path) -> None:
    """Write CSV rows while preserving known fields first and metadata after."""
    fieldnames = ["date", "description", "amount", "page", "category", "notes", "ignored", "raw"]
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)

    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(_single_line_csv_row(row) for row in rows)


def _single_line_csv_row(row: dict[str, Any]) -> dict[str, Any]:
    """Return a CSV row with embedded line breaks flattened inside cells."""
    return {key: _single_line_csv_value(value) for key, value in row.items()}


def _single_line_csv_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    return " ".join(line.strip() for line in value.splitlines())


def export_json(transactions: Iterable[Transaction], path: str | Path) -> None:
    """Write transactions to JSON."""
    payload = [transaction.as_dict() for transaction in transactions]
    Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
