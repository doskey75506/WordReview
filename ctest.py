"""A small GUI app for dictation and spelling practice.

CSV files have a two-language header, followed by two data columns.
"""

from __future__ import annotations

import calendar
import csv
import re
import threading
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from random import shuffle
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from Reader import canonical_language, read_text_aloud

WRONG_FILE = Path(__file__).with_name("Wrong.csv")
RESOURCE_DIR = Path(__file__).with_name("Resource")
WRONG_HEADER = [
    "Practice time",
    "Practice type",
    "Primary language",
    "Secondary language",
    "Primary text",
    "Correct answer",
    "User answer",
]


@dataclass(frozen=True)
class Exercise:
    source: str
    spelling: str


@dataclass(frozen=True)
class WrongEntry:
    when: datetime | None
    kind: str
    primary_language: str
    secondary_language: str
    primary_text: str
    expected: str
    given: str


def language_label(entry: WrongEntry) -> str:
    if entry.primary_language and entry.secondary_language:
        return f"{entry.primary_language} → {entry.secondary_language}"
    return "Unknown"


def parse_wrong_time(value: str) -> datetime | None:
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def load_wrong_entries() -> list[WrongEntry]:
    """Read Wrong.csv in the current seven-column layout."""
    if not WRONG_FILE.exists():
        return []
    with open(WRONG_FILE, "r", encoding="utf-8-sig", newline="") as csv_file:
        rows = [row for row in csv.reader(csv_file) if any(cell.strip() for cell in row)]
    if not rows or rows[0] != WRONG_HEADER:
        return []
    entries: list[WrongEntry] = []
    for row in rows[1:]:
        if len(row) < 7:
            continue
        when, kind, primary_language, secondary_language, primary, expected, given = row[:7]
        entries.append(
            WrongEntry(parse_wrong_time(when), kind, primary_language, secondary_language, primary, expected, given)
        )
    return entries


