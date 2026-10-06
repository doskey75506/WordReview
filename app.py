"""Main application window: state, the home screen and screen switching."""

from __future__ import annotations

import csv
from pathlib import Path
import threading

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from Reader import read_text_aloud
from files import RESOURCE_DIR, load_exercises
from models import Exercise, WrongEntry
from practice import PracticeMixin
from review import ReviewMixin


class PracticeApp(PracticeMixin, ReviewMixin, tk.Tk):
    """Dictation and Spelling Practice.

    CSV files have a two-language header, followed by two data columns.
    """

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

    def speak(self, text: str, language: str) -> None:
        """Speech runs in a worker so it never freezes the answer form."""
        threading.Thread(target=read_text_aloud, args=(text, language), daemon=True).start()
