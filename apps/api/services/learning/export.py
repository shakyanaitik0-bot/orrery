"""Flashcard deck export to Anki-compatible CSV.

The column layout and quoting rule come from TutorBot (MIT): a plain
"Front,Back,Tags" CSV, which Anki's importer accepts directly, with every
field double-quoted so a comma, quote or newline inside a card's text can't
corrupt the row. TutorBot wrote this to disk under its own web root, which
would let one export serve another's content — this build streams the CSV
straight to the response instead, so nothing lands on the server's disk.
"""

import csv
import io


def _quote(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def to_anki_csv(cards: list[dict], subject_title: str) -> str:
    """cards: [{conceptTitle, front, back}]. Tag is the subject, so a deck
    from more than one subject stays sortable inside Anki."""
    buf = io.StringIO()
    writer = csv.writer(buf, quoting=csv.QUOTE_ALL)
    for card in cards:
        writer.writerow([card["front"], card["back"], subject_title.replace(" ", "-")])
    return buf.getvalue()