def write_wrong_entries(entries: list[WrongEntry]) -> None:
    with open(WRONG_FILE, "w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(WRONG_HEADER)
        for entry in entries:
            writer.writerow(
                [
                    entry.when.strftime("%Y-%m-%d %H:%M:%S") if entry.when else "",
                    entry.kind,
                    entry.primary_language,
                    entry.secondary_language,
                    entry.primary_text,
                    entry.expected,
                    entry.given,
                ]
            )


class CalendarPopup(tk.Toplevel):
    """Month calendar that writes an ISO date into a StringVar (empty string clears)."""

    def __init__(self, master: tk.Misc, variable: tk.StringVar, on_change=None) -> None:
        super().__init__(master)
        self.title("Select date")
        self.resizable(False, False)
        self.transient(master.winfo_toplevel())
        self.variable = variable
        self.on_change = on_change
        try:
            current = datetime.strptime(variable.get(), "%Y-%m-%d").date()
        except ValueError:
            current = date.today()
        self.current = current.replace(day=1)
        self._build_header()
        self._build_grid()
        self._build_footer()
        self.geometry(f"+{master.winfo_rootx()}+{master.winfo_rooty()}")
        self._day_buttons: list[ttk.Button] = []
        self._render_days()

    def _build_header(self) -> None:
        header = ttk.Frame(self, padding=(8, 8, 8, 4))
        header.pack(fill="x")
        ttk.Button(header, text="« Y", width=4, command=lambda: self._shift(years=-1)).pack(side="left")
        ttk.Button(header, text="« M", width=4, command=lambda: self._shift(months=-1)).pack(side="left", padx=2)
        self.month_label = ttk.Label(header, text="", width=16, anchor="center")
        self.month_label.pack(side="left", expand=True)
        ttk.Button(header, text="M »", width=4, command=lambda: self._shift(months=1)).pack(side="left", padx=2)
        ttk.Button(header, text="Y »", width=4, command=lambda: self._shift(years=1)).pack(side="left")

    def _build_grid(self) -> None:
        self.grid_frame = ttk.Frame(self, padding=8)
        self.grid_frame.pack()
        for column, name in enumerate(("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su")):
            ttk.Label(self.grid_frame, text=name, width=4, anchor="center").grid(row=0, column=column, padx=1, pady=1)

    def _build_footer(self) -> None:
        footer = ttk.Frame(self, padding=(8, 0, 8, 8))
        footer.pack(fill="x")
        ttk.Button(footer, text="Today", command=self._pick_today).pack(side="left")
        ttk.Button(footer, text="Clear", command=self._clear).pack(side="left", padx=(6, 0))
        ttk.Button(footer, text="Close", command=self.destroy).pack(side="right")

    def _shift(self, months: int = 0, years: int = 0) -> None:
        month = self.current.month + months
        year = self.current.year + years + (month - 1) // 12
        self.current = date(year, (month - 1) % 12 + 1, 1)
        self._render_days()

    def _render_days(self) -> None:
        self.month_label.configure(text=self.current.strftime("%B %Y"))
        for button in self._day_buttons:
            button.destroy()
        self._day_buttons = []
        offset = self.current.weekday()
        days = calendar.monthrange(self.current.year, self.current.month)[1]
        for day in range(1, days + 1):
            slot = offset + day - 1
            button = ttk.Button(
                self.grid_frame,
                text=str(day),
                width=4,
                command=lambda chosen=day: self._pick(chosen),
            )
            button.grid(row=slot // 7 + 1, column=slot % 7, padx=1, pady=1)
            self._day_buttons.append(button)

    def _pick(self, day: int) -> None:
        self.variable.set(date(self.current.year, self.current.month, day).isoformat())
        self._notify()
        self.destroy()

    def _pick_today(self) -> None:
        self.variable.set(date.today().isoformat())
        self._notify()
        self.destroy()

    def _clear(self) -> None:
        self.variable.set("")
        self._notify()
        self.destroy()

    def _notify(self) -> None:
        if self.on_change:
            self.on_change()


class DateField(ttk.Frame):
    """Calendar-driven date input; the bound StringVar holds YYYY-MM-DD or ""."""

    def __init__(self, master: tk.Misc, variable: tk.StringVar, on_change=None) -> None:
        super().__init__(master)
        self.variable = variable
        self.on_change = on_change
        self.display = tk.StringVar()
        self._sync()
        self.button = ttk.Button(self, textvariable=self.display, command=self._open_popup)
        self.button.pack(side="left")
        ttk.Button(self, text="✕", width=2, command=self._clear).pack(side="left", padx=(4, 0))

    def _sync(self) -> None:
        self.display.set(self.variable.get() or "Not set")

    def _clear(self) -> None:
        self.variable.set("")
        self._sync()
        if self.on_change:
            self.on_change()

    def _open_popup(self) -> None:
        CalendarPopup(self, self.variable, on_change=self._changed)

    def _changed(self) -> None:
        self._sync()
        if self.on_change:
            self.on_change()


def normalise(value: str) -> str:
    """Compare answers without making Latin-only assumptions."""
    return re.sub(r"\s+", " ", value.strip()).casefold()


def is_correct_answer(given: str, expected: str, allow_alternatives: bool = False) -> bool:
    """Accept ASCII/full-width pipe-separated alternatives, such as ``to be|being``."""
    if allow_alternatives:
        return normalise(given) in {normalise(answer) for answer in re.split(r"[|｜]", expected)}
    return normalise(given) == normalise(expected)


def select_exercise_range(exercises: list[Exercise], start: int, end: int) -> list[Exercise]:
    """Return an inclusive, one-based row range after validating it."""
    if start < 1 or end < start or end > len(exercises):
        raise ValueError(f"Choose a valid range from 1 to {len(exercises)}.")
    return exercises[start - 1 : end]


def load_exercises(filename: str) -> tuple[list[Exercise], tuple[str, str]]:
    """Read a two-column CSV whose first row names the two languages."""
    exercises: list[Exercise] = []
    with open(filename, "r", encoding="utf-8-sig", newline="") as csv_file:
        rows = csv.reader(csv_file)
        try:
            header = next(rows)
        except StopIteration:
            raise ValueError("The CSV file is empty.") from None
        if len(header) < 2:
            raise ValueError("The first row must name the languages of both columns.")
        languages = (canonical_language(header[0]), canonical_language(header[1]))
        for row_number, row in enumerate(rows, start=2):
            if not row or not any(cell.strip() for cell in row):
                continue
            if len(row) < 2:
                raise ValueError(f"Row {row_number} has fewer than two columns.")
            source, spelling = row[0].strip(), row[1].strip()
            if not source or not spelling:
                raise ValueError(f"Row {row_number} has an empty source or spelling.")
            exercises.append(Exercise(source, spelling))
    if not exercises:
        raise ValueError("The CSV file contains no exercises.")
    return exercises, languages


class PracticeApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Dictation and spelling Practice")
        self.minsize(620, 500)
        self.exercises: list[Exercise] = []
        self.column_languages = ("English", "English")
        self.session_exercises: list[Exercise] = []
        self.current = 0
        self.mode = ""
        self.wrong_answers: list[tuple[Exercise, str]] = []
        self.answer = tk.StringVar()
        self.status = tk.StringVar(value="Choose a CSV file to begin.")
        self.random_order = tk.BooleanVar(value=True)
        self.second_column_primary = tk.BooleanVar(value=False)
        self.range_start = tk.StringVar(value="1")
        self.range_end = tk.StringVar(value="")
        self.range_hint = tk.StringVar(value="Load a CSV file to see the total number of rows.")
        self.review_language = tk.StringVar(value="All languages")
        self.review_from = tk.StringVar()
        self.review_to = tk.StringVar()
        self.all_wrong_entries: list[WrongEntry] = []
        self.review_removed: set[int] = set()
        self.review_queue: list[int] = []
        self.review_pos = 0
        self.review_correct = 0
        self.review_incorrect = 0
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self._build_home()

    def _clear(self) -> None:
        for child in self.winfo_children():
            child.destroy()

    def _build_home(self) -> None:
        self._clear()
        frame = ttk.Frame(self, padding=36)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Dictation and Spelling Practice", font=("Arial Unicode MS", 24, "bold")).pack(pady=(10, 12))
        ttk.Label(frame, text="1. Choose a CSV file\n2. Set the range\n3. Select Dictation or Spelling to start exercise", justify="center").pack(pady=(0, 20))
        ttk.Button(frame, text="Choose CSV File", command=self.choose_file).pack(ipadx=18, ipady=8)
        ttk.Label(frame, textvariable=self.status, wraplength=540, justify="center").pack(pady=14)
        options = ttk.LabelFrame(frame, text="Practice options", padding=(16, 8))
        options.pack(pady=(0, 10))
        ttk.Checkbutton(options, text="Random question order", variable=self.random_order).grid(row=0, column=0, sticky="w")
        ttk.Checkbutton(options, text="Reverse exercise", variable=self.second_column_primary).grid(row=1, column=0, sticky="w", pady=(5, 0))
        ttk.Label(options, text="Type the answer based on the displayed text or spoken prompt.").grid(row=2, column=0, sticky="w", pady=(5, 0))
        range_options = ttk.LabelFrame(frame, text="Exam range (loaded row numbers)", padding=(16, 8))
        range_options.pack(pady=(0, 10))
        ttk.Label(range_options, text="Start row:").grid(row=0, column=0, sticky="w")
        ttk.Entry(range_options, textvariable=self.range_start, width=8).grid(row=0, column=1, padx=(6, 18))
        ttk.Label(range_options, text="End row:").grid(row=0, column=2, sticky="w")
        ttk.Entry(range_options, textvariable=self.range_end, width=8).grid(row=0, column=3, padx=(6, 0))
        ttk.Label(range_options, textvariable=self.range_hint).grid(row=1, column=0, columnspan=4, sticky="w", pady=(6, 0))
        choices = ttk.Frame(frame)
        choices.pack(pady=10)
        self.dictation_button = ttk.Button(choices, text="Dictation", command=lambda: self.start("dictation"), state="disabled")
        self.dictation_button.grid(row=0, column=0, padx=8, ipady=8, ipadx=22)
        self.spelling_button = ttk.Button(choices, text="Spelling", command=lambda: self.start("spelling"), state="disabled")
        self.spelling_button.grid(row=0, column=1, padx=8, ipady=8, ipadx=22)
        ttk.Button(choices, text="Review Wrong Answers", command=self._open_review).grid(
            row=1, column=0, columnspan=2, pady=(12, 0), ipady=6, ipadx=12
        )

    def choose_file(self) -> None:
        filename = filedialog.askopenfilename(
            title="Choose a Two-Column CSV File",
            initialdir=RESOURCE_DIR,
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not filename:
            return
        try:
            self.exercises, self.column_languages = load_exercises(filename)
        except (OSError, UnicodeDecodeError, csv.Error, ValueError) as error:
            self.exercises = []
            messagebox.showerror("Unable to Read File", f"The first row must name two supported languages, followed by two data columns.\n\n{error}")
            return
        self.status.set(f"Loaded {len(self.exercises)} exercise(s): {Path(filename).name}")
        self.range_start.set("1")
        self.range_end.set(str(len(self.exercises)))
        self.range_hint.set(f"Total loaded rows: {len(self.exercises)}. Choose a range from 1 to {len(self.exercises)}.")
        self.dictation_button.configure(state="normal")
        self.spelling_button.configure(state="normal")

    def start(self, mode: str) -> None:
        try:
            start, end = int(self.range_start.get()), int(self.range_end.get())
            self.session_exercises = select_exercise_range(self.exercises, start, end)
        except ValueError as error:
            messagebox.showerror("Invalid Exam Range", str(error))
            return
        self.mode, self.current, self.wrong_answers = mode, 0, []
        if self.random_order.get():
            shuffle(self.session_exercises)
        self._build_question()

    def primary_text(self, item: Exercise) -> str:
        return item.spelling if self.second_column_primary.get() else item.source

    def secondary_text(self, item: Exercise) -> str:
        return item.source if self.second_column_primary.get() else item.spelling

    def primary_language(self) -> str:
        return self.column_languages[1] if self.second_column_primary.get() else self.column_languages[0]

    def secondary_language(self) -> str:
        return self.column_languages[0] if self.second_column_primary.get() else self.column_languages[1]

    def _build_question(self) -> None:
        self._clear()
        item = self.session_exercises[self.current]
        frame = ttk.Frame(self, padding=32)
        frame.pack(fill="both", expand=True)
        label = "Dictation" if self.mode == "dictation" else "Spelling Practice"
        ttk.Label(frame, text=label, font=("Arial Unicode MS", 20, "bold")).pack(anchor="w")
        ttk.Label(frame, text=f"Question {self.current + 1} of {len(self.session_exercises)}").pack(anchor="w", pady=(4, 22))
        primary = self.primary_text(item)
        secondary = self.secondary_text(item)
        primary_language = self.primary_language()
        secondary_language = self.secondary_language()
        if self.mode == "spelling":
            prompt = f"{primary_language} text"
            display = primary
            instruction = f"Based on the {primary_language} text, write the {secondary_language} text:"
        else:
            prompt = f"{secondary_language} dictation"
            display = f"Listen to the {secondary_language} pronunciation, then type the {secondary_language} text."
            instruction = f"Based on the {secondary_language} pronunciation, write the {secondary_language} text:"
        ttk.Label(frame, text=prompt).pack(anchor="w")
        ttk.Label(frame, text=display, font=("Arial Unicode MS", 18), wraplength=550).pack(anchor="w", pady=(5, 20))
        if self.mode == "dictation":
            ttk.Button(frame, text="▶ Play Text to Write", command=lambda: self.speak(secondary, secondary_language)).pack(anchor="w", pady=(0, 16))
            self.after(250, lambda: self.speak(secondary, secondary_language))
        ttk.Label(frame, text=instruction).pack(anchor="w")
        entry = ttk.Entry(frame, textvariable=self.answer, font=("Arial Unicode MS", 16))
        entry.pack(fill="x", pady=(5, 16))
        entry.focus_set()
        entry.bind("<Return>", lambda _event: self.submit())
        ttk.Button(frame, text="Submit Answer", command=self.submit).pack(anchor="e", ipadx=15, ipady=5)
        ttk.Button(frame, text="Back to Home", command=self._build_home).pack(anchor="w", pady=(18, 0))
        self.answer.set("")

    def speak(self, text: str, language: str) -> None:
        """Speech runs in a worker so it never freezes the answer form."""
        threading.Thread(target=read_text_aloud, args=(text, language), daemon=True).start()

    def submit(self) -> None:
        item = self.session_exercises[self.current]
        given = self.answer.get()
        expected = self.secondary_text(item)
        # Either CSV column may contain alternatives, including in dictation.
        if not is_correct_answer(given, expected, allow_alternatives=True):
            self.wrong_answers.append((item, given.strip()))
            messagebox.showinfo("Answer Recorded", f"Correct answer:\n{expected}")
        self.current += 1
        if self.current < len(self.session_exercises):
            self._build_question()
        else:
            self.finish()

    def finish(self) -> None:
        if self.wrong_answers:
            self.save_wrong_answers()
            result = f"Practice complete. {len(self.wrong_answers)} incorrect answer(s) were saved to:\n{WRONG_FILE.name}"
        else:
            result = "Practice complete. All answers were correct!"
        messagebox.showinfo("Complete", result)
        self._build_home()

    def save_wrong_answers(self) -> None:
        entries = load_wrong_entries()
        when = datetime.now()
        kind = "Dictation" if self.mode == "dictation" else "spelling"
        for item, given in self.wrong_answers:
            entries.append(
                WrongEntry(
                    when,
                    kind,
                    self.primary_language(),
                    self.secondary_language(),
                    self.primary_text(item),
                    self.secondary_text(item),
                    given,
                )
            )
        write_wrong_entries(entries)

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
        self._clear()
        frame = ttk.Frame(self, padding=32)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Wrong Answer Review", font=("Arial Unicode MS", 20, "bold")).pack(anchor="w")
        ttk.Label(frame, text=f"Question {self.review_pos + 1} of {len(self.review_queue)}").pack(
            anchor="w", pady=(4, 18)
        )
        is_dictation = entry.kind.casefold() == "dictation"
        if is_dictation:
            prompt = f"{entry.secondary_language} dictation"
            instruction = (
                f"Based on the {entry.secondary_language} pronunciation, write the {entry.secondary_language} text:"
            )
        else:
            prompt = f"{entry.primary_language} text"
            instruction = f"Based on the {entry.primary_language} text, write the {entry.secondary_language} text:"
        ttk.Label(frame, text=prompt).pack(anchor="w")
        if not is_dictation:
            ttk.Label(frame, text=entry.primary_text, font=("Arial Unicode MS", 18), wraplength=550).pack(
                anchor="w", pady=(5, 14)
            )
        ttk.Label(frame, text=f"Your previous answer: {entry.given or '(blank)'}").pack(anchor="w", pady=(0, 10))
        if is_dictation:
            ttk.Button(
                frame, text="▶ Play Audio", command=lambda: self.speak(entry.expected, entry.secondary_language)
            ).pack(anchor="w", pady=(0, 12))
            self.after(250, lambda: self.speak(entry.expected, entry.secondary_language))
        ttk.Label(frame, text=instruction).pack(anchor="w")
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
            f"Review complete. {self.review_correct} answer(s) are now correct and were removed from {WRONG_FILE.name}."
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


if __name__ == "__main__":
    PracticeApp().mainloop()
