from datetime import timedelta

from sqlalchemy import and_, or_
from sqlalchemy.dialects.postgresql import insert

from app.base.accessor import BaseAccessor
from app.store.users.models import UserDC, UserWordDC, UserModel, UserWordModel, UserLangDC, UserLangModel
from app.utils import now

recall_delay = {
    0: timedelta(days=1),
    1: timedelta(days=3),
    2: timedelta(days=7),
    3: timedelta(days=30),
    4: timedelta(days=90),
}


class UserAccessor(BaseAccessor):

    async def add_user(self, user: UserDC) -> UserDC:
        stmt = insert(UserModel).values(**user.as_dict())
        model: UserModel = await stmt.on_conflict_do_update(
            index_elements=[UserModel.id],
            set_=dict(is_bot=stmt.excluded.is_bot,
                      username=stmt.excluded.username,
                      first_name=stmt.excluded.first_name,
                      last_name=stmt.excluded.last_name,
                      language_code=stmt.excluded.language_code)
        ).returning(*UserModel).gino.model(UserModel).first()
        return model.as_dataclass()

    async def get_users(self) -> list[UserDC]:
        users: list[UserModel] = await UserModel.query.gino.all()
        return [i.as_dataclass() for i in users]

    async def add_user_lang(self, user_lang: UserLangDC) -> UserLangDC:
        stmt = insert(UserLangModel).values(**user_lang.as_dict())
        model: UserLangModel = await stmt.on_conflict_do_update(
            index_elements=[UserLangModel.user_id, UserLangModel.translation_code],
            set_=dict(translation_code=stmt.excluded.translation_code)
        ).returning(*UserLangModel).gino.model(UserLangModel).first()
        return model.as_dataclass()

    async def get_user_langs(self, user_id: int) -> list[UserLangDC]:
        models: list[UserLangModel] = await UserLangModel.query \
            .where(UserLangModel.user_id == user_id) \
            .gino.all()
        return [i.as_dataclass() for i in models]

    async def add_user_word(self, user_word: UserWordDC) -> UserWordDC:
        stmt = insert(UserWordModel).values(**user_word.as_dict())
        model: UserWordModel = await stmt.on_conflict_do_update(
            index_elements=[UserWordModel.user_id, UserWordModel.word_id],
            set_=dict(translation_code=stmt.excluded.translation_code)
        ).returning(*UserWordModel).gino.model(UserWordModel).first()
        return model.as_dataclass()

    async def count_user_words(self, user_id: int, translation_code: str) -> int:
        db = self.app.store.database.db
        return await db.select([db.func.count()]) \
            .where(and_(UserWordModel.user_id == user_id,
                        UserWordModel.translation_code == translation_code)) \
            .gino.scalar()

    async def count_to_remember_user_words(self, user_id: int, translation_code: str) -> int:
        db = self.app.store.database.db
        return await db.select([db.func.count()]) \
            .where(and_(UserWordModel.user_id == user_id,
                        UserWordModel.translation_code == translation_code,
                        UserWordModel.remembered_at == None)) \
            .gino.scalar()

    async def count_to_recall_user_words(self, user_id: int, translation_code: str) -> int:
        db = self.app.store.database.db
        n_show_originals = await db.select([db.func.count()]) \
            .where(and_(UserWordModel.user_id == user_id,
                        UserWordModel.translation_code == translation_code,
                        UserWordModel.remembered_at != None,
                        UserWordModel.next_show_original <= now())) \
            .gino.scalar()
        n_show_translations = await db.select([db.func.count()]) \
            .where(and_(UserWordModel.user_id == user_id,
                        UserWordModel.translation_code == translation_code,
                        UserWordModel.remembered_at != None,
                        UserWordModel.next_show_translation <= now())) \
            .gino.scalar()
        return n_show_originals + n_show_translations

    async def get_user_words(self, user_id: int, translation_code: str) -> list[UserWordDC]:
        user_words: list[UserWordModel] = await UserWordModel.query \
            .where(and_(UserWordModel.user_id == user_id,
                        UserWordModel.translation_code == translation_code)) \
            .gino.all()
        return [i.as_dataclass() for i in user_words]

    async def set_remembered(self, user_id: int, word_id: int) -> UserWordDC:
        model: UserWordModel = await UserWordModel.update \
            .values(remembered_at=now(),
                    next_show_original=now() + recall_delay[0],
                    next_show_translation=now() + recall_delay[0] + timedelta(days=1)) \
            .where(and_(UserWordModel.user_id == user_id,
                        UserWordModel.word_id == word_id)) \
            .returning(*UserWordModel) \
            .gino.first()
        return model.as_dataclass()

    async def set_shown_original(self, user_id: int, word_id: int) -> UserWordDC:
        user_word: UserWordModel = await UserWordModel.query \
            .where(and_(UserWordModel.user_id == user_id,
                        UserWordModel.word_id == word_id)) \
            .gino.first()

        n_shown_original = user_word.n_shown_original + 1
        next_show_original = now() + recall_delay[n_shown_original]
        model: UserWordModel = await UserWordModel.update \
            .values(next_show_original=next_show_original,
                    n_shown_original=n_shown_original) \
            .where(UserWordModel.id == user_word.id) \
            .returning(*UserWordModel) \
            .gino.first()
        return model.as_dataclass()

    async def set_shown_translation(self, user_id: int, word_id: int) -> UserWordDC:
        user_word: UserWordModel = await UserWordModel.query \
            .where(and_(UserWordModel.user_id == user_id,
                        UserWordModel.word_id == word_id)) \
            .gino.first()

        n_shown_translation = user_word.n_shown_translation + 1
        next_show_translation = now() + recall_delay[n_shown_translation]
        model: UserWordModel = await UserWordModel.update \
            .values(next_show_translation=next_show_translation,
                    n_shown_translation=n_shown_translation) \
            .where(UserWordModel.id == user_word.id) \
            .returning(*UserWordModel) \
            .gino.first()
        return model.as_dataclass()

    async def delete_word(self, user_id: int, word_id: int) -> None:
        await UserWordModel.delete \
            .where(and_(UserWordModel.user_id == user_id,
                        UserWordModel.word_id == word_id)) \
            .gino.status()

    async def get_words_to_remember(self, user_id: int, translation_code: str) -> list[UserWordDC]:
        user_words: list[UserWordModel] = await UserWordModel.query \
            .where(and_(UserWordModel.user_id == user_id,
                        UserWordModel.translation_code == translation_code,
                        UserWordModel.remembered_at == None)) \
            .gino.all()
        return [i.as_dataclass() for i in user_words]

    async def get_words_to_recall(self, user_id: int, translation_code: str) -> list[UserWordDC]:
        user_words: list[UserWordModel] = await UserWordModel.query \
            .where(and_(UserWordModel.user_id == user_id,
                        UserWordModel.translation_code == translation_code,
                        UserWordModel.remembered_at != None,
                        or_(UserWordModel.next_show_original <= now(),
                            UserWordModel.next_show_translation <= now()))) \
            .gino.all()
        return [i.as_dataclass() for i in user_words]

    async def get_ids_user_words(self, user_id: int, translation_code: str) -> list[int]:
        result = await self.app.store.database.db \
            .select([UserWordModel.word_id]) \
            .where(and_(UserWordModel.user_id == user_id,
                        UserWordModel.translation_code == translation_code)) \
            .gino.all()
        return [i[0] for i in result]

    async def get_ids_words_to_remember(self, user_id: int, translation_code: str) -> list[int]:
        result = await self.app.store.database.db \
            .select([UserWordModel.word_id]) \
            .where(and_(UserWordModel.user_id == user_id,
                        UserWordModel.translation_code == translation_code,
                        UserWordModel.remembered_at == None)) \
            .gino.all()
        return [i[0] for i in result]

    async def get_ids_original_words_to_recall(self, user_id: int, translation_code: str) -> list[int]:
        result = await self.app.store.database.db \
            .select([UserWordModel.word_id]) \
            .where(and_(UserWordModel.user_id == user_id,
                        UserWordModel.translation_code == translation_code,
                        UserWordModel.remembered_at != None,
                        UserWordModel.next_show_original <= now())) \
            .gino.all()
        return [i[0] for i in result]

    async def get_ids_translation_words_to_recall(self, user_id: int, translation_code: str) -> list[int]:
        result = await self.app.store.database.db \
            .select([UserWordModel.word_id]) \
            .where(and_(UserWordModel.user_id == user_id,
                        UserWordModel.translation_code == translation_code,
                        UserWordModel.remembered_at != None,
                        UserWordModel.next_show_translation <= now())) \
            .gino.all()
        return [i[0] for i in result]
