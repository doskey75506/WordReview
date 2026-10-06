"""Practice flow: exam range, the question screen, submitting and saving."""

from __future__ import annotations

from datetime import datetime
from random import shuffle

from tkinter import messagebox, ttk

from dictation import DictationMode
from files import load_wrong_entries, wrong_file_label, write_wrong_entries
from models import Exercise, WrongEntry, is_correct_answer, select_exercise_range
from spelling import SpellingMode

DICTATION = DictationMode()
SPELLING = SpellingMode()
MODES = {"dictation": DICTATION, "spelling": SPELLING}


def mode_for_record_kind(kind: str):
    """Map a Wrong.csv practice type back to its mode object."""
    return DICTATION if kind.casefold() == "dictation" else SPELLING


class PracticeMixin:
    """Practice screens; expects the PracticeApp state defined in ``app.py``."""

    def primary_text(self, item: Exercise) -> str:
        return item.spelling if self.second_column_primary.get() else item.source

    def secondary_text(self, item: Exercise) -> str:
        return item.source if self.second_column_primary.get() else item.spelling

    def primary_language(self) -> str:
        return self.column_languages[1] if self.second_column_primary.get() else self.column_languages[0]

    def secondary_language(self) -> str:
        return self.column_languages[0] if self.second_column_primary.get() else self.column_languages[1]

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

    def _build_question(self) -> None:
        self._clear()
        item = self.session_exercises[self.current]
        frame = ttk.Frame(self, padding=32)
        frame.pack(fill="both", expand=True)
        mode = MODES[self.mode]
        view = mode.view(self.primary_language(), self.secondary_language(), self.primary_text(item))
        secondary = self.secondary_text(item)
        secondary_language = self.secondary_language()
        ttk.Label(frame, text=mode.name, font=("Arial Unicode MS", 20, "bold")).pack(anchor="w")
        ttk.Label(frame, text=f"Question {self.current + 1} of {len(self.session_exercises)}").pack(
            anchor="w", pady=(4, 22)
        )
        ttk.Label(frame, text=view.prompt).pack(anchor="w")
        if view.display:
            ttk.Label(frame, text=view.display, font=("Arial Unicode MS", 18), wraplength=550).pack(
                anchor="w", pady=(5, 20)
            )
        if mode.auto_play:
            ttk.Button(
                frame, text="▶ Play Text to Write", command=lambda: self.speak(secondary, secondary_language)
            ).pack(anchor="w", pady=(0, 16))
            self.after(250, lambda: self.speak(secondary, secondary_language))
        ttk.Label(frame, text=view.instruction).pack(anchor="w")
        entry = ttk.Entry(frame, textvariable=self.answer, font=("Arial Unicode MS", 16))
        entry.pack(fill="x", pady=(5, 16))
        entry.focus_set()
        entry.bind("<Return>", lambda _event: self.submit())
        ttk.Button(frame, text="Submit Answer", command=self.submit).pack(anchor="e", ipadx=15, ipady=5)
        ttk.Button(frame, text="Back to Home", command=self._build_home).pack(anchor="w", pady=(18, 0))
        self.answer.set("")

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
            result = f"Practice complete. {len(self.wrong_answers)} incorrect answer(s) were saved to:\n{wrong_file_label()}"
        else:
            result = "Practice complete. All answers were correct!"
        messagebox.showinfo("Complete", result)
        self._build_home()

    def save_wrong_answers(self) -> None:
        entries = load_wrong_entries()
        when = datetime.now()
        kind = MODES[self.mode].record_kind
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
