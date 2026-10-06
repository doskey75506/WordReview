"""Wrong-answer review: filtering the list, deleting rows and re-testing them."""

from __future__ import annotations

from datetime import date, datetime

from tkinter import messagebox, ttk

from files import load_wrong_entries, wrong_file_label, write_wrong_entries
from models import WrongEntry, is_correct_answer
from practice import mode_for_record_kind
from widgets import DateField


def language_label(entry: WrongEntry) -> str:
    if entry.primary_language and entry.secondary_language:
        return f"{entry.primary_language} → {entry.secondary_language}"
    return "Unknown"


class ReviewMixin:
    """Review screens; expects the PracticeApp state defined in ``app.py``."""

    def _open_review(self) -> None:
        self.all_wrong_entries = load_wrong_entries()
        if not self.all_wrong_entries:
            messagebox.showinfo("No Wrong Answers", "There are no wrong answers recorded yet.")
            return
        self.review_removed = set()
        self._build_review()

    def _build_review(self) -> None:
        self._clear()
        frame = ttk.Frame(self, padding=36)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Wrong Answer Review", font=("Arial Unicode MS", 20, "bold")).pack(anchor="w")
        filters = ttk.LabelFrame(frame, text="Filter mistakes", padding=(16, 8))
        filters.pack(fill="x", pady=(12, 10))
        ttk.Label(filters, text="Language:").grid(row=0, column=0, sticky="w")
        language_options = self._language_options()
        if self.review_language.get() not in language_options:
            self.review_language.set(language_options[0])
        language_box = ttk.Combobox(
            filters,
            textvariable=self.review_language,
            values=language_options,
            state="readonly",
            width=22,
        )
        language_box.grid(row=0, column=1, padx=(6, 18), sticky="w")
        language_box.bind("<<ComboboxSelected>>", lambda _event: self._refresh_review_list())
        ttk.Label(filters, text="From date:").grid(row=0, column=2, sticky="w")
        self.date_from_field = DateField(filters, self.review_from, on_change=self._refresh_review_list)
        self.date_from_field.grid(row=0, column=3, padx=(6, 18), sticky="w")
        ttk.Label(filters, text="To date:").grid(row=0, column=4, sticky="w")
        self.date_to_field = DateField(filters, self.review_to, on_change=self._refresh_review_list)
        self.date_to_field.grid(row=0, column=5, padx=(6, 0), sticky="w")
        ttk.Label(filters, text="Pick dates from the calendar; leave them unset for no bound.").grid(
            row=1, column=0, columnspan=6, sticky="w", pady=(6, 0)
        )
        self.review_tree = ttk.Treeview(
            frame,
            columns=("time", "type", "language", "prompt", "answer", "given"),
            show="headings",
            selectmode="extended",
            height=10,
        )
        headings = [
            ("time", "Time", 140),
            ("type", "Practice", 80),
            ("language", "Language", 140),
            ("prompt", "Question", 150),
            ("answer", "Correct answer", 150),
            ("given", "Your answer", 120),
        ]
        for key, title, width in headings:
            self.review_tree.heading(key, text=title)
            self.review_tree.column(key, width=width, anchor="w")
        self.review_tree.pack(fill="both", expand=True, pady=(0, 10))
        actions = ttk.Frame(frame)
        actions.pack(fill="x")
        ttk.Button(actions, text="Start Review", command=self._start_review).pack(side="left", ipadx=12, ipady=6)
        ttk.Button(actions, text="Delete Selected", command=self._delete_selected).pack(
            side="left", padx=(10, 0), ipadx=12, ipady=6
        )
        ttk.Button(actions, text="Back to Home", command=self._build_home).pack(side="right", ipadx=12, ipady=6)
        self._refresh_review_list()

    def _language_options(self) -> list[str]:
        return ["All languages", *sorted({language_label(entry) for entry in self.all_wrong_entries})]

    def _parse_review_date(self, value: str, label: str) -> date | None:
        value = value.strip()
        if not value:
            return None
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError(f"{label} must use YYYY-MM-DD.") from None

    def _filtered_indices(self) -> list[int]:
        """Visible row indices under the current filter, newest mistakes first."""
        language = self.review_language.get()
        date_from = self._parse_review_date(self.review_from.get(), "From date")
        date_to = self._parse_review_date(self.review_to.get(), "To date")
        if date_from and date_to and date_to < date_from:
            raise ValueError("The to date is before the from date.")
        indices = []
        for index, entry in enumerate(self.all_wrong_entries):
            if index in self.review_removed:
                continue
            if language != "All languages" and language_label(entry) != language:
                continue
            if date_from or date_to:
                if entry.when is None:
                    continue
                if date_from and entry.when.date() < date_from:
                    continue
                if date_to and entry.when.date() > date_to:
                    continue
            indices.append(index)
        indices.sort(key=lambda index: self.all_wrong_entries[index].when or datetime.min, reverse=True)
        return indices

    def _refresh_review_list(self) -> None:
        try:
            indices = self._filtered_indices()
        except ValueError as error:
            messagebox.showerror("Invalid Filter", str(error))
            return
        self.review_tree.delete(*self.review_tree.get_children())
        for index in indices:
            entry = self.all_wrong_entries[index]
            when = entry.when.strftime("%Y-%m-%d %H:%M:%S") if entry.when else "unknown"
            self.review_tree.insert(
                "",
                "end",
                iid=str(index),
                values=(when, entry.kind, language_label(entry), entry.primary_text, entry.expected, entry.given),
            )

    def _save_review_removals(self) -> None:
        write_wrong_entries(
            [entry for index, entry in enumerate(self.all_wrong_entries) if index not in self.review_removed]
        )

    def _delete_selected(self) -> None:
        selected = [int(iid) for iid in self.review_tree.selection()]
        if not selected:
            messagebox.showinfo("Nothing Selected", "Select one or more mistakes in the list first.")
            return
        self.review_removed.update(selected)
        self._save_review_removals()
        self._refresh_review_list()
        if not self._filtered_indices_unchecked():
            messagebox.showinfo("No Wrong Answers", "All wrong answers have been removed.")
            self._build_home()

    def _filtered_indices_unchecked(self) -> list[int]:
        try:
            return self._filtered_indices()
        except ValueError:
            return []

    def _start_review(self) -> None:
        selected = [int(iid) for iid in self.review_tree.selection()]
        if selected:
            self.review_queue = selected
        else:
            self.review_queue = self._filtered_indices_unchecked()
        if not self.review_queue:
            messagebox.showinfo("Nothing to Review", "No mistakes match the current filter.")
            return
        self.review_pos = 0
        self.review_correct = 0
        self.review_incorrect = 0
        self._build_review_question()

    def _build_review_question(self) -> None:
        if self.review_pos >= len(self.review_queue):
            self._review_finish()
            return
        entry = self.all_wrong_entries[self.review_queue[self.review_pos]]
        mode = mode_for_record_kind(entry.kind)
        view = mode.view(
            entry.primary_language, entry.secondary_language, entry.primary_text, listen_hint=False
        )
        self._clear()
        frame = ttk.Frame(self, padding=32)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Wrong Answer Review", font=("Arial Unicode MS", 20, "bold")).pack(anchor="w")
        ttk.Label(frame, text=f"Question {self.review_pos + 1} of {len(self.review_queue)}").pack(
            anchor="w", pady=(4, 18)
        )
        ttk.Label(frame, text=view.prompt).pack(anchor="w")
        if view.display:
            ttk.Label(frame, text=view.display, font=("Arial Unicode MS", 18), wraplength=550).pack(
                anchor="w", pady=(5, 14)
            )
        ttk.Label(frame, text=f"Your previous answer: {entry.given or '(blank)'}").pack(anchor="w", pady=(0, 10))
        if mode.auto_play:
            ttk.Button(
                frame, text="▶ Play Audio", command=lambda: self.speak(entry.expected, entry.secondary_language)
            ).pack(anchor="w", pady=(0, 12))
            self.after(250, lambda: self.speak(entry.expected, entry.secondary_language))
        ttk.Label(frame, text=view.instruction).pack(anchor="w")
        answer_entry = ttk.Entry(frame, textvariable=self.answer, font=("Arial Unicode MS", 16))
        answer_entry.pack(fill="x", pady=(5, 16))
        answer_entry.focus_set()
        answer_entry.bind("<Return>", lambda _event: self.review_submit())
        ttk.Button(frame, text="Submit Answer", command=self.review_submit).pack(anchor="e", ipadx=15, ipady=5)
        ttk.Button(frame, text="Back to Review List", command=self._build_review).pack(anchor="w", pady=(18, 0))
        self.answer.set("")

    def review_submit(self) -> None:
        index = self.review_queue[self.review_pos]
        entry = self.all_wrong_entries[index]
        if is_correct_answer(self.answer.get(), entry.expected, allow_alternatives=True):
            # A corrected mistake leaves the wrong-answer file.
            self.review_correct += 1
            self.review_removed.add(index)
            self._save_review_removals()
        else:
            self.review_incorrect += 1
            messagebox.showinfo("Still Incorrect", f"Correct answer:\n{entry.expected}")
        self.review_pos += 1
        if self.review_pos < len(self.review_queue):
            self._build_review_question()
        else:
            self._review_finish()

    def _review_finish(self) -> None:
        summary = [
            f"Review complete. {self.review_correct} answer(s) are now correct and were removed from {wrong_file_label()}."
        ]
        if self.review_incorrect:
            summary.append(f"{self.review_incorrect} answer(s) are still incorrect and stay in the list.")
        messagebox.showinfo("Review Complete", "\n".join(summary))
        self.all_wrong_entries = load_wrong_entries()
        self.review_removed = set()
        if self.all_wrong_entries:
            self._build_review()
        else:
            self._build_home()
