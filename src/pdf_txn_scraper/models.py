"""Data structures used by the PDF transaction scraper."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass(slots=True)
class Transaction:
    """A transaction line extracted from a PDF statement."""

    date: str
    description: str
    amount: Decimal
    raw: str
    page: int | None = None
    category: str = ""
    notes: str = ""
    ignored: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON/CSV-friendly representation of this transaction."""
        return {
            "date": self.date,
            "description": self.description,
            "amount": str(self.amount),
            "page": self.page,
            "category": self.category,
            "notes": self.notes,
            "ignored": self.ignored,
            "raw": self.raw,
            **{f"meta_{key}": value for key, value in self.metadata.items()},
        }
