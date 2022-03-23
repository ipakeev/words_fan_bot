import pathlib
import typing
from dataclasses import dataclass
from typing import Union

import yaml

if typing.TYPE_CHECKING:
    from app.web.app import Application

LANGUAGES = [
    ("en", "English"),
    ("ru", "Русский"),
]


class Langs:

    def __init__(self):
        self.codes = sorted([i[0] for i in LANGUAGES])
        self.languages = sorted([i[1] for i in LANGUAGES])
        self._code_langs = {i[0]: i[1] for i in LANGUAGES}
        self._lang_codes = {i[1]: i[0] for i in LANGUAGES}

    def get_language_code(self, language: str) -> str:
        return self._lang_codes[language]

    def get_language_by_code(self, lang_code: str) -> str:
        return self._code_langs[lang_code]

    def get_translation_code(self, native_lang_code: str, foreign_lang_code: str) -> str:
        return f"{foreign_lang_code}-{native_lang_code}"

    def get_native_language(self, translation_code: str) -> str:
        return self.get_language_by_code(self.get_native_language_code(translation_code))

    def get_foreign_language(self, translation_code: str) -> str:
        return self.get_language_by_code(self.get_foreign_language_code(translation_code))

    def get_native_language_code(self, translation_code: str) -> str:
        return translation_code.split("-")[1]

    def get_foreign_language_code(self, translation_code: str) -> str:
        return translation_code.split("-")[0]

    def get_translation_text(self, translation_code: str, reverse=False) -> str:
        s = [self.get_language_by_code(i) for i in translation_code.split("-")]
        if reverse:
            s = s[::-1]
        return "  ➡  ".join(s)


@dataclass
class DatabaseConfig:
    driver: str
    username: str
    password: str
    host: str
    port: int
    database: str


@dataclass
class RedisConfig:
    host: str
    port: int
    db: int


@dataclass
class BotConfig:
    token: str
    admin_id: int
    temp_chat_id: int


@dataclass
class TranslatorConfig:
    work: bool
    headless: bool


@dataclass
class CommonConfig:
    queue_worker_sleep: float
    tasks_gc_sleep: int


@dataclass
class Config:
    langs: Langs
    database: DatabaseConfig
    redis: RedisConfig
    bot: BotConfig
    translator: TranslatorConfig
    common: CommonConfig


def setup_config(app: "Application", config_file: Union[str, pathlib.Path]):
    with open(config_file) as f:
        raw_yaml = yaml.safe_load(f)

    app.config = Config(
        langs=Langs(),
        database=DatabaseConfig(**raw_yaml["database"]),
        redis=RedisConfig(**raw_yaml["redis"]),
        bot=BotConfig(**raw_yaml["bot"]),
        translator=TranslatorConfig(**raw_yaml["translator"]),
        common=CommonConfig(**raw_yaml["common"]),
    )
