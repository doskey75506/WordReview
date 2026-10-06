"""Spelling mode: show the prompt text, the learner types the translation."""

from __future__ import annotations

from models import QuestionView


class SpellingMode:
    """Screen title, recorded practice type and prompt text for spelling."""

    name = "Spelling Practice"
    record_kind = "spelling"
    auto_play = False

    def view(
        self,
        primary_language: str,
        secondary_language: str,
        primary_text: str,
        *,
        listen_hint: bool = True,
    ) -> QuestionView:
        return QuestionView(
            prompt=f"{primary_language} text",
            display=primary_text,
            instruction=f"Based on the {primary_language} text, write the {secondary_language} text:",
        )
