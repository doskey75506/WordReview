"""Smoke tests for the module boundaries created by splitting ``ctest.py``."""

from __future__ import annotations

import importlib
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

MODULES = ["models", "files", "dictation", "spelling", "widgets", "practice", "review", "app", "ctest"]

EXPECTED_SYMBOLS = {
    "models": ["Exercise", "WrongEntry", "QuestionView", "normalise", "is_correct_answer", "select_exercise_range"],
    "files": [
        "RESOURCE_DIR",
        "WRONG_FILE",
        "WRONG_HEADER",
        "load_exercises",
        "load_wrong_entries",
        "write_wrong_entries",
        "wrong_file_label",
        "parse_wrong_time",
    ],
    "dictation": ["DictationMode"],
    "spelling": ["SpellingMode"],
    "widgets": ["DateField", "CalendarPopup"],
    "practice": ["PracticeMixin", "MODES", "mode_for_record_kind"],
    "review": ["ReviewMixin", "language_label"],
    "app": ["PracticeApp"],
    "ctest": ["PracticeApp"],
}


class ModuleBoundaryTest(unittest.TestCase):
    def test_each_module_imports_in_a_fresh_interpreter(self):
        """Catches missing symbols and import-order dependencies per module."""
        for name in MODULES:
            with self.subTest(module=name):
                result = subprocess.run(
                    [sys.executable, "-c", f"import {name}"],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 0, msg=result.stderr)

    def test_expected_symbols_exist(self):
        for name, symbols in EXPECTED_SYMBOLS.items():
            module = importlib.import_module(name)
            for symbol in symbols:
                with self.subTest(module=name, symbol=symbol):
                    self.assertTrue(hasattr(module, symbol), f"{name}.{symbol} is missing")

    def test_modules_do_not_import_the_entrypoint(self):
        for name in MODULES:
            if name == "ctest":
                continue
            source = (ROOT / f"{name}.py").read_text(encoding="utf-8")
            self.assertNotIn("import ctest", source, f"{name}.py must not import the entrypoint")

    def test_app_composes_the_expected_mixins(self):
        import tkinter as tk

        import app
        from practice import PracticeMixin
        from review import ReviewMixin

        self.assertTrue(issubclass(app.PracticeApp, PracticeMixin))
        self.assertTrue(issubclass(app.PracticeApp, ReviewMixin))
        self.assertTrue(issubclass(app.PracticeApp, tk.Tk))

    def test_modes_share_one_interface(self):
        from practice import MODES, mode_for_record_kind

        self.assertEqual(set(MODES), {"dictation", "spelling"})
        self.assertIs(mode_for_record_kind("Dictation"), MODES["dictation"])
        self.assertIs(mode_for_record_kind("spelling"), MODES["spelling"])
        for key, mode in MODES.items():
            with self.subTest(mode=key):
                for attr in ("name", "record_kind", "auto_play", "view"):
                    self.assertTrue(hasattr(mode, attr), f"{type(mode).__name__}.{attr} is missing")
                view = mode.view("English", "French", "is")
                self.assertTrue(view.prompt)
                self.assertTrue(view.instruction)

    def test_wrong_file_lives_under_resource_data(self):
        import files

        self.assertEqual(files.WRONG_FILE, files.RESOURCE_DIR / "Data" / "Wrong.csv")


if __name__ == "__main__":
    unittest.main()
