# import asyncio
# import time
import typing
# from collections.abc import Callable
# from datetime import timedelta
# from functools import wraps
from typing import Optional

# import orjson
from aiohttp import ClientSession

# from selbs import Browser
# from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
#
# from app.base.accessor import BaseAccessor
from app.logger import logger
from app.store.words.models import WordDC
from app.utils import now

if typing.TYPE_CHECKING:
    from app.web.app import Application


# def catch(function=None, *,
#           exceptions=(TimeoutException, StaleElementReferenceException),
#           n_attempts=-1,
#           sleep=1.0):
#     def decorator(func: Callable):
#         @wraps(func)
#         def wrapper(*args, **kwargs):
#             self: "YandexTranslator" = args[0]
#             n_done_attempts = 0
#             while 1:
#                 n_done_attempts += 1
#                 try:
#                     return func(*args, **kwargs)
#                 except exceptions as e:
#                     # logger.exception(e)
#
#                     self.browser.refresh()
#
#                     if 0 < n_attempts <= n_done_attempts:
#                         return e
#
#                 time.sleep(sleep)
#
#         return wrapper
#
#     if function is None:
#         return decorator
#     else:
#         return decorator(function)


def get_correct_original(namespace) -> Optional[str]:
    for loc in namespace["regular"]:
        return loc["text"]


def get_translations(namespace) -> list[str]:
    result = []
    for loc in namespace["regular"]:
        for tr in loc["tr"][:5]:
            if tr["text"] not in result:
                result.append(tr["text"])
    return result


def get_exclusive(namespace) -> list[str]:
    result = []
    if "def" not in namespace:
        return result
    for loc in namespace["def"]:
        for tr in loc["tr"][:5]:
            if tr["def"] not in result:
                result.append(tr["def"])
    return result


def get_transcriptions(namespace) -> list[str]:
    result = set()
    for loc in namespace["regular"]:
        if "ts" in loc:
            result.add(loc["ts"])
    return list(result)


def get_verb_forms(namespace) -> dict:
    result = {}
    for loc in namespace["regular"]:
        if "pos" not in loc:
            continue
        if loc["pos"]["tooltip"] != "verb":
            continue
        if "prdg" not in loc:
            continue
        rows = loc["prdg"]["data"][0]["tables"][0]["rows"]
        result["indefinite"] = [i.replace("(had) ", "") for i in rows[0]]
        result["participle"] = [i.replace("(had) ", "") for i in rows[2]]
    return result


def get_noun_plural(namespace) -> list[str]:
    result = []
    for loc in namespace["regular"]:
        if "pos" not in loc:
            continue
        if loc["pos"]["tooltip"] != "noun":
            continue
        if "prdg" not in loc:
            continue
        result.append(loc["prdg"]["data"][0]["tables"][0]["rows"][0][1])
    return result


def get_idioms(namespace) -> list[list[str]]:
    result = []
    for row in namespace["result"]["examples"]:
        if row["ref"]["type"] != "idiom":
            continue
        result.append([row["src"], row["dst"]])
    return result


def get_examples(namespace) -> list[list[str]]:
    result = []
    for row in namespace["result"]["examples"]:
        if row["ref"]["type"] == "idiom":
            continue
        result.append([row["src"], row["dst"]])
    return result


