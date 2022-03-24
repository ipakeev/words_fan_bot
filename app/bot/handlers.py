import re
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from functools import wraps
from random import shuffle
from typing import Union

from aiogram import types

from app.bot import callback_data as cb, payload
from app.bot import keyboards
from app.bot.base import config, store, states, messenger, coroutines, bot, dp
from app.bot.payload import Emoji, Notifications
from app.bot.states import WordsNavigationState
from app.logger import logger
from app.store.users.models import UserLangDC, UserWordDC, UserDC
from app.utils import now, MediaGenerator

TRANSLATION_CODE = "en-ru"


@asynccontextmanager
async def context_send_sticker(user_id: int, sticker: str):
    msg = await bot.send_sticker(user_id, sticker)
    try:
        yield
    finally:
        await msg.delete()


async def when_throttled(msg: Union[types.Message, types.CallbackQuery], *args, **kwargs):
    await msg.answer("Too many requests.")


def queue_message(func: Callable[..., Awaitable]):
    @dp.throttled(when_throttled)
    @wraps(func)
    async def wrapper(msg: types.Message, *args, **kwargs):
        chat = msg.chat
        user = msg.from_user
        if chat.id == user.id:
            logger.debug(f"{func.__name__} | {user.username} ({user.id}): {[msg.text]}")
        else:
            logger.debug(f"{func.__name__} | {chat.title} ({chat.id}): {user.username} ({user.id}): {[msg.text]}")
        await coroutines.add(user.id, func(msg, *args, **kwargs))

    return wrapper


def queue_query(func: Callable[..., Awaitable]):
    @dp.throttled(when_throttled)
    @wraps(func)
    async def wrapper(msg: types.CallbackQuery, *args, **kwargs):
        chat = msg.message.chat
        user = msg.from_user
        if chat.id == user.id:
            logger.debug(f"{func.__name__} | {user.username} ({user.id})")
        else:
            logger.debug(f"{func.__name__} | {chat.title} ({chat.id}): {user.username} ({user.id})")
        await coroutines.add(user.id, func(msg, *args, **kwargs))

    return wrapper


@dp.message_handler(text="/start")
@queue_message
async def start(msg: types.Message):
    await msg.delete()

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    keyboard.add(types.KeyboardButton("/start"))
    await msg.answer("👋", reply_markup=keyboard)

    user = msg.from_user
    user_langs = await store.users.get_user_langs(user.id)
    if not user_langs:
        await store.users.add_user(
            UserDC(id=user.id,
                   is_bot=user.is_bot,
                   username=user.username,
                   first_name=user.first_name,
                   last_name=user.last_name,
                   language_code=user.language_code,
                   joined_at=now())
        )
        await store.users.add_user_lang(
            UserLangDC(user_id=msg.from_user.id,
                       translation_code=config.langs.get_translation_code(
                           config.langs.get_native_language_code(TRANSLATION_CODE),
                           config.langs.get_foreign_language_code(TRANSLATION_CODE)),
                       )
        )
        await main_menu_message(msg)
        # await init_language_selection(msg)
    else:
        await main_menu_message(msg)


async def init_language_selection(msg: types.Message):
    keyboard = keyboards.InlineKeyboard()
    for language in config.langs.languages:
        code = config.langs.get_language_code(language)
        keyboard.add([
            (language, cb.SelectNativeLanguage(native=code)),
        ])
    await messenger.send(msg.from_user.id, "Select your native language:", keyboard=keyboard.dump())


async def main_menu_message(msg: types.Message):
    foreign = config.langs.get_foreign_language(TRANSLATION_CODE)
    n_to_remember = await store.users.count_to_remember_user_words(msg.from_user.id, TRANSLATION_CODE)
    n_to_recall = await store.users.count_to_recall_user_words(msg.from_user.id, TRANSLATION_CODE)

    keyboard = keyboards.main_menu(n_to_remember, n_to_recall)
    text = f"Привет, {msg.from_user.first_name}!\n" \
           f"Изучаем {foreign}."

    await messenger.send(msg.from_user.id, text, keyboard=keyboard)


