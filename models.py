"""Domain data and answer checking shared by every screen."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re


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


@dataclass(frozen=True)
class QuestionView:
    """What a practice/review screen shows for one question."""

    prompt: str
    display: str  # empty string means "show no text under the prompt"
    instruction: str


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
