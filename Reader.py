"""Header-selected, best-effort text-to-speech used by the GUI."""

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
LANGUAGE_CODES = {
    "Chinese": ("zh",),
    "French": ("fr",),
    "Spanish": ("es",),
    "English": ("en",),
}
NON_ENGLISH_RATE = "150"
PREFERRED_MACOS_VOICE_FAMILY = "Eddy"
PREFERRED_CHINESE_VOICE = "Tingting"


def speech_text(text: str) -> str:
    """Avoid spelling out capital letters when the content is a word."""
    return text.casefold()


def canonical_language(value: str) -> str:
    """Validate and standardise a language name from a CSV header cell."""
    for language in LANGUAGE_LOCALES:
        if value.strip().casefold() == language.casefold():
            return language
    supported = ", ".join(LANGUAGE_LOCALES)
    raise ValueError(f"Unsupported language '{value}'. Use one of: {supported}.")


@lru_cache(maxsize=1)
def available_macos_voices() -> dict[str, str]:
    """Map installed macOS locale codes to voice names, without fixed names."""
    try:
        result = subprocess.run(["say", "-v", "?"], capture_output=True, text=True, check=False)
    except OSError:
        return {}
    voices: dict[str, str] = {}
    for line in result.stdout.splitlines():
        match = re.match(r"^(.*?)\s+([a-z]{2}_[A-Z]{2})\s+#", line)
        if match:
            voice_name, locale = match.groups()
            # Keep the original Chinese voice, while preferring the modern
            # Eddy family for French and Spanish.
            is_preferred_chinese_voice = locale == "zh_CN" and voice_name == PREFERRED_CHINESE_VOICE
            is_preferred_eddy_voice = locale.startswith(("fr_", "es_")) and voice_name.startswith(PREFERRED_MACOS_VOICE_FAMILY)
            if is_preferred_chinese_voice or is_preferred_eddy_voice or locale not in voices:
                voices[locale] = voice_name
    return voices


def voice_for(language: str) -> str | None:
    # Match SpellingTest's English behaviour: `say text` with no forced voice.
    # The user can therefore choose their preferred English voice in macOS.
    if language == "English":
        return None
    for locale in LANGUAGE_LOCALES[language]:
        voice = available_macos_voices().get(locale)
        if voice:
            return voice
    return None


def pyttsx3_voice_for(engine: object, language: str) -> str | None:
    """Find a language-tagged pyttsx3 voice on Windows or Linux when present."""
    target_codes = LANGUAGE_CODES[language]
    for voice in engine.getProperty("voices"):
        raw_languages = getattr(voice, "languages", ()) or ()
        if isinstance(raw_languages, (str, bytes)):
            raw_languages = (raw_languages,)
        for raw_language in raw_languages:
            if isinstance(raw_language, bytes):
                raw_language = raw_language.decode("utf-8", errors="ignore")
            code = re.sub(r"[^a-z_-]", "", str(raw_language).casefold()).replace("-", "_")
            if any(code.startswith(target) for target in target_codes):
                return voice.id
        description = f"{getattr(voice, 'id', '')} {getattr(voice, 'name', '')}".casefold()
        if any(code in description for code in target_codes):
            return voice.id
    return None


def read_text_aloud(text: str, language: str) -> None:
    """Read text using the language explicitly supplied by the CSV header."""
    text = speech_text(text)
    language = canonical_language(language)
    try:
        if platform.system() == "Darwin":
            command = ["say"]
            voice = voice_for(language)
            if voice:
                command.extend(["-v", voice])
            if language != "English":
                command.extend(["-r", NON_ENGLISH_RATE])
            subprocess.run([*command, text], check=False)
            return
        # pyttsx3 uses voices installed on Windows/Linux. Select a matching
        # language-tagged voice where the platform exposes one.
        import pyttsx3

        engine = pyttsx3.init()
        voice = pyttsx3_voice_for(engine, language)
        if voice:
            engine.setProperty("voice", voice)
        engine.say(text)
        engine.runAndWait()
    except Exception:
        # Audio availability should not prevent a learner from practising.
        pass