@dp.callback_query_handler(cb.MainMenu.filter())
@queue_query
async def main_menu(msg: types.CallbackQuery, callback_data: dict):
    callback_data = cb.MainMenu(**callback_data)

    foreign = config.langs.get_foreign_language(TRANSLATION_CODE)
    n_to_remember = await store.users.count_to_remember_user_words(msg.from_user.id, TRANSLATION_CODE)
    n_to_recall = await store.users.count_to_recall_user_words(msg.from_user.id, TRANSLATION_CODE)

    keyboard = keyboards.main_menu(n_to_remember, n_to_recall)
    text = f"Привет, {msg.from_user.first_name}!\n" \
           f"Изучаем {foreign}."

    await msg.answer()
    if callback_data.new:
        await messenger.send(msg.from_user.id, text, keyboard=keyboard)
    else:
        await messenger.edit(msg.from_user.id, text, keyboard=keyboard)


@dp.message_handler()
@queue_message
async def add_new_word(msg: types.Message):
    user_id = msg.from_user.id
    original = msg.text.lower().strip()

    if "http" in original:
        sub = re.findall('\"(.+)\"', original)
        if not sub:
            return await msg.answer("Неправильный запрос.")
        original = sub[0]

    if len(original) < 2:
        return await msg.answer("Слишком короткое слово.")
    if len(original) > 20:
        return await msg.answer("Слишком длинное слово.")
    if any(i in "[]()<>/?,.|\\~`!@#$%^&*_+=:;1234567890" for i in original):
        return await msg.answer("В слове присутствуют запрещенные символы.")

    word = await store.words.get_word(TRANSLATION_CODE, original)
    if word is None:
        word = await store.translator.translate(TRANSLATION_CODE, original)
        if not word.translations:
            return await msg.answer("Перевод слова не найден.")

        async with MediaGenerator.generate_audio(
                config.langs.get_foreign_language_code(TRANSLATION_CODE),
                original,
        ) as filename:
            audio = types.input_file.InputFile(filename, filename="_.mp3")
            audio_msg = await bot.send_audio(config.bot.temp_chat_id, audio)
            audio_id = audio_msg.audio.file_id
        word.audio_id = audio_id
        word = await store.words.add_word(word)

    if not word.translations:
        return await msg.answer("Перевод слова не найден.")

    current_time = now()
    user_word = await store.users.add_user_word(UserWordDC(user_id=user_id,
                                                           translation_code=word.translation_code,
                                                           word_id=word.id,
                                                           added_at=current_time))
    text = "Добавлено слово:" if user_word.added_at == current_time else "Добавлено ранее:"
    keyboard = keyboards.InlineKeyboard([
        [("Удалить сообщение", cb.Delete())],
    ])
    await msg.answer(f"{text}\n\n" + payload.full_word_text(word), reply_markup=keyboard.dump())


@dp.callback_query_handler(cb.Delete().filter())
@queue_query
async def delete_msg(msg: types.CallbackQuery):
    await msg.message.delete()


@dp.callback_query_handler(cb.SelectNativeLanguage.filter())
@queue_query
async def select_native_language(msg: types.CallbackQuery, callback_data: dict):
    native_code = cb.SelectNativeLanguage(**callback_data).native
    keyboard = keyboards.InlineKeyboard()
    for language in config.langs.languages:
        code = config.langs.get_language_code(language)
        if code == native_code:
            continue
        keyboard.add([
            (language, cb.SelectForeignLanguage(native=native_code, foreign=code)),
        ])
    await msg.answer()
    await messenger.edit(msg.from_user.id, "Select language to learn:", keyboard=keyboard.dump())


