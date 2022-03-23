from aiogram import types

from app.bot import callback_data as cb
from app.bot.payload import Notifications


class InlineKeyboard:

    def __init__(self, layout: list[list[tuple[str, cb.BaseCallbackData]]] = None):
        self.layout = layout or []

    def add(self, row: list[tuple[str, cb.BaseCallbackData]]):
        self.layout.append(row)

    def dump(self) -> types.InlineKeyboardMarkup:
        markup = types.InlineKeyboardMarkup()
        for row in self.layout:
            markup.add(*[types.InlineKeyboardButton(i[0], callback_data=i[1].dump()) for i in row])
        return markup


class ReplyKeyboard:

    def __init__(self, layout: list[list[str]] = None):
        self.layout = layout or []

    def add(self, row: list[str]):
        self.layout.append(row)

    def dump(self) -> types.ReplyKeyboardMarkup:
        markup = types.ReplyKeyboardMarkup()
        for row in self.layout:
            markup.add(*[types.KeyboardButton(i) for i in row])
        return markup


def main_menu(n_to_remember: int, n_to_recall: int) -> types.InlineKeyboardMarkup:
    keyboard = InlineKeyboard()

    if n_to_remember == 0:
        keyboard.add([
            (f"Изучить ({n_to_remember})", cb.Notify(text_id=Notifications.no_words_to_remember)),
        ])
    else:
        keyboard.add([
            (f"Изучить ({n_to_remember})", cb.RememberWordsMenu()),
        ])

    if n_to_recall == 0:
        keyboard.add([
            (f"Повторить ({n_to_recall})", cb.Notify(text_id=Notifications.no_words_to_recall)),
        ])
    else:
        keyboard.add([
            (f"Повторить ({n_to_recall})", cb.RecallWordsQuestion()),
        ])

    keyboard.add([
        ("⚙ Настройки", cb.Stub()),
    ])
    keyboard.add([
        ("О боте", cb.AboutBot()),
        ("Обновить", cb.MainMenu(new=True)),
    ])
    return keyboard.dump()
