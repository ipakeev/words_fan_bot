import pytest

from app.web.config import Langs


@pytest.fixture
def langs():
    return Langs()


class TestConfig:

    def test_langs(self, langs):
        assert langs.get_language_code("English") == "en"
        assert langs.get_language_by_code("en") == "English"

    def test_translation_code(self, langs):
        assert langs.get_translation_code(langs.get_language_code("Русский"),
                                          langs.get_language_code("English")) == "en-ru"

    def test_get_native_language(self, langs):
        assert langs.get_native_language("en-ru") == "Русский"

    def test_get_foreign_language(self, langs):
        assert langs.get_foreign_language("en-ru") == "English"

    def test_get_native_language_code(self, langs):
        assert langs.get_native_language_code("en-ru") == "ru"

    def test_get_foreign_language_code(self, langs):
        assert langs.get_foreign_language_code("en-ru") == "en"

    def test_get_translation_text(self, langs):
        assert langs.get_translation_text("en-ru") == "English  ➡  Русский"
        assert langs.get_translation_text("en-ru", reverse=True) == "Русский  ➡  English"
