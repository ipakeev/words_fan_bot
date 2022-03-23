import pathlib
import typing
from unittest.mock import Mock, patch

import pytest

if typing.TYPE_CHECKING:
    from app.web.app import Application


@pytest.fixture(scope="session", autouse=True)
def browser():
    from app.web.parser import YandexTranslator
    with patch("app.web.parser.YandexTranslator", Mock(spec=YandexTranslator)):
        yield


@pytest.fixture()
async def application() -> "Application":
    from app.web.app import setup_app
    config_file = pathlib.Path(__file__).resolve().parent / "test_config.yml"
    app = setup_app(config_file)
    await app.connect()
    yield app
    await app.disconnect()


@pytest.fixture(autouse=True)
async def clear_db(application: "Application"):
    yield
    db = application.store.database.db
    await db.gino.drop_all()
    # for table in db.sorted_tables:
    #     await db.status(db.text(f"TRUNCATE {table.name} RESTART IDENTITY"))
