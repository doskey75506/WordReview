"""Cross-platform best-effort text-to-speech used by the GUI."""

import platform
import subprocess


def read_text_aloud(text: str) -> None:
    try:
        if platform.system() == "Darwin":
            subprocess.run(["say", text], check=False)
            return
        # pyttsx3 uses the voices installed on the operating system. It is
        # optional so the rest of the GUI remains usable without it.
        import pyttsx3

        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
    except Exception:
        # Audio availability should not prevent a learner from practising.
        pass
