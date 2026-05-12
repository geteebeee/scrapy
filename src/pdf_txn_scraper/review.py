"""Reusable transaction review operations for CLI and GUI front-ends."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable

from .export import active_transactions, export_accounting_csv, export_csv, export_json
from .models import Transaction

EDITABLE_FIELDS = {"date", "description", "amount", "category", "notes", "raw"}


class ReviewError(ValueError):
    """Raised when a review operation cannot be applied."""


class TransactionReviewSession:
    """Mutable review session around extracted transactions."""

    def __init__(self, transactions: Iterable[Transaction] | None = None) -> None:
        self.transactions = list(transactions or [])

    def replace(self, transactions: Iterable[Transaction]) -> None:
        """Replace all transactions in the review session."""
        self.transactions = list(transactions)

    def get(self, index: int) -> Transaction:
        """Return one transaction by index or raise a ReviewError."""
        if not 0 <= index < len(self.transactions):
            raise ReviewError(f"Index out of range: {index}")
        return self.transactions[index]

    def edit(self, index: int, field: str, value: str) -> None:
        """Edit one field on a transaction."""
        if field not in EDITABLE_FIELDS:
            fields = ", ".join(sorted(EDITABLE_FIELDS))
            raise ReviewError(f"Field must be one of: {fields}")
        transaction = self.get(index)
        if field == "amount":
            try:
                parsed_value = Decimal(value)
            except InvalidOperation as exc:
                raise ReviewError(f"Invalid decimal amount: {value}") from exc
            setattr(transaction, field, parsed_value)
            return
        setattr(transaction, field, value)

    def toggle_ignore(self, index: int) -> bool:
        """Toggle ignored state and return the new state."""
        transaction = self.get(index)
        transaction.ignored = not transaction.ignored
        return transaction.ignored

    def split_after(self, index: int, date: str, description: str, amount: str) -> Transaction:
        """Insert a new transaction after an existing transaction."""
        source = self.get(index)
        try:
            parsed_amount = Decimal(amount)
        except InvalidOperation as exc:
            raise ReviewError(f"Invalid decimal amount: {amount}") from exc
        transaction = Transaction(
            date=date,
            description=description,
            amount=parsed_amount,
            raw=f"{date} {description} {amount}",
            page=source.page,
        )
        self.transactions.insert(index + 1, transaction)
        return transaction

    def add(self, date: str, description: str, amount: str) -> Transaction:
        """Append a manually entered transaction."""
        try:
            parsed_amount = Decimal(amount)
        except InvalidOperation as exc:
            raise ReviewError(f"Invalid decimal amount: {amount}") from exc
        transaction = Transaction(
            date=date,
            description=description,
            amount=parsed_amount,
            raw=f"{date} {description} {amount}",
        )
        self.transactions.append(transaction)
        return transaction

    def merge(self, left_index: int, right_index: int) -> None:
        """Merge two rows by appending right row text to the left row."""
        if left_index == right_index:
            raise ReviewError("Cannot merge a row into itself.")
        left = self.get(left_index)
        right = self.get(right_index)
        left.description = f"{left.description} {right.description}".strip()
        left.raw = f"{left.raw}\n{right.raw}".strip()
        del self.transactions[right_index]

    def delete(self, index: int) -> Transaction:
        """Delete and return a transaction."""
        self.get(index)
        return self.transactions.pop(index)

    def export(self, output: str | Path, output_format: str, include_ignored: bool = False) -> int:
        """Export reviewed transactions and return the number of exported rows."""
        rows = self.transactions if include_ignored else active_transactions(self.transactions)
        if output_format == "csv":
            export_csv(rows, output)
        elif output_format == "json":
            export_json(rows, output)
        else:
            raise ReviewError("Format must be csv or json")
        return len(rows)

    def export_accounting(self, output: str | Path, include_ignored: bool = False) -> int:
        """Export rows plus inverted debit/credit copies and return written row count."""
        rows = self.transactions if include_ignored else active_transactions(self.transactions)
        export_accounting_csv(rows, output)
        return len(rows) * 2
