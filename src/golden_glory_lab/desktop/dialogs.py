"""Presentation-only bounded Tkinter dialogs."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from typing import Any

from golden_glory_lab.build_state import MANUAL_ENTRY_LIMITS
from golden_glory_lab.pob_import import DEFAULT_IMPORT_LIMITS


class ShareCodeDialog(simpledialog.Dialog):
    def __init__(self, parent: tk.Misc) -> None:
        self.value: str | None = None
        self._text: tk.Text
        self._count: ttk.Label
        super().__init__(parent, title="Paste Path of Building share code")

    def body(self, master: tk.Misc) -> tk.Widget:
        limit = DEFAULT_IMPORT_LIMITS.maxShareCodeCharacters
        ttk.Label(
            master,
            text=(
                "Paste a PoB share code. Input above "
                f"{limit:,} characters is rejected before import."
            ),
            wraplength=620,
        ).grid(row=0, column=0, sticky="w", padx=8, pady=(8, 4))
        frame = ttk.Frame(master)
        frame.grid(row=1, column=0, sticky="nsew", padx=8)
        master.grid_rowconfigure(1, weight=1)
        master.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        self._text = tk.Text(frame, width=80, height=14, wrap="char", undo=True)
        scroll = ttk.Scrollbar(frame, orient="vertical", command=self._text.yview)
        self._text.configure(yscrollcommand=scroll.set)
        self._text.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        self._count = ttk.Label(master, text="0 characters")
        self._count.grid(row=2, column=0, sticky="e", padx=8, pady=(3, 8))
        self._text.bind("<KeyRelease>", self._update_count)
        return self._text

    def _update_count(self, _event: tk.Event[Any] | None = None) -> None:
        count = len(self._text.get("1.0", "end-1c"))
        self._count.configure(text=f"{count:,} characters")

    def validate(self) -> bool:
        value = self._text.get("1.0", "end-1c")
        if not value:
            messagebox.showerror("Share code required", "Paste a share code first.", parent=self)
            return False
        limit = DEFAULT_IMPORT_LIMITS.maxShareCodeCharacters
        if len(value) > limit:
            messagebox.showerror(
                "Share code too long",
                f"The pasted value exceeds the {limit:,}-character limit.",
                parent=self,
            )
            return False
        return True

    def apply(self) -> None:
        self.value = self._text.get("1.0", "end-1c")


class ManualEntryDialog(simpledialog.Dialog):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        title: str,
        initial: dict[str, str] | None = None,
    ) -> None:
        self.value: dict[str, str] | None = None
        self._initial = initial or {}
        self._slot: ttk.Entry
        self._raw: tk.Text
        self._note: tk.Text
        super().__init__(parent, title=title)

    def body(self, master: tk.Misc) -> tk.Widget:
        master.grid_columnconfigure(1, weight=1)
        ttk.Label(master, text="Slot label").grid(
            row=0, column=0, sticky="nw", padx=8, pady=8
        )
        self._slot = ttk.Entry(master, width=52)
        self._slot.grid(row=0, column=1, sticky="ew", padx=(0, 8), pady=8)
        self._slot.insert(0, self._initial.get("slotLabel", ""))

        ttk.Label(master, text="Exact raw or descriptive text").grid(
            row=1, column=0, sticky="nw", padx=8, pady=8
        )
        raw_frame = ttk.Frame(master)
        raw_frame.grid(row=1, column=1, sticky="nsew", padx=(0, 8), pady=8)
        raw_frame.grid_columnconfigure(0, weight=1)
        raw_frame.grid_rowconfigure(0, weight=1)
        self._raw = tk.Text(raw_frame, width=62, height=12, wrap="none", undo=True)
        raw_y = ttk.Scrollbar(raw_frame, orient="vertical", command=self._raw.yview)
        raw_x = ttk.Scrollbar(raw_frame, orient="horizontal", command=self._raw.xview)
        self._raw.configure(yscrollcommand=raw_y.set, xscrollcommand=raw_x.set)
        self._raw.grid(row=0, column=0, sticky="nsew")
        raw_y.grid(row=0, column=1, sticky="ns")
        raw_x.grid(row=1, column=0, sticky="ew")
        self._raw.insert("1.0", self._initial.get("rawText", ""))
        self._raw.bind("<Return>", self._insert_text_newline)

        ttk.Label(master, text="Optional note").grid(
            row=2, column=0, sticky="nw", padx=8, pady=8
        )
        self._note = tk.Text(master, width=62, height=4, wrap="word", undo=True)
        self._note.grid(row=2, column=1, sticky="ew", padx=(0, 8), pady=8)
        self._note.insert("1.0", self._initial.get("note", ""))
        self._note.bind("<Return>", self._insert_text_newline)
        return self._slot

    @staticmethod
    def _insert_text_newline(event: tk.Event[Any]) -> str:
        event.widget.insert("insert", "\n")
        return "break"

    def validate(self) -> bool:
        slot = self._slot.get()
        raw = self._raw.get("1.0", "end-1c")
        note = self._note.get("1.0", "end-1c")
        errors = []
        if not slot:
            errors.append("Slot label is required.")
        if len(slot) > MANUAL_ENTRY_LIMITS["maxSlotLabelCharacters"]:
            errors.append("Slot label is too long.")
        if not raw:
            errors.append("Raw or descriptive text is required.")
        if len(raw) > MANUAL_ENTRY_LIMITS["maxRawTextCharacters"]:
            errors.append("Raw text is too long.")
        if len(note) > MANUAL_ENTRY_LIMITS["maxNoteCharacters"]:
            errors.append("Note is too long.")
        if errors:
            messagebox.showerror("Manual entry", "\n".join(errors), parent=self)
            return False
        return True

    def apply(self) -> None:
        self.value = {
            "slotLabel": self._slot.get(),
            "rawText": self._raw.get("1.0", "end-1c"),
            "note": self._note.get("1.0", "end-1c"),
        }
