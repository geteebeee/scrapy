"""Transaction parsing helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Iterable

from .models import Transaction

DEFAULT_TRANSACTION_PATTERN = re.compile(
    r"^\s*"
    r"(?P<date>(?:\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)|(?:\d{4}-\d{2}-\d{2}))"
    r"\s+"
    r"(?P<description>.+?)"
    r"\s+"
    r"(?P<amount>[-+]?\(?\$?\d{1,3}(?:,\d{3})*(?:\.\d{2})?\)?|[-+]?\(?\$?\d+(?:\.\d{2})?\)?)"
    r"\s*$"
)


@dataclass(frozen=True, slots=True)
class ParseConfig:
    """Configurable parsing behavior for statement text."""

    transaction_pattern: re.Pattern[str] = DEFAULT_TRANSACTION_PATTERN
    skip_patterns: tuple[re.Pattern[str], ...] = (
        re.compile(r"^\s*$"),
        re.compile(r"\b(page|statement|balance|account)\b", re.IGNORECASE),
    )
    join_continuations: bool = True


def parse_amount(value: str) -> Decimal:
    """Parse a statement amount, including commas, dollars, and parentheses."""
    cleaned = value.strip().replace("$", "").replace(",", "")
    negative = cleaned.startswith("(") and cleaned.endswith(")")
    cleaned = cleaned.strip("()")
    try:
        amount = Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError(f"Could not parse amount: {value!r}") from exc
    return -amount if negative else amount


def iter_lines(pages: Iterable[tuple[int | None, str]]) -> Iterable[tuple[int | None, str]]:
    """Yield normalized lines with their source page numbers."""
    for page, text in pages:
        for line in text.splitlines():
            yield page, " ".join(line.strip().split())


def parse_transactions(
    pages: Iterable[tuple[int | None, str]],
    config: ParseConfig | None = None,
) -> list[Transaction]:
    """Parse transaction-looking rows from extracted statement text.

    The parser intentionally uses a conservative default pattern. In interactive
    mode users can edit, split, merge, ignore, or annotate rows that their bank's
    PDF layout did not expose cleanly.
    """
    cfg = config or ParseConfig()
    transactions: list[Transaction] = []
    pending_index: int | None = None

    for page, line in iter_lines(pages):
        if any(pattern.search(line) for pattern in cfg.skip_patterns):
            continue

        match = cfg.transaction_pattern.match(line)
        if match:
            transactions.append(
                Transaction(
                    date=match.group("date"),
                    description=match.group("description").strip(),
                    amount=parse_amount(match.group("amount")),
                    raw=line,
                    page=page,
                )
            )
            pending_index = len(transactions) - 1
            continue

        if cfg.join_continuations and pending_index is not None and line:
            transaction = transactions[pending_index]
            transaction.description = f"{transaction.description} {line}".strip()
            transaction.raw = f"{transaction.raw}\n{line}"

    return transactions
