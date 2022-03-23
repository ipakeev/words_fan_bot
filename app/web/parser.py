import asyncio
import typing
from typing import Optional

from aiohttp import ClientSession, TCPConnector

from app.base.accessor import BaseAccessor
from app.logger import logger
from app.store.words.models import WordDC
from app.utils import now

if typing.TYPE_CHECKING:
    pass


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


class YandexTranslator(BaseAccessor):
    session: ClientSession

    async def connect(self) -> None:
        self.session = ClientSession(connector=TCPConnector(verify_ssl=False, force_close=True))

    async def disconnect(self) -> None:
        await self.session.close()

    async def get(self, url: str) -> dict:
        try:
            async with self.session.get(url) as response:
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            logger.exception(e)
            await asyncio.sleep(5.0)

    async def translate(self, translation_code: str, original: str) -> WordDC:
        logger.info(f"({translation_code}) {original}")
        url_translate = f"https://dictionary.yandex.net/dicservice.json/lookupMultiple?" \
                        f"text={original}&lang={translation_code}&flags=15783&dict={translation_code}"
        url_examples = f"https://dictionary.yandex.net/dicservice.json/queryCorpus?" \
                       f"srv=tr-text&text={original}&type&lang={translation_code}&flags=1063&src={original}" \
                       f"&chunks=1&maxlen=100&v=2"
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