@dp.callback_query_handler(cb.SelectForeignLanguage.filter())
@queue_query
async def select_foreign_language(msg: types.CallbackQuery, callback_data: dict):
    callback_data = cb.SelectForeignLanguage(**callback_data)
    await store.users.add_user_lang(
        UserLangDC(user_id=msg.from_user.id,
                   translation_code=config.langs.get_translation_code(callback_data.native,
                                                                      callback_data.foreign))
    )
    await msg.answer()
    await main_menu(msg, cb.MainMenu(new=False).as_dict())


@dp.callback_query_handler(cb.RememberWordsMenu.filter())
@queue_query
async def remember_words_menu(msg: types.CallbackQuery, callback_data: dict):
    callback_data = cb.RememberWordsMenu(**callback_data)
    random_emoji = Emoji.yes if callback_data.random else Emoji.no

    await states.set_words_remember_state(
        msg.from_user.id,
        WordsNavigationState(swap=callback_data.swap,
                             random=callback_data.random)
    )

    keyboard = keyboards.InlineKeyboard([
        [
            (config.langs.get_translation_text(TRANSLATION_CODE, reverse=callback_data.swap),
             cb.RememberWordsMenu(swap=not callback_data.swap, random=callback_data.random)),
        ],
        [
            (f"{random_emoji}  Перемешать",
             cb.RememberWordsMenu(swap=callback_data.swap,
                                  random=not callback_data.random)),
        ],
        [
            ("Назад", cb.MainMenu()),
            ("Далее", cb.RememberWordsQuestion()),
        ],
    ])
    await msg.answer()
    await messenger.edit(msg.from_user.id, "Выберите параметры", keyboard=keyboard.dump())


@dp.callback_query_handler(cb.RememberWordsQuestion().filter())
@queue_query
async def remember_words_question(msg: types.CallbackQuery, callback_data: dict):
    callback_data = cb.RememberWordsQuestion(**callback_data)
    user_id = msg.from_user.id
    settings = await states.get_words_remember_state(user_id)

    if callback_data.i == 0:
        idx = await store.users.get_ids_words_to_remember(user_id, TRANSLATION_CODE)
        if settings.random:
            shuffle(idx)
        await states.set_words_remember_order(user_id, idx)
    else:
        idx = await states.get_words_remember_order(user_id)

    if callback_data.mem:
        await msg.answer("Запомнили.")
        await store.users.set_remembered(user_id, idx[callback_data.i - 1])
    if callback_data.rm:
        await msg.answer("Удалено.")
        await store.users.delete_word(user_id, idx[callback_data.i - 1])

    if callback_data.i == len(idx):
        await msg.answer("Закончились слова.")
        return await main_menu(msg, cb.MainMenu().as_dict())

    word = await store.words.get_word_by_id(idx[callback_data.i])

    if settings.swap:
        text = f"❓❓❓\n\n"
        text += f"<b>Перевод:</b>\n"
        for w in word.translations:
            text += f"- {w}\n"
    else:
        text = f"📗 <b>{word.original}</b>\n\n" \
               f"❓❓❓"

    keyboard = keyboards.InlineKeyboard()
    keyboard.add([
        ("Назад", cb.MainMenu()),
        ("Ответ", cb.RememberWordsAnswer(i=callback_data.i)),
    ])

    await msg.answer()
    await messenger.edit(msg.from_user.id, text, audio_id=word.audio_id, keyboard=keyboard.dump())


