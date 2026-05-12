"""Command-line interface for PDF transaction scraping."""

from __future__ import annotations

import argparse
import getpass
from pathlib import Path

from .export import active_transactions, export_csv, export_json
from .interactive import TransactionShell
from .parser import parse_transactions
from .pdf import extract_pdf_pages, extract_text_file


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="pdf-txn-scraper",
        description="Extract transaction-like rows from PDF statements and review them interactively.",
    )
    parser.add_argument("input", nargs="?", help="PDF statement path, or plain text when --text is used.")
    parser.add_argument("-o", "--output", help="Export path for non-interactive runs or quick save after review.")
    parser.add_argument("--format", choices=("csv", "json"), help="Output format. Defaults to output extension or csv.")
    parser.add_argument("--text", action="store_true", help="Treat input as a plain text file instead of a PDF.")
    parser.add_argument("--password", help="PDF password. If omitted for encrypted PDFs, you will be prompted.")
    parser.add_argument("--ask-password", action="store_true", help="Prompt for a PDF password before opening the file.")
    parser.add_argument("--non-interactive", action="store_true", help="Skip review shell and export parsed rows immediately.")
    parser.add_argument("--include-ignored", action="store_true", help="Include ignored rows when exporting from the CLI.")
    parser.add_argument("--gui", action="store_true", help="Launch the desktop GUI instead of terminal review mode.")
    return parser


def infer_format(output: str | None, explicit_format: str | None) -> str:
    """Infer export format from CLI options."""
    if explicit_format:
        return explicit_format
    if output and Path(output).suffix.lower() == ".json":
        return "json"
    return "csv"


def write_output(transactions, output: str, output_format: str, include_ignored: bool = False) -> None:
    """Export transactions to the requested file."""
    rows = transactions if include_ignored else active_transactions(transactions)
    if output_format == "csv":
        export_csv(rows, output)
    elif output_format == "json":
        export_json(rows, output)
    else:  # Defensive guard if called outside argparse.
        raise ValueError(f"Unsupported output format: {output_format}")
    print(f"Exported {len(rows)} rows to {output}")


def main(argv: list[str] | None = None) -> int:
    """Run the CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.gui:
        from .gui import main as gui_main

        gui_main()
        return 0

    if not args.input:
        parser.error("input is required unless --gui is used")

    password = args.password
    if args.ask_password:
        password = getpass.getpass("PDF password: ")

    pages = extract_text_file(args.input) if args.text else extract_pdf_pages(args.input, password=password)
    transactions = parse_transactions(pages)
    print(f"Parsed {len(transactions)} transaction rows.")

    output_format = infer_format(args.output, args.format)
    if args.non_interactive:
        if not args.output:
            parser.error("--non-interactive requires --output")
        write_output(transactions, args.output, output_format, args.include_ignored)
        return 0

    TransactionShell(transactions).cmdloop()
    if args.output:
        write_output(transactions, args.output, output_format, args.include_ignored)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
