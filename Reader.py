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
LANGUAGE_CODES = {
    "Chinese": ("zh",),
    "French": ("fr",),
    "Spanish": ("es",),
    "English": ("en",),
}
FRENCH_ACCENTS = "àâæçèêëîïôœùûÿ"
SPANISH_ACCENTS = "ñáíóú¿¡"
# These appear in both French and Spanish. They are used as a weaker signal,
# while language-specific words and accents decide ambiguous cases.
SHARED_ACCENTS = "éü"
FRENCH_WORDS = {
    "bonjour", "merci", "être", "est", "français", "anglais", "petit", "grand",
    "je", "il", "elle", "aimer", "aime", "le", "la", "les", "un", "une",
    "êtes", "prêt", "été", "café", "bébé", "aiguë", "crème", "déjà", "très",
    "de", "des", "et", "dans", "pour", "avec", "vous", "nous", "pas", "que",
}
SPANISH_WORDS = {
    "hola", "gracias", "adiós", "ser", "estar", "es", "pequeño", "grande",
    "yo", "él", "ella", "me", "gusta", "el", "la", "los", "las", "un", "una",
    "qué", "café", "pingüino", "también", "estás", "esté", "más", "sí", "después",
    "de", "y", "en", "para", "con", "usted", "nosotros", "no", "que", "como",
}


def speech_text(text: str) -> str:
    """Avoid spelling out capital letters when the content is a word."""
    return text.casefold()


def detect_language(text: str) -> str:
    """Recognise the four languages supported by this app, with English fallback."""
    lowered = speech_text(text)
    if any("\u4e00" <= character <= "\u9fff" for character in lowered):
        return "Chinese"
    words = set(re.findall(r"[a-zà-ÿœ]+", lowered))
    french_score = 3 * len(words & FRENCH_WORDS) + sum(character in FRENCH_ACCENTS for character in lowered)
    spanish_score = 3 * len(words & SPANISH_WORDS) + sum(character in SPANISH_ACCENTS for character in lowered)
    # A standalone é/ü is more common in French vocabulary. Spanish lexical
    # evidence still wins, for example "qué" and "pingüino".
    french_score += sum(character in SHARED_ACCENTS for character in lowered)
    if french_score > spanish_score:
        return "French"
    if spanish_score > french_score:
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


def read_text_aloud(text: str) -> None:
    text = speech_text(text)
    language = detect_language(text)
    try:
        if platform.system() == "Darwin":
            command = ["say"]
            voice = voice_for(language)
            if voice:
                command.extend(["-v", voice])
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
