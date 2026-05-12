# PDF Transaction Scraper

A desktop GUI and CLI for extracting transaction-looking rows from PDF
statements, reviewing/fixing them, and exporting cleaned data as CSV or JSON.

## Install for local use

```bash
python -m pip install -e .
```

For local development and tests:

```bash
python -m pip install -e '.[dev]'
```

## GUI usage

Launch the desktop app after installation:

```bash
pdf-txn-scraper-gui
```

Or launch the same GUI through the CLI:

```bash
pdf-txn-scraper --gui
```

In the GUI you can:

- Open a PDF bank statement, or open a plain text extraction file for debugging.
- Review parsed rows in a table.
- Edit the selected row's date, description, amount, category, notes, and raw
  extracted text.
- Add a missing row, split a row after the current selection, merge two selected
  rows, delete rows, or toggle rows as ignored.
- Export reviewed transactions to CSV or JSON. Ignored rows are excluded unless
  you choose to include them during export.

## Build a Windows `.exe`

Install the build extras and run the checked-in PyInstaller build script:

```bash
python -m pip install -e '.[build]'
python scripts/build_exe.py
```

The generated executable is written to:

```text
dist/pdf-transaction-scraper-gui.exe
```

You can also run the `Build Windows GUI executable` GitHub Actions workflow on a
Windows runner to produce the same `.exe` as a downloadable artifact.

The build uses `pdf-transaction-scraper-gui.spec`, with `console=False`, so the
result is a windowed desktop app instead of a console application.

> Note: Build the Windows `.exe` on Windows for the most reliable result.
> PyInstaller generally does not cross-compile Windows executables from Linux or
> macOS.

## CLI usage

Parse a PDF and enter terminal review mode:

```bash
pdf-txn-scraper statement.pdf
```

Parse a PDF, review rows in the terminal, and write a CSV when you quit:

```bash
pdf-txn-scraper statement.pdf --output transactions.csv
```

Skip review and export immediately:

```bash
pdf-txn-scraper statement.pdf --non-interactive --output transactions.json --format json
```

You can also test parsing against plain text extracted from a PDF:

```bash
pdf-txn-scraper sample.txt --text --non-interactive --output transactions.csv
```

## Terminal interactive commands

Inside the terminal shell, use `help` to list commands. The most useful commands
are:

- `list [all|active|ignored]` — show parsed rows.
- `show INDEX` — inspect one row, including raw extracted text.
- `edit INDEX FIELD VALUE` — edit `date`, `description`, `amount`, `category`,
  `notes`, or `raw`.
- `ignore INDEX` — toggle whether a row is excluded from default exports.
- `split INDEX DATE "DESCRIPTION" AMOUNT` — add a missing transaction after a row.
- `merge LEFT_INDEX RIGHT_INDEX` — combine broken multi-line rows.
- `export PATH [--format csv|json] [--all]` — save the current review state.
- `quit` — leave the shell.

## Current parsing assumptions

The default parser is intentionally conservative and targets rows that look like:

```text
01/15 Grocery Store -42.18
2026-01-16 Payroll Deposit 1,250.00
```

It supports dates like `MM/DD`, `MM/DD/YYYY`, and `YYYY-MM-DD`, dollar signs,
comma separators, negative signs, and parenthesized negative amounts. Because PDF
statement layouts vary by bank, the GUI is designed for fixing rows that extract
imperfectly.
