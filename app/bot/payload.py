import re

from app.store.words.models import WordDC

EXAMPLES_PER_PAGE = 4
IDIOMS_PER_PAGE = 4


class Emoji:
    yes = "✅"
    no = "❌"


class Notifications:
    data = {
        0: "Сначала добавьте слова для изучения.",
        1: "Пока нет слов для повторения.",
    }

    no_words_to_remember = 0
    no_words_to_recall = 1

    @classmethod
    def get(cls, id_: int) -> str:
        return cls.data[id_]


def drop_symbols(text: str):
    parts = re.findall(r"(<.+>)", text)
    if not parts:
        return text
    for part in parts:
        correct = part[1:-1].replace("<", "").replace(">", "")
        text = text.replace(part, f"<u>{correct}</u>")
    return text


def full_word_text(word: WordDC) -> str:
    original = drop_symbols(word.original)
    text = f"📗 <b>{original}</b>"
    if word.transcription:
        text += f"  [" + ", ".join(word.transcription) + "]"
    if word.noun_plural:
        text += f"  (" + ", ".join(word.noun_plural) + ")"
    text += "\n\n"
    if word.past_indefinite and word.past_participle:
        text += f"<i>verb:</i>\n"
        text += f"II : " + ", ".join(word.past_indefinite) + "\n"
        text += f"III: " + ", ".join(word.past_participle) + "\n\n"
    text += f"<b>Перевод:</b>\n"
    for w in word.translations[:10]:
        w = drop_symbols(w)
        text += f"- {w}\n"
    return text


def examples_text(word: WordDC, page: int) -> str:
    original = drop_symbols(word.original)
    text = f"📗 <b>{original}</b>"
    if word.transcription:
        text += f" [" + ", ".join(word.transcription) + "]"
    text += "\n\nПримеры:\n\n"
    start = EXAMPLES_PER_PAGE * page
    stop = start + EXAMPLES_PER_PAGE
    for original, translation in word.examples[start:stop]:
        original = drop_symbols(original)
        translation = drop_symbols(translation)
        text += f"📌 {original}\n" \
                f"🔗 {translation}\n\n"
    return text


def idioms_text(word: WordDC, page: int) -> str:
    original = drop_symbols(word.original)
    text = f"📗 <b>{original}</b>"
    if word.transcription:
        text += f" [" + ", ".join(word.transcription) + "]"
    text += "\n\nИдиомы:\n\n"
    start = IDIOMS_PER_PAGE * page
    stop = start + IDIOMS_PER_PAGE
    for original, translation in word.idioms[start:stop]:
        original = drop_symbols(original)
        translation = drop_symbols(translation)
        text += f"📌 <u>{original}</u>\n" \
                f"🔗 {translation}\n\n"
    return text


def has_more_examples(word: WordDC, current_page: int) -> bool:
    return len(word.examples) - (EXAMPLES_PER_PAGE * (current_page + 1)) > 0


def has_more_idioms(word: WordDC, current_page: int) -> bool:
    return len(word.idioms) - (IDIOMS_PER_PAGE * (current_page + 1)) > 0
