from dataclasses import dataclass
from typing import Any

import orjson
from aiogram.utils.callback_data import CallbackDataFilter


@dataclass
class BaseCallbackData:
    loc = ""

    def validate(self) -> None:
        pass

    def dump(self) -> str:
        self.validate()
        return orjson.dumps(self.__dict__).decode()

    def as_dict(self) -> dict:
        # dataclass' asdict very slow
        return self.__dict__

    @classmethod
    def filter(cls) -> CallbackDataFilter:
        return CallbackDataFilter(cls, dict(loc=cls.loc))

    @classmethod
    def parse(cls, data: str) -> dict[str, Any]:
        return orjson.loads(data)


@dataclass
class Stub(BaseCallbackData):
    loc: str = "stub"


@dataclass
class Delete(BaseCallbackData):
    loc: str = "del"


@dataclass
class Notify(BaseCallbackData):
    text_id: int
    loc: str = "ntf"


@dataclass
class MainMenu(BaseCallbackData):
    new: bool = False
    loc: str = "mm"


@dataclass
class SelectNativeLanguage(BaseCallbackData):
    native: str
    loc: str = "snl"


@dataclass
class SelectForeignLanguage(BaseCallbackData):
    native: str
    foreign: str
    loc: str = "sfl"


@dataclass
class RememberWordsMenu(BaseCallbackData):
    swap: bool = False
    random: bool = True
    loc: str = "memw"


@dataclass
class RememberWordsQuestion(BaseCallbackData):
    i: int = 0
    mem: bool = False  # remembered previous word
    rm: bool = False  # delete previous word
    loc: str = "memwq"

    def validate(self):
        if self.mem and self.rm:
            raise AssertionError


@dataclass
class RememberWordsAnswer(BaseCallbackData):
    i: int = 0
    sub: str = "full"  # ["full", 'examples", "idioms"]
    page: int = 0
    loc: str = "memwa"


@dataclass
class RecallWordsQuestion(RememberWordsQuestion):
    swap: bool = False
    loc: str = "recwq"

    def validate(self):
        if self.mem and self.rm:
            raise AssertionError


@dataclass
class RecallWordsAnswer(RememberWordsAnswer):
    loc: str = "recwa"


@dataclass
class AboutBot(BaseCallbackData):
    loc: str = "about"
