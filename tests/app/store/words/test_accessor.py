import pytest

from app.store.words.models import WordDC
from app.utils import now

word = WordDC(translation_code="en-ru",
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


@pytest.mark.asyncio
class TestWordsAccessor:

    async def test_empty(self, application):
        assert (await application.store.words.get_word(word.translation_code, word.original)) is None

    async def test_word(self, application):
        await application.store.words.add_word(word)
        same_word = await application.store.words.get_word(word.translation_code, word.original)
        word.id = 1
        assert same_word == word

    async def test_insert_the_same(self, application):
        same_word1 = await application.store.words.add_word(word)
        same_word2 = await application.store.words.add_word(word)
        word.id = 1
        assert word == same_word1 == same_word2

