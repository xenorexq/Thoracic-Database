"""
Minimal HTML viewer for Tkinter
--------------------------------

This module provides a lightweight replacement for the third‑party
``tkhtmlview`` package.  It implements a ``HTMLScrolledText`` widget
compatible with Tkinter that can display a very small subset of HTML
markup.  The primary goal is to render the embedded AJCC staging
reference files contained in this project without requiring any
external dependencies.

Supported tags:

* ``h1``, ``h2`` and ``h3`` – rendered as bold headings with
  progressively smaller font sizes.
* ``p`` – inserts a blank line before the paragraph text.
* ``br`` – inserts a line break.
* ``strong`` – applies a bold font to the enclosed text.
* ``hr`` – inserts a horizontal rule (rendered as a line of dashes).
* ``table``, ``tr``, ``th`` and ``td`` – tables are converted into
  plain text.  Header rows (``th``) are rendered in bold and cells
  are separated by a few spaces.  Border attributes are ignored.

Any unsupported tags are ignored and their contents are displayed as
plain text.  Nested tags are handled in a simple stack‑based manner,
allowing combinations such as bold headings.  While not a full HTML
renderer, this implementation is sufficient for the structured
definition tables contained in the AJCC reference documents.

Usage example::

    from tkinter import Tk
    from tkhtmlview import HTMLScrolledText

    root = Tk()
    viewer = HTMLScrolledText(root, width=60)
    viewer.pack(fill="both", expand=True)
    viewer.set_html("<h1>Hello</h1><p>This is <strong>bold</strong> text.</p>")
    root.mainloop()

"""

from __future__ import annotations

import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from html.parser import HTMLParser

__all__ = ["HTMLScrolledText"]


class _SimpleHTMLParser(HTMLParser):
    """Internal HTML parser that writes parsed content into a text widget.

    This parser walks through a limited subset of HTML and inserts
    corresponding text into a target ``ScrolledText`` widget.  It
    ignores unsupported tags and treats their contents as plain text.
    Heading levels and bold styling are recorded on a tag stack so
    that multiple styles can be applied simultaneously.
    """

    def __init__(self, widget: ScrolledText) -> None:
        super().__init__()
        self.widget = widget
        self.tag_stack: list[str] = []
        self.in_table: bool = False
        self.current_row: list[str] = []
        self.current_cell: str | None = None
        self.row_is_header: bool = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str]]) -> None:
        tag = tag.lower()
        if tag in {"h1", "h2", "h3"}:
            # start of a heading; push onto stack
            self.tag_stack.append(tag)
        elif tag == "strong":
            self.tag_stack.append("bold")
        elif tag == "p":
            # paragraphs separated by blank line
            self.widget.insert(tk.END, "\n")
        elif tag == "br":
            self.widget.insert(tk.END, "\n")
        elif tag == "hr":
            self.widget.insert(tk.END, "\n" + ("-" * 40) + "\n")
        elif tag == "table":
            self.in_table = True
        elif tag == "tr":
            self.current_row = []
            self.row_is_header = False
        elif tag == "th":
            # header cell inside table
            self.current_cell = ""
            self.row_is_header = True
        elif tag == "td":
            self.current_cell = ""

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"h1", "h2", "h3"}:
            # pop the heading tag
            if tag in self.tag_stack:
                self.tag_stack.remove(tag)
            # append newline after heading
            self.widget.insert(tk.END, "\n")
        elif tag == "strong":
            if "bold" in self.tag_stack:
                self.tag_stack.remove("bold")
        elif tag == "p":
            self.widget.insert(tk.END, "\n")
        elif tag == "table":
            self.in_table = False
        elif tag == "tr":
            # flush accumulated row cells
            if self.current_row:
                row_text = "   ".join(self.current_row)
                tags = ("bold",) if self.row_is_header else ()
                self.widget.insert(tk.END, row_text + "\n", tags)
            self.current_row = []
            self.row_is_header = False
        elif tag in {"th", "td"}:
            if self.current_cell is not None:
                self.current_row.append(self.current_cell.strip())
                self.current_cell = None

    def handle_data(self, data: str) -> None:
        text = data
        if self.in_table and self.current_cell is not None:
            # accumulate table cell content
            self.current_cell += text
        else:
            # normal text outside of table
            tags = tuple(self.tag_stack)
            self.widget.insert(tk.END, text, tags)


class HTMLScrolledText(ScrolledText):
    """A ScrolledText widget capable of rendering a limited subset of HTML.

    Use the :meth:`set_html` method to load HTML content.  The widget
    remains read‑only unless explicitly configured otherwise.
    """

    def __init__(self, master=None, **kwargs) -> None:
        super().__init__(master, **kwargs)
        # Configure default tags for headings and bold text
        # Larger headings use a bigger font size; bold tag uses bold weight.
        self.tag_configure("h1", font=("Arial", 14, "bold"))
        self.tag_configure("h2", font=("Arial", 12, "bold"))
        self.tag_configure("h3", font=("Arial", 11, "bold"))
        self.tag_configure("bold", font=("Arial", 10, "bold"))
        # Default paragraph text uses normal font
        self.config(font=("Arial", 10))
        # Prevent user editing by default
        self.config(state="disabled")

    def set_html(self, html: str) -> None:
        """Render the provided HTML string inside the text widget.

        Existing content is cleared.  The widget will be set to
        read‑only after content is inserted.
        """
        # enable editing while inserting content
        self.config(state="normal")
        self.delete("1.0", tk.END)
        parser = _SimpleHTMLParser(self)
        parser.feed(html)
        # ensure trailing newline
        self.insert(tk.END, "\n")
        self.config(state="disabled")