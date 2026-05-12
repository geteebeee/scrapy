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
NORDEA_PERIOD_PATTERN = re.compile(r"^\d{2}\.\d{2}\.(?P<year>\d{4})\s+-\s+\d{2}\.\d{2}\.\d{4}$")
NORDEA_BOOKING_DATE_PATTERN = re.compile(r"^Kirjauspäivä\s+(?P<day>\d{2})\.(?P<month>\d{2})\.$")
NORDEA_DATE_PATTERN = re.compile(r"^(?P<day>\d{2})\.(?P<month>\d{2})\.(?:\s+(?P<rest>.+))?$")
NORDEA_ARCHIVE_PATTERN = re.compile(
    r"^(?:[1-9]\d(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])[A-Z0-9]{8,}|GSIPC[A-Z0-9]{10,})$"
)
NORDEA_AMOUNT_PATTERN = re.compile(
    r"^(?:(?P<number>\d{1,4})\s+)?(?P<amount>\d{1,3}(?:\.\d{3})*,\d{2}[+-])$"
)
NORDEA_SUMMARY_WORDS = (
    "saldo",
    "käyttövara",
    "panot",
    "otot",
    "asiakkaan tulostama",
    "file://",
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


@dataclass(slots=True)
class _NordeaBlock:
    archive_id: str
    raw: list[str]
    description: list[str]
    date: str | None = None


def parse_amount(value: str) -> Decimal:
    """Parse a statement amount, including US and Finnish/European formats."""
    cleaned = value.strip().replace("$", "")
    suffix_negative = cleaned.endswith("-")
    suffix_positive = cleaned.endswith("+")
    if suffix_negative or suffix_positive:
        cleaned = cleaned[:-1].replace(".", "").replace(",", ".")
    else:
        cleaned = cleaned.replace(",", "")

    negative = cleaned.startswith("(") and cleaned.endswith(")") or suffix_negative
    cleaned = cleaned.strip("()")
    try:
        amount = Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError(f"Could not parse amount: {value!r}") from exc
    return -amount if negative else amount


def _format_nordea_date(day: str, month: str, year: int | None) -> str:
    if year is None:
        return f"{day}.{month}."
    return f"{day}.{month}.{year}"


def _parse_nordea_amount_line(line: str, transaction_number: int | None) -> tuple[int | None, Decimal] | None:
    match = NORDEA_AMOUNT_PATTERN.match(line)
    if not match:
        return None

    number = match.group("number")
    amount_text = match.group("amount")
    if number is not None:
        return int(number), parse_amount(amount_text)

    if transaction_number is not None and line.startswith(str(transaction_number)):
        amount_text = line[len(str(transaction_number)) :]
        if re.fullmatch(r"\d{1,3}(?:\.\d{3})*,\d{2}[+-]", amount_text):
            return transaction_number, parse_amount(amount_text)

    return None


def _is_nordea_noise(line: str) -> bool:
    lowered = line.lower()
    return (
        not line
        or any(word in lowered for word in NORDEA_SUMMARY_WORDS)
        or lowered in {"sivu 1", "sivu 2", "kausi", "swift/bic", "tiliote"}
        or lowered in {"arkistointitunnus", "saajan tilinumero", "maksup", "arvop", "saaja / maksaja"}
        or lowered in {"viesti", "tap.", "nro", "määrä", "valuutta", "eur", "iban"}
    )


def _parse_nordea_transactions(pages: Iterable[tuple[int | None, str]]) -> list[Transaction]:
    transactions: list[Transaction] = []
    period_year: int | None = None
    booking_date: str | None = None
    transaction_number: int | None = None
    block: _NordeaBlock | None = None

    def finish_block(amount: Decimal, number: int | None, page: int | None) -> None:
        nonlocal block
        if block is None:
            return
        raw_lines = block.raw
        description_lines = block.description
        date = block.date or booking_date or ""
        description = " ".join(str(line) for line in description_lines).strip()
        if not date or not description:
            block = None
            return
        transactions.append(
            Transaction(
                date=str(date),
                description=description,
                amount=amount,
                raw="\n".join(str(line) for line in raw_lines),
                page=page,
                metadata={
                    "archive_id": block.archive_id,
                    **({"transaction_number": number} if number is not None else {}),
                },
            )
        )
        block = None

    previous_line = ""
    for page, line in iter_lines(pages):
        if previous_line == "Kausi":
            period_match = NORDEA_PERIOD_PATTERN.match(line)
            if period_match:
                period_year = int(period_match.group("year"))

        booking_match = NORDEA_BOOKING_DATE_PATTERN.match(line)
        if booking_match:
            booking_date = _format_nordea_date(booking_match.group("day"), booking_match.group("month"), period_year)

        if NORDEA_ARCHIVE_PATTERN.match(line) and not _is_nordea_noise(line):
            block = _NordeaBlock(archive_id=line, raw=[line], description=[])
            previous_line = line
            continue

        if block is None:
            previous_line = line
            continue

        block.raw.append(line)
        amount_line = _parse_nordea_amount_line(line, transaction_number)
        if amount_line is not None:
            number, amount = amount_line
            transaction_number = number
            finish_block(amount, number, page)
            previous_line = line
            continue

        date_match = NORDEA_DATE_PATTERN.match(line)
        if date_match:
            date = _format_nordea_date(date_match.group("day"), date_match.group("month"), period_year)
            if block.date is None:
                block.date = date
            rest = date_match.group("rest")
            if rest:
                block.description.append(rest)
            previous_line = line
            continue

        if not _is_nordea_noise(line):
            block.description.append(line)
        previous_line = line

    return transactions


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
    pages = list(pages)
    nordea_transactions = _parse_nordea_transactions(pages)
    if nordea_transactions:
        return nordea_transactions

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
