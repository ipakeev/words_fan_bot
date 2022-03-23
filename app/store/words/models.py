import typing
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional

from sqlalchemy.dialects.postgresql import JSONB

from app.database.database import db

if typing.TYPE_CHECKING:
    import sqlalchemy as db


@dataclass
class WordDC:
    translation_code: str
    original: str
    transcription: list[str]
    translations: list[str]
    past_indefinite: list[str]
    past_participle: list[str]
    noun_plural: list[str]
    examples: list[list[str]]
    idioms: list[list[str]]
    audio_id: Optional[str]
    added_at: datetime
    id: Optional[int] = None

    def as_model(self) -> "WordModel":
        return WordModel(translation_code=self.translation_code,
                         original=self.original,
                         transcription=self.transcription,
                         translations=self.translations,
                         past_indefinite=self.past_indefinite,
                         past_participle=self.past_participle,
                         noun_plural=self.noun_plural,
                         examples=self.examples,
                         idioms=self.idioms,
                         audio_id=self.audio_id,
                         added_at=self.added_at)

    def as_dict(self) -> dict:
        return dict(translation_code=self.translation_code,
                    original=self.original,
                    profile=dict(transcription=self.transcription,
                                 translations=self.translations,
                                 past_indefinite=self.past_indefinite,
                                 past_participle=self.past_participle,
                                 noun_plural=self.noun_plural,
                                 examples=self.examples,
                                 idioms=self.idioms),
                    audio_id=self.audio_id,
                    added_at=self.added_at)


class WordModel(db.Model):
    __tablename__ = "words"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    translation_code = db.Column(db.String, nullable=False)
    original = db.Column(db.String, nullable=False)

    profile = db.Column(JSONB, nullable=False)
    transcription = db.ArrayProperty()
    translations = db.ArrayProperty()
    past_indefinite = db.ArrayProperty()
    past_participle = db.ArrayProperty()
    noun_plural = db.ArrayProperty()
    examples = db.ArrayProperty()
    idioms = db.ArrayProperty()

    audio_id = db.Column(db.String, nullable=True)
    added_at = db.Column(db.DateTime(timezone=True), nullable=False)

    _idx1 = db.Index("words_idx_translation_code_original", "translation_code", "original", unique=True)

    def as_dataclass(self) -> WordDC:
        return WordDC(translation_code=self.translation_code,
                      original=self.original,
                      transcription=self.transcription,
                      translations=self.translations,
                      past_indefinite=self.past_indefinite,
                      past_participle=self.past_participle,
                      noun_plural=self.noun_plural,
                      examples=self.examples,
                      idioms=self.idioms,
                      audio_id=self.audio_id,
                      added_at=self.added_at,
                      id=self.id)
