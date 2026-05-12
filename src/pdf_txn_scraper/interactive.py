"""Interactive transaction review shell."""

from __future__ import annotations

import cmd
import shlex
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .export import active_transactions, export_csv, export_json
from .models import Transaction


class TransactionShell(cmd.Cmd):
    """Small command shell for manipulating extracted transaction lines."""

    intro = "Interactive transaction review. Type help or ? to list commands."
    prompt = "pdf-txn> "

    def __init__(self, transactions: list[Transaction]) -> None:
        super().__init__()
        self.transactions = transactions

    def do_list(self, arg: str) -> None:
        """list [all|active|ignored]: show extracted transaction rows."""
        mode = arg.strip() or "active"
        for index, transaction in enumerate(self.transactions):
            if mode != "all" and mode != "ignored" and transaction.ignored:
                continue
            if mode == "ignored" and not transaction.ignored:
                continue
            marker = "x" if transaction.ignored else " "
            page = f"p{transaction.page}" if transaction.page else "text"
            print(
                f"{index:03d} [{marker}] {transaction.date:<10} "
                f"{transaction.amount:>12} {page:<5} {transaction.description}"
            )

    def do_show(self, arg: str) -> None:
        """show INDEX: show full details for a row."""
        transaction = self._get(arg)
        if transaction is None:
            return
        for key, value in transaction.as_dict().items():
            print(f"{key}: {value}")

    def do_edit(self, arg: str) -> None:
        """edit INDEX FIELD VALUE: edit date, description, amount, category, notes, or raw."""
        try:
            parts = shlex.split(arg)
        except ValueError as exc:
            print(exc)
            return
        if len(parts) < 3:
            print("Usage: edit INDEX FIELD VALUE")
            return
        index_text, field = parts[:2]
        value = " ".join(parts[2:])
        transaction = self._get(index_text)
        if transaction is None:
            return
        if field not in {"date", "description", "amount", "category", "notes", "raw"}:
            print("Field must be one of: date, description, amount, category, notes, raw")
            return
        if field == "amount":
            try:
                setattr(transaction, field, Decimal(value))
            except InvalidOperation:
                print(f"Invalid decimal amount: {value}")
                return
        else:
            setattr(transaction, field, value)

    def do_ignore(self, arg: str) -> None:
        """ignore INDEX: toggle whether a row is excluded from default export."""
        transaction = self._get(arg)
        if transaction is None:
            return
        transaction.ignored = not transaction.ignored
        state = "ignored" if transaction.ignored else "active"
        print(f"Row {arg.strip()} is now {state}.")

    def do_split(self, arg: str) -> None:
        """split INDEX DATE DESCRIPTION AMOUNT: insert a new row after INDEX."""
        try:
            parts = shlex.split(arg)
            if len(parts) != 4:
                raise ValueError
            index_text, date, description, amount_text = parts
            index = int(index_text)
            amount = Decimal(amount_text)
        except (ValueError, InvalidOperation):
            print('Usage: split INDEX DATE "DESCRIPTION" AMOUNT')
            return
        if not 0 <= index < len(self.transactions):
            print(f"Index out of range: {index}")
            return
        source = self.transactions[index]
        self.transactions.insert(
            index + 1,
            Transaction(date=date, description=description, amount=amount, raw=description, page=source.page),
        )

    def do_merge(self, arg: str) -> None:
        """merge LEFT_INDEX RIGHT_INDEX: append right description/raw to left and remove right."""
        try:
            left_index, right_index = [int(part) for part in shlex.split(arg)]
        except ValueError:
            print("Usage: merge LEFT_INDEX RIGHT_INDEX")
            return
        if not (0 <= left_index < len(self.transactions) and 0 <= right_index < len(self.transactions)):
            print("Index out of range.")
            return
        if left_index == right_index:
            print("Cannot merge a row into itself.")
            return
        left = self.transactions[left_index]
        right = self.transactions[right_index]
        left.description = f"{left.description} {right.description}".strip()
        left.raw = f"{left.raw}\n{right.raw}".strip()
        del self.transactions[right_index]

    def do_export(self, arg: str) -> None:
        """export PATH [--format csv|json] [--all]: export reviewed rows."""
        try:
            parts = shlex.split(arg)
        except ValueError as exc:
            print(exc)
            return
        if not parts:
            print("Usage: export PATH [--format csv|json] [--all]")
            return
        path = Path(parts[0])
        include_all = "--all" in parts
        fmt = path.suffix.lower().lstrip(".") or "csv"
        if "--format" in parts:
            try:
                fmt = parts[parts.index("--format") + 1]
            except IndexError:
                print("--format needs csv or json")
                return
        rows = self.transactions if include_all else active_transactions(self.transactions)
        if fmt == "csv":
            export_csv(rows, path)
        elif fmt == "json":
            export_json(rows, path)
        else:
            print("Format must be csv or json")
            return
        print(f"Exported {len(rows)} rows to {path}")

    def do_quit(self, arg: str) -> bool:
        """quit: exit the interactive shell."""
        return True

    def do_EOF(self, arg: str) -> bool:  # noqa: N802 - cmd expects this name
        """Exit on Ctrl-D."""
        print()
        return True

    def _get(self, index_text: str) -> Transaction | None:
        try:
            index = int(index_text.strip())
        except ValueError:
            print("Expected a numeric row index.")
            return None
        if not 0 <= index < len(self.transactions):
            print(f"Index out of range: {index}")
            return None
        return self.transactions[index]
