"""A small GUI app for dictation and spelling practice.

CSV files have a two-language header, followed by two data columns.
"""

from __future__ import annotations

import csv
import re
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from random import shuffle
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from Reader import canonical_language, read_text_aloud

WRONG_FILE = Path(__file__).with_name("Wrong.csv")
RESOURCE_DIR = Path(__file__).with_name("Resource")


@dataclass(frozen=True)
class Exercise:
    source: str
    spelling: str


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
        ttk.Label(options, text="By default, try to type out words in the right column").grid(row=2, column=0, sticky="w", pady=(5, 0))
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
            prompt = f"{primary_language} dictation"
            display = f"Listen to the {primary_language} pronunciation, then type the {primary_language} text."
            instruction = f"Based on the {primary_language} pronunciation, write the {primary_language} text:"
        ttk.Label(frame, text=prompt).pack(anchor="w")
        ttk.Label(frame, text=display, font=("Arial Unicode MS", 18), wraplength=550).pack(anchor="w", pady=(5, 20))
        if self.mode == "dictation":
            ttk.Button(frame, text="▶ Play Primary Text", command=lambda: self.speak(self.primary_text(item))).pack(anchor="w", pady=(0, 16))
            self.after(250, lambda: self.speak(self.primary_text(item)))
        ttk.Label(frame, text=instruction).pack(anchor="w")
        entry = ttk.Entry(frame, textvariable=self.answer, font=("Arial Unicode MS", 16))
        entry.pack(fill="x", pady=(5, 16))
        entry.focus_set()
        entry.bind("<Return>", lambda _event: self.submit())
        ttk.Button(frame, text="Submit Answer", command=self.submit).pack(anchor="e", ipadx=15, ipady=5)
        ttk.Button(frame, text="Back to Home", command=self._build_home).pack(anchor="w", pady=(18, 0))
        self.answer.set("")

    def speak(self, text: str) -> None:
        """Speech runs in a worker so it never freezes the answer form."""
        threading.Thread(target=read_text_aloud, args=(text, self.primary_language()), daemon=True).start()

    def submit(self) -> None:
        item = self.session_exercises[self.current]
        given = self.answer.get()
        expected = self.primary_text(item) if self.mode == "dictation" else self.secondary_text(item)
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
        new_file = not WRONG_FILE.exists()
        with open(WRONG_FILE, "a", encoding="utf-8-sig" if new_file else "utf-8", newline="") as file:
            writer = csv.writer(file)
            if new_file:
                writer.writerow(["Practice time", "Practice type", "Primary text", "Correct answer", "User answer"])
            kind = "Dictation" if self.mode == "dictation" else "spelling"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for item, given in self.wrong_answers:
                expected = self.primary_text(item) if self.mode == "dictation" else self.secondary_text(item)
                writer.writerow([timestamp, kind, self.primary_text(item), expected, given])


if __name__ == "__main__":
    PracticeApp().mainloop()
