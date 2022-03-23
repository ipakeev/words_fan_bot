from typing import Optional

from sqlalchemy import and_
from sqlalchemy.dialects.postgresql import insert

from app.base.accessor import BaseAccessor
from app.store.words.models import WordDC, WordModel


class WordAccessor(BaseAccessor):

    async def add_word(self, word: WordDC) -> WordDC:
        """
        To avoid error in cases when more than one user add the same word,
        we use insert method.
        """
        stmt = insert(WordModel).values(**word.as_dict())
        model: WordModel = await stmt.on_conflict_do_update(
            index_elements=[WordModel.translation_code, WordModel.original],
            set_=dict(audio_id=stmt.excluded.audio_id,
                      profile=stmt.excluded.profile)
        ).returning(*WordModel).gino.model(WordModel).first()
        return model.as_dataclass()

    async def get_word(self, translation_code: str, original: str) -> Optional[WordDC]:
        word_model: WordModel = await WordModel.query \
            .where(and_(WordModel.translation_code == translation_code,
                        WordModel.original == original)) \
            .gino.first()
        if not word_model:
            return None
        return word_model.as_dataclass()

    async def get_word_by_id(self, word_id: int) -> WordDC:
        word_model: WordModel = await WordModel.query \
            .where(WordModel.id == word_id) \
            .gino.first()
        return word_model.as_dataclass()
