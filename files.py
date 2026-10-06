"""CSV file management: exercise input files and the wrong-answer store."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from Reader import canonical_language
from models import Exercise, WrongEntry

RESOURCE_DIR = Path(__file__).with_name("Resource")
WRONG_FILE = RESOURCE_DIR / "Data" / "Wrong.csv"
WRONG_HEADER = [
    "Practice time",
    "Practice type",
    "Primary language",
    "Secondary language",
    "Primary text",
    "Correct answer",
    "User answer",
]


def wrong_file_label() -> str:
    """Project-relative wrong-answer path for user-facing messages."""
    try:
        return str(WRONG_FILE.relative_to(Path(__file__).parent))
    except ValueError:
        return str(WRONG_FILE)


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


def parse_wrong_time(value: str) -> datetime | None:
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def _entry_from_row(row: list[str]) -> WrongEntry | None:
    """Return the entry of a well-formed row, or None if the row is malformed."""
    if len(row) != 7:
        return None
    when, kind, primary_language, secondary_language, primary, expected, given = row
    parsed_when = parse_wrong_time(when)
    if parsed_when is None:
        return None
    if kind.strip().casefold() not in ("dictation", "spelling"):
        return None
    if not primary.strip() or not expected.strip():
        return None
    for language in (primary_language, secondary_language):
        if not language.strip():
            return None
        try:
            canonical_language(language)
        except ValueError:
            return None
    return WrongEntry(parsed_when, kind, primary_language, secondary_language, primary, expected, given)


def load_wrong_entries() -> list[WrongEntry]:
    """Read Wrong.csv, tolerating hand edits and an emptied or deleted file.

    Malformed rows (wrong column count, bad timestamp, unknown practice
    type, empty or unsupported language, empty question or answer) are
    dropped, a missing header is restored and an existing but empty file is
    rebuilt with just the header; whenever anything was cleaned the file is
    rewritten on the spot.
    """
    if not WRONG_FILE.exists():
        return []
    with open(WRONG_FILE, "r", encoding="utf-8-sig", newline="") as csv_file:
        rows = [row for row in csv.reader(csv_file) if any(cell.strip() for cell in row)]
    if not rows:
        write_wrong_entries([])
        return []
    has_header = rows[0] == WRONG_HEADER
    entries: list[WrongEntry] = []
    needs_cleanup = not has_header
    for row in rows[1:] if has_header else rows:
        entry = _entry_from_row(row)
        if entry is None:
            needs_cleanup = True
            continue
        entries.append(entry)
    if needs_cleanup:
        write_wrong_entries(entries)
    return entries


def write_wrong_entries(entries: list[WrongEntry]) -> None:
    WRONG_FILE.parent.mkdir(parents=True, exist_ok=True)
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