@dp.callback_query_handler(cb.RememberWordsAnswer().filter())
@queue_query
async def remember_words_answer(msg: types.CallbackQuery, callback_data: dict):
    callback_data = cb.RememberWordsAnswer(**callback_data)
    user_id = msg.from_user.id

    idx = await states.get_words_remember_order(user_id)
    word = await store.words.get_word_by_id(idx[callback_data.i])

    keyboard = keyboards.InlineKeyboard()

    if callback_data.sub == "full":
        text = payload.full_word_text(word)
        row = []
        if word.examples:
            row.append(("Примеры", cb.RememberWordsAnswer(i=callback_data.i, sub="examples")))
        if word.idioms:
            row.append(("Идиомы", cb.RememberWordsAnswer(i=callback_data.i, sub="idioms")))
        if row:
            keyboard.add(row)
    elif callback_data.sub == "examples":
        text = payload.examples_text(word, callback_data.page)
        row = [("Основное", cb.RememberWordsAnswer(i=callback_data.i, sub="full"))]
        if word.idioms:
            row.append(("Идиомы", cb.RememberWordsAnswer(i=callback_data.i, sub="idioms")))
        if payload.has_more_examples(word, callback_data.page):
            row.append(("Еще", cb.RememberWordsAnswer(i=callback_data.i, sub="examples", page=callback_data.page + 1)))
        keyboard.add(row)
    elif callback_data.sub == "idioms":
        text = payload.idioms_text(word, callback_data.page)
        row = [("Основное", cb.RememberWordsAnswer(i=callback_data.i, sub="full"))]
        if word.examples:
            row.append(("Примеры", cb.RememberWordsAnswer(i=callback_data.i, sub="examples")))
        if payload.has_more_idioms(word, callback_data.page):
            row.append(("Еще", cb.RememberWordsAnswer(i=callback_data.i, sub="idioms", page=callback_data.page + 1)))
        keyboard.add(row)
    else:
        raise ValueError(callback_data)

    keyboard.add([
        ("Удалить", cb.RememberWordsQuestion(i=callback_data.i + 1, rm=True)),
        ("Запомнил", cb.RememberWordsQuestion(i=callback_data.i + 1, mem=True)),
    ])
    keyboard.add([
        ("Назад", cb.MainMenu()),
        ("Далее", cb.RememberWordsQuestion(i=callback_data.i + 1)),
    ])

    await msg.answer()
    await messenger.edit(msg.from_user.id, text, audio_id=word.audio_id, keyboard=keyboard.dump())


@dp.callback_query_handler(cb.RecallWordsQuestion.filter())
@queue_query
async def recall_words_question(msg: types.CallbackQuery, callback_data: dict):
    callback_data = cb.RecallWordsQuestion(**callback_data)
    user_id = msg.from_user.id

    if callback_data.i == 0:
        original_ids = await store.users.get_ids_original_words_to_recall(user_id, TRANSLATION_CODE)
        translation_ids = await store.users.get_ids_translation_words_to_recall(user_id, TRANSLATION_CODE)
        ids = [(i, False) for i in original_ids] + [(i, True) for i in translation_ids]
        shuffle(ids)
        await states.set_words_recall_order(user_id, ids)
    else:
        ids = await states.get_words_recall_order(user_id)

    if callback_data.mem:
        await msg.answer("Запомнили.")
        word_id, swap = ids[callback_data.i - 1]
        if swap:
            await store.users.set_shown_translation(user_id, word_id)
        else:
            await store.users.set_shown_original(user_id, word_id)
    if callback_data.rm:
        await msg.answer("Удалено.")
        word_id, swap = ids[callback_data.i - 1]
        await store.users.delete_word(user_id, word_id)

        n_deleted = len([i for i in ids if i[0] == word_id])
        ids = [i for i in ids if i[0] != word_id]
        callback_data.i -= n_deleted
        await states.set_words_recall_order(user_id, ids)

    if callback_data.i == len(ids):
        await msg.answer("Закончились слова.")
        return await main_menu(msg, cb.MainMenu().as_dict())

    word_id, swap = ids[callback_data.i]
    word = await store.words.get_word_by_id(word_id)

    if swap:
        text = f"❓❓❓\n\n"
        text += f"<b>Перевод:</b>\n"
        for w in word.translations:
            text += f"- {w}\n"
    else:
        text = f"📗 <b>{word.original}</b>\n\n" \
               f"❓❓❓"

    keyboard = keyboards.InlineKeyboard([
        [
            ("Пропустить", cb.RecallWordsQuestion(i=callback_data.i + 1))
        ],
        [
            ("Назад", cb.MainMenu()),
            ("Ответ", cb.RecallWordsAnswer(i=callback_data.i)),
        ]
    ])
    await msg.answer()
    await messenger.edit(msg.from_user.id, text, audio_id=word.audio_id, keyboard=keyboard.dump())


