"""Dictation mode: play the prompt aloud, the learner types what they hear."""

from __future__ import annotations

from models import QuestionView


class DictationMode:
    """Screen title, recorded practice type and prompt text for dictation."""

    name = "Dictation"
    record_kind = "Dictation"
    auto_play = True

    def view(
        self,
        primary_language: str,
        secondary_language: str,
        primary_text: str,
        *,
        listen_hint: bool = True,
    ) -> QuestionView:
        # primary_text is unused: dictation never shows the written prompt.
        return QuestionView(
            prompt=f"{secondary_language} dictation",
            display=(
                f"Listen to the {secondary_language} pronunciation, then type the {secondary_language} text."
                if listen_hint
                else ""
            ),
            instruction=f"Based on the {secondary_language} pronunciation, write the {secondary_language} text:",
        )
