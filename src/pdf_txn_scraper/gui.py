"""Tkinter GUI for reviewing PDF statement transactions."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from .cli import infer_format
from .models import Transaction
from .parser import parse_transactions
from .pdf import extract_pdf_pages, extract_text_file
from .review import ReviewError, TransactionReviewSession


class TransactionScraperApp(tk.Tk):
    """Desktop GUI for loading, editing, and exporting transactions."""

    columns = ("ignored", "date", "description", "amount", "page", "category", "notes")

    def __init__(self) -> None:
        super().__init__()
        self.title("PDF Transaction Scraper")
        self.geometry("1100x700")
        self.minsize(900, 550)
        self.session = TransactionReviewSession()
        self.current_file: Path | None = None
        self.status = tk.StringVar(value="Open a PDF or text file to begin.")

        self._build_menu()
        self._build_layout()
        self._refresh_table()

    def _build_menu(self) -> None:
        menu = tk.Menu(self)
        file_menu = tk.Menu(menu, tearoff=False)
        file_menu.add_command(label="Open PDF...", command=self.open_pdf)
        file_menu.add_command(label="Open Text...", command=self.open_text)
        file_menu.add_separator()
        file_menu.add_command(label="Export...", command=self.export_rows)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.destroy)
        menu.add_cascade(label="File", menu=file_menu)
        self.config(menu=menu)

    def _build_layout(self) -> None:
        toolbar = ttk.Frame(self, padding=8)
        toolbar.pack(fill=tk.X)
        ttk.Button(toolbar, text="Open PDF", command=self.open_pdf).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(toolbar, text="Open Text", command=self.open_text).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(toolbar, text="Export", command=self.export_rows).pack(side=tk.LEFT, padx=(0, 18))
        ttk.Button(toolbar, text="Apply Edit", command=self.apply_edit).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(toolbar, text="Add Row", command=self.add_row).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(toolbar, text="Split After", command=self.split_after).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(toolbar, text="Toggle Ignore", command=self.toggle_ignore).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(toolbar, text="Merge Selected", command=self.merge_selected).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(toolbar, text="Delete", command=self.delete_selected).pack(side=tk.LEFT)

        main = ttk.PanedWindow(self, orient=tk.VERTICAL)
        main.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        table_frame = ttk.Frame(main)
        self.tree = ttk.Treeview(table_frame, columns=self.columns, show="headings", selectmode="extended")
        headings = {
            "ignored": "Ignored",
            "date": "Date",
            "description": "Description",
            "amount": "Amount",
            "page": "Page",
            "category": "Category",
            "notes": "Notes",
        }
        widths = {"ignored": 70, "date": 110, "description": 390, "amount": 110, "page": 70, "category": 130, "notes": 220}
        for column in self.columns:
            self.tree.heading(column, text=headings[column])
            self.tree.column(column, width=widths[column], anchor=tk.W)
        yscroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        xscroll = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        main.add(table_frame, weight=4)

        editor = ttk.LabelFrame(main, text="Selected transaction", padding=8)
        editor.columnconfigure(1, weight=1)
        self.date_var = tk.StringVar()
        self.description_var = tk.StringVar()
        self.amount_var = tk.StringVar()
        self.category_var = tk.StringVar()
        self.notes_var = tk.StringVar()
        self.raw_text = tk.Text(editor, height=4, wrap=tk.WORD)
        fields = [
            ("Date", self.date_var),
            ("Description", self.description_var),
            ("Amount", self.amount_var),
            ("Category", self.category_var),
            ("Notes", self.notes_var),
        ]
        for row, (label, variable) in enumerate(fields):
            ttk.Label(editor, text=f"{label}:").grid(row=row, column=0, sticky="w", pady=2)
            ttk.Entry(editor, textvariable=variable).grid(row=row, column=1, sticky="ew", pady=2)
        ttk.Label(editor, text="Raw text:").grid(row=5, column=0, sticky="nw", pady=2)
        self.raw_text.grid(row=5, column=1, sticky="nsew", pady=2)
        editor.rowconfigure(5, weight=1)
        main.add(editor, weight=1)

        self.tree.bind("<<TreeviewSelect>>", self._load_selected_into_editor)
        ttk.Label(self, textvariable=self.status, anchor=tk.W, padding=(8, 0, 8, 8)).pack(fill=tk.X)

    def open_pdf(self) -> None:
        """Prompt for and parse a PDF file."""
        path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")])
        if not path:
            return
        password = None
        try:
            pages = extract_pdf_pages(path)
        except ValueError as exc:
            if "encrypted" not in str(exc).lower():
                self._show_error(exc)
                return
            password = simpledialog.askstring("PDF password", "Enter PDF password:", show="*")
            if password is None:
                return
            try:
                pages = extract_pdf_pages(path, password=password)
            except Exception as password_exc:  # noqa: BLE001 - surface GUI load errors to user.
                self._show_error(password_exc)
                return
        except Exception as exc:  # noqa: BLE001 - surface GUI load errors to user.
            self._show_error(exc)
            return
        self._load_transactions(path, parse_transactions(pages))

    def open_text(self) -> None:
        """Prompt for and parse a plain text extraction file."""
        path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if not path:
            return
        try:
            self._load_transactions(path, parse_transactions(extract_text_file(path)))
        except Exception as exc:  # noqa: BLE001 - surface GUI load errors to user.
            self._show_error(exc)

    def _load_transactions(self, path: str, transactions: list[Transaction]) -> None:
        self.current_file = Path(path)
        self.session.replace(transactions)
        self.status.set(f"Loaded {len(transactions)} rows from {self.current_file.name}.")
        self._refresh_table()

    def apply_edit(self) -> None:
        """Apply editor fields to the selected transaction."""
        index = self._single_selected_index()
        if index is None:
            return
        updates = {
            "date": self.date_var.get(),
            "description": self.description_var.get(),
            "amount": self.amount_var.get(),
            "category": self.category_var.get(),
            "notes": self.notes_var.get(),
            "raw": self.raw_text.get("1.0", tk.END).strip(),
        }
        try:
            for field, value in updates.items():
                self.session.edit(index, field, value)
        except ReviewError as exc:
            self._show_error(exc)
            return
        self._refresh_table(select=index)
        self.status.set(f"Updated row {index}.")

    def add_row(self) -> None:
        """Append a new row using the editor fields."""
        try:
            transaction = self.session.add(self.date_var.get(), self.description_var.get(), self.amount_var.get())
            transaction.category = self.category_var.get()
            transaction.notes = self.notes_var.get()
            raw = self.raw_text.get("1.0", tk.END).strip()
            if raw:
                transaction.raw = raw
        except ReviewError as exc:
            self._show_error(exc)
            return
        self._refresh_table(select=len(self.session.transactions) - 1)
        self.status.set("Added manual row.")

    def split_after(self) -> None:
        """Insert a new row after the selected row using editor fields."""
        index = self._single_selected_index()
        if index is None:
            return
        try:
            transaction = self.session.split_after(index, self.date_var.get(), self.description_var.get(), self.amount_var.get())
            transaction.category = self.category_var.get()
            transaction.notes = self.notes_var.get()
            raw = self.raw_text.get("1.0", tk.END).strip()
            if raw:
                transaction.raw = raw
        except ReviewError as exc:
            self._show_error(exc)
            return
        self._refresh_table(select=index + 1)
        self.status.set(f"Inserted row after {index}.")

    def toggle_ignore(self) -> None:
        """Toggle ignored state for selected rows."""
        indices = self._selected_indices()
        if not indices:
            return
        for index in indices:
            self.session.toggle_ignore(index)
        self._refresh_table(select=indices[0])
        self.status.set(f"Toggled ignore for {len(indices)} row(s).")

    def merge_selected(self) -> None:
        """Merge exactly two selected rows."""
        indices = self._selected_indices()
        if len(indices) != 2:
            messagebox.showinfo("Merge rows", "Select exactly two rows to merge.")
            return
        left, right = sorted(indices)
        try:
            self.session.merge(left, right)
        except ReviewError as exc:
            self._show_error(exc)
            return
        self._refresh_table(select=left)
        self.status.set(f"Merged row {right} into row {left}.")

    def delete_selected(self) -> None:
        """Delete selected rows after confirmation."""
        indices = self._selected_indices()
        if not indices:
            return
        if not messagebox.askyesno("Delete rows", f"Delete {len(indices)} selected row(s)?"):
            return
        for index in sorted(indices, reverse=True):
            self.session.delete(index)
        self._refresh_table(select=min(indices[0], len(self.session.transactions) - 1))
        self.status.set(f"Deleted {len(indices)} row(s).")

    def export_rows(self) -> None:
        """Prompt for output path and export reviewed rows."""
        if not self.session.transactions:
            messagebox.showinfo("Export", "There are no transactions to export.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        include_ignored = messagebox.askyesno("Export", "Include ignored rows in the export?")
        output_format = infer_format(path, None)
        try:
            count = self.session.export(path, output_format, include_ignored=include_ignored)
        except ReviewError as exc:
            self._show_error(exc)
            return
        self.status.set(f"Exported {count} row(s) to {path}.")

    def _refresh_table(self, select: int | None = None) -> None:
        for row in self.tree.get_children():
            self.tree.delete(row)
        for index, transaction in enumerate(self.session.transactions):
            self.tree.insert(
                "",
                tk.END,
                iid=str(index),
                values=(
                    "yes" if transaction.ignored else "",
                    transaction.date,
                    transaction.description,
                    str(transaction.amount),
                    transaction.page or "",
                    transaction.category,
                    transaction.notes,
                ),
            )
        if select is not None and 0 <= select < len(self.session.transactions):
            iid = str(select)
            self.tree.selection_set(iid)
            self.tree.focus(iid)
            self.tree.see(iid)
            self._load_selected_into_editor()
        elif not self.session.transactions:
            self._clear_editor()

    def _load_selected_into_editor(self, event: tk.Event | None = None) -> None:
        index = self._single_selected_index(show_message=False)
        if index is None:
            return
        transaction = self.session.get(index)
        self.date_var.set(transaction.date)
        self.description_var.set(transaction.description)
        self.amount_var.set(str(transaction.amount))
        self.category_var.set(transaction.category)
        self.notes_var.set(transaction.notes)
        self.raw_text.delete("1.0", tk.END)
        self.raw_text.insert("1.0", transaction.raw)

    def _clear_editor(self) -> None:
        self.date_var.set("")
        self.description_var.set("")
        self.amount_var.set("")
        self.category_var.set("")
        self.notes_var.set("")
        self.raw_text.delete("1.0", tk.END)

    def _selected_indices(self) -> list[int]:
        return sorted(int(item_id) for item_id in self.tree.selection())

    def _single_selected_index(self, show_message: bool = True) -> int | None:
        indices = self._selected_indices()
        if len(indices) == 1:
            return indices[0]
        if show_message:
            messagebox.showinfo("Select row", "Select exactly one row first.")
        return None

    def _show_error(self, exc: BaseException) -> None:
        messagebox.showerror("PDF Transaction Scraper", str(exc))
        self.status.set(str(exc))


def main() -> None:
    """Launch the desktop GUI."""
    app = TransactionScraperApp()
    app.mainloop()


if __name__ == "__main__":
    main()
