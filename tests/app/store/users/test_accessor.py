import asyncio
from datetime import timedelta

import pytest
from freezegun import freeze_time

from app.store.store import Store
from app.store.users.models import UserDC, UserLangDC, UserWordDC
from app.store.words.models import WordDC
from app.utils import now

USER = UserDC(id=123,
              is_bot=False,
              username="username",
              first_name="Ivan",
              last_name="Ivanov",
              language_code="ru",
              joined_at=now())

WORD1 = WordDC(translation_code="en-ru",
               original="catch",
               transcription=["caetsh"],
               translations=[["поймать", "схватить"]],
               past_indefinite=["caught"],
               past_participle=["caught"],
               noun_plural=[],
               examples=[["We caught!", "Мы поймали!"]],
               idioms=[],
               audio_id="telegram_id1",
               added_at=now())

WORD2 = WordDC(translation_code="en-ru",
               original="number",
               transcription=["nambar"],
               translations=[["число"]],
               past_indefinite=[],
               past_participle=[],
               noun_plural=["numbers"],
               examples=[["One number.", "Одно число."]],
               idioms=[],
               audio_id="telegram_id2",
               added_at=now())


@pytest.fixture
def store(application) -> Store:
    return application.store


@pytest.fixture
def user(application) -> UserDC:
    user = asyncio.get_event_loop().run_until_complete(
        application.store.users.add_user(USER)
    )
    return user


@pytest.fixture
def word1(application) -> WordDC:
    return asyncio.get_event_loop().run_until_complete(
        application.store.words.add_word(WORD1)
    )


@pytest.fixture
def user_word1(application, user, word1) -> UserWordDC:
    return asyncio.get_event_loop().run_until_complete(
        application.store.users.add_user_word(
            UserWordDC(user_id=user.id,
                       word_id=word1.id,
                       translation_code=word1.translation_code,
                       added_at=now())
        )
    )


@pytest.fixture
def word2(application) -> WordDC:
    return asyncio.get_event_loop().run_until_complete(
        application.store.words.add_word(WORD2)
    )


@pytest.fixture
def user_word2(application, user, word2) -> UserWordDC:
    return asyncio.get_event_loop().run_until_complete(
        application.store.users.add_user_word(
            UserWordDC(user_id=user.id,
                       word_id=word2.id,
                       translation_code=word2.translation_code,
                       added_at=now())
        )
    )