# class YandexTranslator(BaseAccessor):
#     browser: Browser
#     update_task: asyncio.Task
#
#     def __init__(self, app: "Application"):
#         super().__init__(app)
#         self.is_running = False
#         self.last_activity = now() - timedelta(days=100)
#
#     async def connect(self):
#         if not self.app.config.translator.work:
#             return
#
#         self.browser = Browser()
#         self.browser.init_chrome(headless=self.app.config.translator.headless)
#         self.is_running = True
#         self.update_task = asyncio.create_task(self.update_cookies())
#
#     async def disconnect(self):
#         if not self.app.config.translator.work:
#             return
#
#         self.is_running = False
#         await self.update_task
#         self.browser.quit()
#
#     async def update_cookies(self):
#         while self.is_running:
#             if (now() - self.last_activity).total_seconds() > 60 * 60:
#                 self.browser.go(f"https://translate.yandex.ru")
#                 self.last_activity = now()
#             await asyncio.sleep(10.0)
#
#     async def translate(self, translation_code: str, original: str) -> WordDC:
#         logger.info(f"({translation_code}) {original}")
#         url_translate = f"https://dictionary.yandex.net/dicservice.json/lookupMultiple?" \
#                         f"text={original}&lang={translation_code}&flags=15783&dict={translation_code}"
#         url_examples = f"https://dictionary.yandex.net/dicservice.json/queryCorpus?" \
#                        f"srv=tr-text&text={original}&type&lang={translation_code}&flags=1063&src={original}" \
#                        f"&chunks=1&maxlen=200&v=2"
#         url_exclusive = f"https://dictionary.yandex.net/dicservice.json/lookupMultiple?" \
#                         f"srv=tr-text&text={original}&type=regular&lang={translation_code}" \
#                         f"&flags=1255&dict={translation_code}.regular"
#
#         base_namespace = orjson.loads(self.browser.request(url_translate))[translation_code]
#         translations = get_translations(base_namespace)
#         if not translations:
#             exclusive_namespace = orjson.loads(self.browser.request(url_exclusive))[translation_code]
#             exclusive_translations = get_exclusive(exclusive_namespace)
#             translations.extend(exclusive_translations)
#
#         verb_forms = get_verb_forms(base_namespace)
#
#         examples_namespace = orjson.loads(self.browser.request(url_examples))
#
#         logger.info("done")
#         return WordDC(translation_code=translation_code,
#                       original=get_correct_original(base_namespace) or original,
#                       transcription=get_transcriptions(base_namespace),
#                       translations=translations,
#                       past_indefinite=verb_forms.get("indefinite", []),
#                       past_participle=verb_forms.get("participle", []),
#                       noun_plural=get_noun_plural(base_namespace),
#                       examples=get_examples(examples_namespace)[:30],
#                       idioms=get_idioms(examples_namespace)[:30],
#                       audio_id=None,
#                       added_at=now())


class YandexTranslator:

    def __init__(self, app: "Application"):
        self.app = app

    async def get(self, url: str) -> dict:
        async with ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                return await response.json()

    async def translate(self, translation_code: str, original: str) -> WordDC:
        logger.info(f"({translation_code}) {original}")
        url_translate = f"https://dictionary.yandex.net/dicservice.json/lookupMultiple?" \
                        f"text={original}&lang={translation_code}&flags=15783&dict={translation_code}"
        url_examples = f"https://dictionary.yandex.net/dicservice.json/queryCorpus?" \
                       f"srv=tr-text&text={original}&type&lang={translation_code}&flags=1063&src={original}" \
                       f"&chunks=1&maxlen=200&v=2"
        url_exclusive = f"https://dictionary.yandex.net/dicservice.json/lookupMultiple?" \
                        f"srv=tr-text&text={original}&type=regular&lang={translation_code}" \
                        f"&flags=1255&dict={translation_code}.regular"

        base_namespace = (await self.get(url_translate))[translation_code]
        translations = get_translations(base_namespace)
        if not translations:
            exclusive_namespace = (await self.get(url_exclusive))[translation_code]
            exclusive_translations = get_exclusive(exclusive_namespace)
            translations.extend(exclusive_translations)

        verb_forms = get_verb_forms(base_namespace)

        examples_namespace = await self.get(url_examples)

        logger.info("done")
        return WordDC(translation_code=translation_code,
                      original=get_correct_original(base_namespace) or original,
                      transcription=get_transcriptions(base_namespace),
                      translations=translations,
                      past_indefinite=verb_forms.get("indefinite", []),
                      past_participle=verb_forms.get("participle", []),
                      noun_plural=get_noun_plural(base_namespace),
                      examples=get_examples(examples_namespace)[:30],
                      idioms=get_idioms(examples_namespace)[:30],
                      audio_id=None,
                      added_at=now())
