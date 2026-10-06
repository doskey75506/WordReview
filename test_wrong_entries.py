"""Behaviour of the wrong-answer CSV store: cleanup, rebuild and round-trip."""

from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

import files
from models import WrongEntry

HEADER_ROW = ",".join(files.WRONG_HEADER)
GOOD_ONE = "2026-09-16 10:05:00,spelling,English,French,grand,big,gros"
GOOD_TWO = "2026-10-01 09:00:00,dictation,English,French,hello,bonjour,banojour"

MALFORMED_ROWS = [
    "too,few",  # wrong column count
    "2026-09-16 10:05:00,spelling,English,French,a,b,c,extra",  # eight columns
    "not-a-time,spelling,English,French,a,b,c",  # bad timestamp
    "2026-09-16 10:05:00,Reading,English,French,a,b,c",  # unknown practice type
    "2026-09-16 10:05:00,spelling,English,German,a,b,c",  # unsupported language
    "2026-09-16 10:05:00,spelling,,French,a,b,c",  # empty language
    "2026-09-16 10:05:00,spelling,English,French,a,,c",  # empty correct answer
]


class WrongEntriesTest(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.wrong = Path(tmp.name) / "Data" / "Wrong.csv"
        patcher = patch.object(files, "WRONG_FILE", self.wrong)
        patcher.start()
        self.addCleanup(patcher.stop)

    def write_raw(self, text: str) -> None:
        self.wrong.parent.mkdir(parents=True, exist_ok=True)
        self.wrong.write_text(text, encoding="utf-8")

    def disk_rows(self) -> list[list[str]]:
        with open(self.wrong, encoding="utf-8-sig", newline="") as handle:
            return list(csv.reader(handle))

    # --- rebuild from zero -------------------------------------------------

    def test_missing_file_reads_empty_without_creating_it(self):
        self.assertEqual(files.load_wrong_entries(), [])
        self.assertFalse(self.wrong.exists())

    def test_emptied_file_is_rebuilt_with_header_only(self):
        self.write_raw("")
        self.assertEqual(files.load_wrong_entries(), [])
        self.assertEqual(self.disk_rows(), [files.WRONG_HEADER])

    def test_write_creates_missing_parent_directories(self):
        self.assertFalse(self.wrong.parent.exists())
        entry = WrongEntry(
            datetime(2026, 10, 6, 12, 0, 0), "spelling", "English", "French", "is", "est", "wrong"
        )
        files.write_wrong_entries([entry])
        self.assertTrue(self.wrong.exists())
        self.assertEqual(files.load_wrong_entries(), [entry])

    def test_new_file_starts_with_utf8_bom(self):
        files.write_wrong_entries([])
        self.assertEqual(self.wrong.read_bytes()[:3], b"\xef\xbb\xbf")

    # --- cleanup of malformed rows ----------------------------------------

    def test_legacy_five_column_rows_are_purged(self):
        self.write_raw(
            "Practice time,Practice type,Primary text,Correct answer,User answer\n"
            "2026-09-16 10:05:00,spelling,grand,big,\n"
        )
        self.assertEqual(files.load_wrong_entries(), [])
        self.assertEqual(self.disk_rows(), [files.WRONG_HEADER])

    def test_malformed_rows_are_dropped_and_valid_rows_kept_verbatim(self):
        self.write_raw("\n".join([HEADER_ROW, GOOD_ONE, *MALFORMED_ROWS, GOOD_TWO]) + "\n")
        entries = files.load_wrong_entries()
        self.assertEqual([entry.primary_text for entry in entries], ["grand", "hello"])
        self.assertEqual(
            self.disk_rows(),
            [files.WRONG_HEADER, GOOD_ONE.split(","), GOOD_TWO.split(",")],
        )

    def test_missing_header_is_restored_keeping_valid_rows(self):
        self.write_raw(GOOD_ONE + "\n")
        entries = files.load_wrong_entries()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].expected, "big")
        self.assertEqual(self.disk_rows(), [files.WRONG_HEADER, GOOD_ONE.split(",")])

    def test_case_variant_kind_and_blank_user_answer_are_valid(self):
        self.write_raw("\n".join([HEADER_ROW, "2026-09-16 10:05:00,dictation,English,French,hello,bonjour,"]) + "\n")
        entries = files.load_wrong_entries()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].given, "")

    # --- hand edits and round-trips ----------------------------------------

    def test_valid_hand_edited_row_survives_unchanged(self):
        self.write_raw("\n".join([HEADER_ROW, GOOD_ONE]) + "\n")
        (entry,) = files.load_wrong_entries()
        self.assertEqual(
            (
                entry.when,
                entry.kind,
                entry.primary_language,
                entry.secondary_language,
                entry.primary_text,
                entry.expected,
                entry.given,
            ),
            (datetime(2026, 9, 16, 10, 5, 0), "spelling", "English", "French", "grand", "big", "gros"),
        )

    def test_clean_file_is_not_rewritten_on_load(self):
        self.write_raw("\n".join([HEADER_ROW, GOOD_ONE]) + "\n")
        before = self.wrong.stat().st_mtime_ns
        files.load_wrong_entries()
        self.assertEqual(self.wrong.stat().st_mtime_ns, before)

    def test_round_trip_preserves_every_field(self):
        entry = WrongEntry(
            datetime(2026, 10, 6, 9, 30, 15), "spelling", "French", "English", "bonjour", "hello", "hi"
        )
        files.write_wrong_entries([entry])
        self.assertEqual(files.load_wrong_entries(), [entry])

    def test_wrong_file_label_falls_back_outside_the_repo(self):
        self.assertEqual(files.wrong_file_label(), str(self.wrong))


if __name__ == "__main__":
    unittest.main()