@pytest.mark.asyncio
class TestUserAccessor:

    async def test_user(self, store):
        assert len(await store.users.get_users()) == 0

        assert (await store.users.add_user(USER)) == USER
        assert (await store.users.add_user(USER)) == USER

        existed = await store.users.get_users()
        assert len(existed) == 1
        assert existed[0] == USER

    async def test_user_lang(self, store, user):
        assert len(await store.users.get_user_langs(user.id)) == 0

        user_lang = UserLangDC(user_id=user.id, translation_code="en-ru")
        assert (await store.users.add_user_lang(user_lang)) == user_lang
        assert (await store.users.add_user_lang(user_lang)) == user_lang

        user_langs_list = await store.users.get_user_langs(user.id)
        assert len(user_langs_list) == 1
        assert user_langs_list[0] == user_lang

    async def test_user_word_zero(self, store, user):
        assert len(await store.users.get_user_words(user.id, "en-ru")) == 0

    async def test_user_word(self, store, user_word1):
        words = await store.users.get_user_words(user_word1.user_id, user_word1.translation_code)
        assert words == [user_word1]

    async def test_user_word_many(self, store, user_word1, user_word2):
        words = await store.users.get_user_words(user_word1.user_id, user_word1.translation_code)
        assert words == [user_word1, user_word2]

    async def test_user_word_not_raises(self, store, user_word1):
        assert (await store.users.add_user_word(user_word1)) == user_word1
        assert (await store.users.add_user_word(user_word1)) == user_word1
        words = await store.users.get_user_words(user_word1.user_id, user_word1.translation_code)
        assert len(words) == 1

    async def test_count_user_words(self, store, user_word1, user_word2):
        assert (await store.users.count_user_words(
            user_word1.user_id, user_word1.translation_code)) == 2

    async def test_count_to_remember_user_words(self, store, user_word1, user_word2):
        assert (await store.users.count_to_remember_user_words(
            user_word1.user_id, user_word1.translation_code)) == 2

        await store.users.set_remembered(user_word1.user_id, user_word1.word_id)
        assert (await store.users.count_to_remember_user_words(
            user_word1.user_id, user_word1.translation_code)) == 1

    async def test_count_to_recall_user_words(self, store, user_word1, user_word2):
        assert (await store.users.count_to_recall_user_words(
            user_word1.user_id, user_word1.translation_code)) == 0

        with freeze_time(now() - timedelta(days=2)):
            await store.users.set_remembered(user_word1.user_id, user_word1.word_id)
        await store.users.set_remembered(user_word2.user_id, user_word2.word_id)
        assert (await store.users.count_to_recall_user_words(
            user_word1.user_id, user_word1.translation_code)) == 2

        with freeze_time(now() + timedelta(days=2)):
            assert (await store.users.count_to_recall_user_words(
                user_word1.user_id, user_word1.translation_code)) == 4

    async def test_count_to_recall_multiple(self, store, user_word1, user_word2):
        with freeze_time(now() - timedelta(days=6)):
            await store.users.set_remembered(user_word1.user_id, user_word1.word_id)

        with freeze_time(now() - timedelta(days=4)):
            assert (await store.users.count_to_recall_user_words(
                user_word1.user_id, user_word1.translation_code)) == 2
            await store.users.set_shown_original(user_word1.user_id, user_word1.word_id)
            assert (await store.users.count_to_recall_user_words(
                user_word1.user_id, user_word1.translation_code)) == 1
            await store.users.set_shown_translation(user_word1.user_id, user_word1.word_id)
            assert (await store.users.count_to_recall_user_words(
                user_word1.user_id, user_word1.translation_code)) == 0

        assert (await store.users.count_to_recall_user_words(
            user_word1.user_id, user_word1.translation_code)) == 2

    async def test_set_remembered(self, store, user_word1, user_word2):
        uw1, uw2 = await store.users.get_user_words(user_word1.user_id,
                                                    user_word1.translation_code)
        t = now()
        same_uw1 = await store.users.set_remembered(uw1.user_id, uw1.word_id)
        assert same_uw1.id == uw1.id
        words = await store.users.get_user_words(user_word1.user_id,
                                                 user_word1.translation_code)
        assert len(words) == 2
        assert t <= words[0].remembered_at <= now()
        assert words[1] == user_word2

    async def test_delete_word(self, store, user_word1, user_word2):
        await store.users.delete_word(user_word1.user_id, user_word1.word_id)
        words = await store.users.get_user_words(user_word1.user_id, user_word1.translation_code)
        assert len(words) == 1
        assert words[0].id == user_word2.id

    async def test_get_words_to_remember(self, store, user_word1, user_word2):
        words = await store.users.get_words_to_remember(user_word1.user_id,
                                                        user_word1.translation_code)
        assert len(words) == 2

        await store.users.set_remembered(user_word1.user_id, user_word1.word_id)
        words = await store.users.get_words_to_remember(user_word1.user_id,
                                                        user_word1.translation_code)
        assert len(words) == 1
        assert words[0] == user_word2

    async def test_get_words_to_recall(self, store, user_word1, user_word2):
        words = await store.users.get_words_to_recall(user_word1.user_id,
                                                      user_word1.translation_code)
        assert len(words) == 0

        with freeze_time(now() - timedelta(days=2)):
            same = await store.users.set_remembered(user_word1.user_id, user_word1.word_id)
            assert same.next_show_original > now()
            assert same.next_show_translation > now()
        words = await store.users.get_words_to_recall(user_word1.user_id,
                                                      user_word1.translation_code)
        assert len(words) == 1
        assert words[0].id == user_word1.id

        with freeze_time(now() - timedelta(days=2)):
            await store.users.set_remembered(user_word2.user_id, user_word2.word_id)
        words = await store.users.get_words_to_recall(user_word1.user_id,
                                                      user_word1.translation_code)
        assert len(words) == 2

    async def test_set_shown_original(self, store, user_word1, user_word2):
        with freeze_time(now() - timedelta(days=5)):
            await store.users.set_remembered(user_word1.user_id, user_word1.word_id)
        with freeze_time(now() - timedelta(days=3)):
            same = await store.users.set_shown_original(user_word1.user_id, user_word1.word_id)
            assert same.n_shown_original == 1
            assert same.n_shown_translation == 0
            assert same.next_show_original > now()
            assert same.next_show_translation < now()
        words = await store.users.get_words_to_recall(user_word1.user_id,
                                                      user_word1.translation_code)
        assert len(words) == 1
        assert words[0].id == user_word1.id

    async def test_set_shown_translation(self, store, user_word1, user_word2):
        with freeze_time(now() - timedelta(days=5)):
            await store.users.set_remembered(user_word1.user_id, user_word1.word_id)
        with freeze_time(now() - timedelta(days=3)):
            same = await store.users.set_shown_translation(user_word1.user_id, user_word1.word_id)
            assert same.n_shown_original == 0
            assert same.n_shown_translation == 1
            assert same.next_show_original < now()
            assert same.next_show_translation > now()
        words = await store.users.get_words_to_recall(user_word1.user_id,
                                                      user_word1.translation_code)
        assert len(words) == 1
        assert words[0].id == user_word1.id

    async def test_get_ids_user_words(self, store, user_word1):
        idx = await store.users.get_ids_user_words(user_word1.user_id,
                                                   user_word1.translation_code)
        assert idx == [user_word1.word_id]

    async def test_get_ids_user_words_many(self, store, user_word1, user_word2):
        idx = await store.users.get_ids_user_words(user_word1.user_id,
                                                   user_word1.translation_code)
        assert idx == [user_word1.word_id, user_word2.word_id]

    async def test_get_ids_words_to_remember(self, store, user_word1, user_word2):
        idx = await store.users.get_ids_words_to_remember(user_word1.user_id,
                                                          user_word1.translation_code)
        assert idx == [user_word1.word_id, user_word2.word_id]

        await store.users.set_remembered(user_word1.user_id, user_word1.word_id)
        idx = await store.users.get_ids_words_to_remember(user_word1.user_id,
                                                          user_word1.translation_code)
        assert idx == [user_word2.word_id]

    async def test_get_ids_original_words_to_recall(self, store, user_word1, user_word2):
        idx = await store.users.get_ids_original_words_to_recall(user_word1.user_id,
                                                                 user_word1.translation_code)
        assert idx == []

        with freeze_time(now() - timedelta(days=2)):
            await store.users.set_remembered(user_word1.user_id, user_word1.word_id)
        idx = await store.users.get_ids_original_words_to_recall(user_word1.user_id,
                                                                 user_word1.translation_code)
        assert idx == [user_word1.word_id]

        await store.users.set_shown_translation(user_word1.user_id, user_word1.word_id)
        idx = await store.users.get_ids_original_words_to_recall(user_word1.user_id,
                                                                 user_word1.translation_code)
        assert idx == [user_word1.word_id]

        await store.users.set_shown_original(user_word1.user_id, user_word1.word_id)
        idx = await store.users.get_ids_original_words_to_recall(user_word1.user_id,
                                                                 user_word1.translation_code)
        assert idx == []

    async def test_get_ids_translation_words_to_recall(self, store, user_word1, user_word2):
        idx = await store.users.get_ids_translation_words_to_recall(user_word1.user_id,
                                                                    user_word1.translation_code)
        assert idx == []

        with freeze_time(now() - timedelta(days=2)):
            await store.users.set_remembered(user_word1.user_id, user_word1.word_id)
        idx = await store.users.get_ids_translation_words_to_recall(user_word1.user_id,
                                                                    user_word1.translation_code)
        assert idx == [user_word1.word_id]

        await store.users.set_shown_original(user_word1.user_id, user_word1.word_id)
        idx = await store.users.get_ids_translation_words_to_recall(user_word1.user_id,
                                                                    user_word1.translation_code)
        assert idx == [user_word1.word_id]

        await store.users.set_shown_translation(user_word1.user_id, user_word1.word_id)
        idx = await store.users.get_ids_translation_words_to_recall(user_word1.user_id,
                                                                    user_word1.translation_code)
        assert idx == []
