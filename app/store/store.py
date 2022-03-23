import typing
from dataclasses import dataclass

from app.database.database import Database
from app.store.users.accessor import UserAccessor
from app.store.words.accessor import WordAccessor
from app.web.parser import YandexTranslator

if typing.TYPE_CHECKING:
    from app.web.app import Application


@dataclass
class Store:
    database: Database
    users: UserAccessor
    words: WordAccessor
    translator: YandexTranslator


def setup_store(app: "Application") -> None:
    app.store = Store(
        database=Database(app),
        users=UserAccessor(app),
        words=WordAccessor(app),
        translator=YandexTranslator(app),
    )
