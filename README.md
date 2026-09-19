# Dictation and Spelling Practice

Run the graphical interface:

```*bash*
/usr/bin/python3 ctest.py
```

You can also run it with any Python interpreter that has the Tk GUI library installed. If `python3 ctest.py` reports that `_tkinter` cannot be found, use the macOS system Python shown above, or install Tk in the current Python environment.

When the file selection window opens, it will default to the `Resource` directory in the project. On the home page, select a UTF-8 encoded CSV file, then choose either “Dictation” or “Spelling Practice”. The first row is required: it names the language in each column. Supported names are `English`, `French`, `Spanish`, and `Chinese`. Every later row must contain the two matching data values:

```*csv*
English,French
is,est
French,français
I,je
he,il
```

- **Dictation**: Play the content of the primary column and enter the text you hear.
- **Spelling Practice**: Display the content of the primary column and enter the text from the other column.
- The **Random question order** option on the home page is selected by default. Uncheck it to practice in the original row order of the CSV file.
- The **Reverse exercise** option on the home page swaps the roles of the two columns. Dictation always reads the current primary column aloud; Spelling Practice displays the current primary column and tests the other column.
- You can enter the starting and ending row numbers in **Exam range** (for example, `1` to `10`) to practice only the specified inclusive range.
- Answer comparison ignores leading/trailing and consecutive spaces, as well as English letter case; `|` or `｜` means “or”, and either option is accepted as correct. Differences in French accents, Chinese characters, and other text are still preserved.
- Incorrect answers from each practice session are appended to `Wrong.csv` in the project directory. It contains the question, the correct translation, and the answer entered by the user.

Dictation uses the language declared for the current primary column in the CSV header to select a matching system voice. On macOS, English uses the default `say` voice (the same behaviour as the `SpellingTest` project), while Chinese, French, and Spanish select a matching voice. On Windows/Linux it uses a language-tagged `pyttsx3` voice when the installed engine exposes one. If no matching system voice is available, it falls back to the system default and Spelling Practice remains available.