@dp.callback_query_handler(cb.RecallWordsAnswer().filter())
@queue_query
async def recall_words_answer(msg: types.CallbackQuery, callback_data: dict):
    callback_data = cb.RecallWordsAnswer(**callback_data)
    user_id = msg.from_user.id

    ids = await states.get_words_recall_order(user_id)
    word_id, swap = ids[callback_data.i]
    word = await store.words.get_word_by_id(word_id)

    keyboard = keyboards.InlineKeyboard()

    if callback_data.sub == "full":
        text = payload.full_word_text(word)
        row = []
        if word.examples:
            row.append(("Примеры", cb.RecallWordsAnswer(i=callback_data.i, sub="examples")))
        if word.idioms:
            row.append(("Идиомы", cb.RecallWordsAnswer(i=callback_data.i, sub="idioms")))
        if row:
            keyboard.add(row)
    elif callback_data.sub == "examples":
        text = payload.examples_text(word, callback_data.page)
        row = [("Основное", cb.RecallWordsAnswer(i=callback_data.i, sub="full"))]
        if word.idioms:
            row.append(("Идиомы", cb.RecallWordsAnswer(i=callback_data.i, sub="idioms")))
        if payload.has_more_examples(word, callback_data.page):
            row.append(("Еще", cb.RecallWordsAnswer(i=callback_data.i, sub="examples", page=callback_data.page + 1)))
        keyboard.add(row)
    elif callback_data.sub == "idioms":
        text = payload.idioms_text(word, callback_data.page)
        row = [("Основное", cb.RecallWordsAnswer(i=callback_data.i, sub="full"))]
        if word.examples:
            row.append(("Примеры", cb.RecallWordsAnswer(i=callback_data.i, sub="examples")))
        if payload.has_more_idioms(word, callback_data.page):
            row.append(("Еще", cb.RecallWordsAnswer(i=callback_data.i, sub="idioms", page=callback_data.page + 1)))
        keyboard.add(row)
    else:
        raise ValueError(callback_data)

    keyboard.add([
        ("Удалить", cb.RecallWordsQuestion(i=callback_data.i + 1, rm=True)),
        ("Запомнил", cb.RecallWordsQuestion(i=callback_data.i + 1, mem=True)),
    ])
    keyboard.add([
        ("Назад", cb.MainMenu()),
        ("Далее", cb.RecallWordsQuestion(i=callback_data.i + 1)),
    ])
    await msg.answer()
    await messenger.edit(msg.from_user.id, text, audio_id=word.audio_id, keyboard=keyboard.dump())


@dp.callback_query_handler(cb.Stub.filter())
@queue_query
async def stub_function(msg: types.CallbackQuery):
    await msg.answer("Пока не реализовано...")


@dp.callback_query_handler(cb.Notify.filter())
@queue_query
async def notify_function(msg: types.CallbackQuery, callback_data: dict):
    callback_data = cb.Notify(**callback_data)
    await msg.answer(Notifications.get(callback_data.text_id))


@dp.callback_query_handler(cb.AboutBot.filter())
@queue_query
async def about_bot(msg: types.CallbackQuery):
    text = "Бот предназначен для изучения иностранных слов. " \
           "В данный момент - слов на английском языке.\n\n" \
           "Есть 2 способа добавления слов для изучения:\n" \
           "1. Отправить слово в чат с ботом.\n" \
           "2. Переслать слово из другого приложения, например, из браузера Chrome.\n\n" \
           "После того как Вы запомнили слово, через определенные промежутки времени " \
           "бот будет предлагать повторить это слово (через 1, 3, 7, 30 и 90 дней)."
    keyboard = keyboards.InlineKeyboard([
        [("В главное меню", cb.MainMenu())],
    ])
    await msg.answer()
    await messenger.edit(msg.from_user.id, text, keyboard=keyboard.dump())
