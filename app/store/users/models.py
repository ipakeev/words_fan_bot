import typing
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional

from sqlalchemy.dialects.postgresql import JSONB

from app.database.database import db
from app.store.words.models import WordModel

if typing.TYPE_CHECKING:
    import sqlalchemy as db


@dataclass
class UserDC:
    id: int
    is_bot: bool
    username: str
    first_name: str
    last_name: str
    language_code: str
    joined_at: datetime

    def as_model(self) -> "UserModel":
        return UserModel(id=self.id,
                         is_bot=self.is_bot,
                         username=self.username,
                         first_name=self.first_name,
                         last_name=self.last_name,
                         language_code=self.language_code,
                         joined_at=self.joined_at)

    def as_dict(self) -> dict:
        return asdict(self)


class UserModel(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    is_bot = db.Column(db.Boolean, nullable=False)
    username = db.Column(db.String, nullable=False)
    first_name = db.Column(db.String, nullable=False)
    last_name = db.Column(db.String, nullable=False)
    language_code = db.Column(db.String, nullable=False)
    joined_at = db.Column(db.DateTime(timezone=True), nullable=False)

    def as_dataclass(self) -> UserDC:
        return UserDC(id=self.id,
                      is_bot=self.is_bot,
                      username=self.username,
                      first_name=self.first_name,
                      last_name=self.last_name,
                      language_code=self.language_code,
                      joined_at=self.joined_at)


@dataclass
class UserLangDC:
    user_id: int
    translation_code: str

    def as_model(self) -> "UserLangModel":
        return UserLangModel(user_id=self.user_id,
                             translation_code=self.translation_code)

    def as_dict(self) -> dict:
        return asdict(self)


class UserLangModel(db.Model):
    __tablename__ = "user_langs"

    user_id = db.Column(db.ForeignKey(UserModel.id, ondelete="CASCADE"), primary_key=True)
    translation_code = db.Column(db.String, nullable=False, primary_key=True)

    def as_dataclass(self) -> UserLangDC:
        return UserLangDC(user_id=self.user_id,
                          translation_code=self.translation_code)


@dataclass
class UserWordDC:
    user_id: int
    translation_code: str
    word_id: int
    added_at: datetime
    remembered_at: Optional[datetime] = None
    next_show_original: Optional[datetime] = None
    next_show_translation: Optional[datetime] = None
    n_shown_original: int = 0
    n_shown_translation: int = 0
    id: Optional[int] = None

    def as_model(self) -> "UserWordModel":
        return UserWordModel(user_id=self.user_id,
                             translation_code=self.translation_code,
                             word_id=self.word_id,
                             added_at=self.added_at,
                             remembered_at=self.remembered_at,
                             next_show_original=self.next_show_original,
                             next_show_translation=self.next_show_translation,
                             n_shown_original=self.n_shown_original,
                             n_shown_translation=self.n_shown_translation)

    def as_dict(self) -> dict:
        result = asdict(self)
        del result["id"]
        return result


class UserWordModel(db.Model):
    __tablename__ = "user_words"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.ForeignKey(UserModel.id, ondelete="CASCADE"), nullable=False)
    translation_code = db.Column(db.String, nullable=False)
    word_id = db.Column(db.ForeignKey(WordModel.id, ondelete="CASCADE"), nullable=False)
    added_at = db.Column(db.DateTime(timezone=True), nullable=False)
    remembered_at = db.Column(db.DateTime(timezone=True), nullable=True)
    next_show_original = db.Column(db.DateTime(timezone=True), nullable=True)
    next_show_translation = db.Column(db.DateTime(timezone=True), nullable=True)
    n_shown_original = db.Column(db.Integer, nullable=False)
    n_shown_translation = db.Column(db.Integer, nullable=False)

    _unique_constraint = db.UniqueConstraint("user_id", "word_id")

    def as_dataclass(self) -> UserWordDC:
        return UserWordDC(user_id=self.user_id,
                          translation_code=self.translation_code,
                          word_id=self.word_id,
                          added_at=self.added_at,
                          remembered_at=self.remembered_at,
                          next_show_original=self.next_show_original,
                          next_show_translation=self.next_show_translation,
                          n_shown_original=self.n_shown_original,
                          n_shown_translation=self.n_shown_translation,
                          id=self.id)
