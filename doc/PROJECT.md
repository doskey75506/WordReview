# Project Structure and Developer Guide

Dictation and spelling practice desktop tool: Python + Tkinter, flat modules in the repository root — no src layout, no subpackages.

## Run

```bash
/usr/bin/python3 ctest.py   # macOS system Python has Tkinter built in
```

- Tkinter is **not** on pip. If `_tkinter` is missing, use the macOS system Python or `conda create -n wordreview python=3.11 tk`.
- `requirements.txt` lists only `pyttsx3`, needed **only on Windows/Linux**; macOS uses the `say` CLI (`Reader.py`), so a fresh macOS environment runs with no installs.

## Modules

`ctest.py` is only the entrypoint (`PracticeApp().mainloop()`, 6 lines). The real structure:

| File | Responsibility |
| --- | --- |
| `app.py` | **Main program**: `PracticeApp(tk.Tk)`, all Tk state vars, home screen, file dialog, `speak` (TTS thread) |
| `practice.py` | **Practice flow**: question screen, submit/finish/save; mode registry `MODES` and `mode_for_record_kind` |
| `review.py` | **Wrong-answer review**: list filtering (language + calendar dates), deletion, review quiz; `language_label` |
| `files.py` | **File management**: exercise CSV loading (`load_exercises`), wrong-answer store (`WRONG_FILE`/`load_wrong_entries`/`write_wrong_entries`) |
| `models.py` | Domain data and answer checking: `Exercise`, `WrongEntry`, `QuestionView`, `normalise`, `is_correct_answer`, `select_exercise_range` |
| `dictation.py` | **Dictation** mode: `DictationMode` (`name`/`record_kind`/`auto_play`/`view(...)`) |
| `spelling.py` | **Spelling** mode: `SpellingMode`, same interface |
| `widgets.py` | Reusable widgets: `DateField`, `CalendarPopup` (calendar date picker) |
| `Reader.py` | TTS and language parsing: `read_text_aloud`, `canonical_language` |

## Architecture notes

- **Screens are mixins, not separate widgets**: `PracticeApp(PracticeMixin, ReviewMixin, tk.Tk)`. State is defined only in `app.py.__init__`; mixin methods reach it via `self`. Switching screens = `_clear()` and rebuild.
- **Acyclic dependency direction**: `models` ← `files` / `dictation` / `spelling` ← `practice` ← `review` ← `app` ← `ctest`.
- **Mode objects carry the dictation/spelling differences**: `mode.view(primary_language, secondary_language, primary_text, listen_hint=...)` returns `QuestionView(prompt, display, instruction)`; an empty `display` means that line is not rendered. The practice screen uses the default `listen_hint=True` (dictation shows the "Listen to…" hint); the review screen passes `False`. `auto_play` controls automatic speech.
- **Data flow**: choose a CSV (first row = two language names) → load exercises → wrong answers collect in `self.wrong_answers` → `save_wrong_answers` appends them to `Wrong.csv` at the end → the review screen filters/re-tests and removes a row from the file once answered correctly.

## Data formats

- **Exercise CSV**: first row holds two language names (only `English`/`French`/`Spanish`/`Chinese`, validated by `canonical_language`); every later row is exactly two non-empty cells, read with `utf-8-sig`.
- **`Wrong.csv`** at `Resource/Data/Wrong.csv` (gitignored) header:
  `Practice time,Practice type,Primary language,Secondary language,Primary text,Correct answer,User answer`.
  The practice-type values are `DictationMode.record_kind` / `SpellingMode.record_kind` (`"Dictation"` / `"spelling"`); `mode_for_record_kind` and existing rows depend on those exact strings — **don't rename them**. The file is **hand-editable**: `load_wrong_entries` purges malformed rows (wrong column count, bad timestamp, unknown type, empty or unsupported language, empty question or answer), restores a missing header, rebuilds an emptied file and rewrites the file whenever it cleaned something; `write_wrong_entries` creates the parent directory, so deleting the whole `Resource/Data` folder just starts a fresh log. **No legacy support**: 5-column rows fail validation and are purged. Every write rewrites the whole file; new files get a UTF-8 BOM (Excel expects it — don't "fix" it).
- **Answer checking**: `is_correct_answer(..., allow_alternatives=True)` is always used — `|`/`｜` separates accepted alternatives; comparison collapses whitespace and English case only, it does **not** strip accents or Chinese characters.
- **Review semantics**: a row's identity is its index in `self.all_wrong_entries`; correcting or deleting it adds that index to `review_removed` and rewrites the whole file. Never write back from the filtered subset.

## Extending

- **Add a screen**: add a mixin (or a method on `PracticeApp`) and wire it from `_build_home`.
- **Add a practice mode**: create a module with a class matching `DictationMode`'s interface, register it in `practice.MODES`; add a `record_kind` and extend `mode_for_record_kind` if it should be recorded.
- **UI text**: existing labels use the font `("Arial Unicode MS", …)` to render Chinese/French — keep it for new labels.
- **TTS**: runs in a daemon thread (`PracticeApp.speak`) and `Reader.read_text_aloud` swallows all exceptions — speech failures are expected, don't report them as bugs. macOS voice names are parsed from `say -v ?` at runtime and cached; don't hardcode them.

## Verification

There is **no** test suite, linter, formatter, typechecker or CI in this repo. Available checks:

1. `python -m py_compile *.py`
2. Launch the GUI manually and exercise Dictation / Spelling / review with `Resource/example.csv`.

Scripted tests can drive `PracticeApp` without a mainloop — but you **must** patch `tkinter.messagebox.showinfo/showerror` first or dialogs will block. For the data layer, `import files` and point `files.WRONG_FILE` at a temp path.

## Known issues

- The merge-conflict markers that were committed at the end of `README.md` have been resolved in favour of the side matching `Reader.py` (Chinese `Tingting`, French/Spanish `Eddy` voices, rate 150). A stash (`stash@{0}`) from that conflict still exists in the repo.
- Line 4 of `.gitignore` ignores `.gitignore` itself, so the ignore rules are **local-only** and never committed.

A Chinese version of this guide lives in `doc/PROJECT.zh-CN.md`.
