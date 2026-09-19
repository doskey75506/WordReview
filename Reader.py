"""Language-aware, best-effort text-to-speech used by the GUI."""

from __future__ import annotations

from functools import lru_cache
import platform
import re
import subprocess


LANGUAGE_LOCALES = {
    "Chinese": ("zh_CN", "zh_TW", "zh_HK"),
    "French": ("fr_FR", "fr_CA"),
    "Spanish": ("es_ES", "es_MX"),
    "English": ("en_US", "en_GB"),
}
FRENCH_WORDS = {
    "bonjour", "merci", "être", "est", "français", "anglais", "petit", "grand",
    "je", "il", "elle", "aimer", "aime", "le", "la", "les", "un", "une",
}
SPANISH_WORDS = {
    "hola", "gracias", "adiós", "ser", "estar", "es", "pequeño", "grande",
    "yo", "él", "ella", "me", "gusta", "el", "la", "los", "las", "un", "una",
}


def speech_text(text: str) -> str:
    """Avoid spelling out capital letters when the content is a word."""
    return text.casefold()


def detect_language(text: str) -> str:
    """Recognise the four languages supported by this app, with English fallback."""
    lowered = speech_text(text)
    if any("\u4e00" <= character <= "\u9fff" for character in lowered):
        return "Chinese"
    if any(character in lowered for character in "ñáíóú¿¡"):
        return "Spanish"
    if any(character in lowered for character in "àâæçèêëîïôœùûÿ"):
        return "French"

    words = set(re.findall(r"[a-zà-ÿœ]+", lowered))
    french_score = len(words & FRENCH_WORDS)
    spanish_score = len(words & SPANISH_WORDS)
    if french_score > spanish_score and french_score:
        return "French"
    if spanish_score > french_score and spanish_score:
        return "Spanish"
    return "English"


@lru_cache(maxsize=1)
def available_macos_voices() -> dict[str, str]:
    """Map installed macOS locale codes to voice names, without fixed names."""
    try:
        result = subprocess.run(["say", "-v", "?"], capture_output=True, text=True, check=False)
    except OSError:
        return {}
    voices: dict[str, str] = {}
    for line in result.stdout.splitlines():
        match = re.match(r"^(.*?)\s{2,}([a-z]{2}_[A-Z]{2})\s+#", line)
        if match:
            voice_name, locale = match.groups()
            voices.setdefault(locale, voice_name)
    return voices


def voice_for(language: str) -> str | None:
    for locale in LANGUAGE_LOCALES[language]:
        voice = available_macos_voices().get(locale)
        if voice:
            return voice
    return None


def read_text_aloud(text: str) -> None:
    text = speech_text(text)
    try:
        if platform.system() == "Darwin":
            command = ["say"]
            voice = voice_for(detect_language(text))
            if voice:
                command.extend(["-v", voice])
            subprocess.run([*command, text], check=False)
            return
        # pyttsx3 uses a voice installed on the operating system. It is
        # optional so the rest of the GUI remains usable without it.
        import pyttsx3

        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
    except Exception:
        # Audio availability should not prevent a learner from practising.
        pass
