import asyncio
import multiprocessing
import os
import pathlib
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from gtts import gTTS, gTTSError

from app.logger import logger


def now() -> datetime:
    return datetime.now(tz=timezone.utc)


def generate_uuid() -> str:
    return str(uuid.uuid4())


def proc_generate_audio(foreign_lang_code: str, original: str, filename: str):
    audio = gTTS(original, lang=foreign_lang_code)
    try:
        audio.save(filename)
    except gTTSError:
        logger.warning("gTTSError")
        raise multiprocessing.TimeoutError()


class MediaGenerator:
    last_activity = now()

    @classmethod
    @asynccontextmanager
    async def generate_audio(cls, foreign_lang_code: str, original: str) -> pathlib.Path:
        await asyncio.sleep(
            max(0.0, 3.0 - (now() - cls.last_activity).total_seconds())  # to avoid flood detection
        )

        path = pathlib.Path(__file__).resolve().parent.parent / "temp"
        path.mkdir(exist_ok=True, parents=True)
        filename = path / f"{generate_uuid()}.mp3"

        while 1:
            proc = multiprocessing.Process(target=proc_generate_audio,
                                           args=(foreign_lang_code, original, str(filename)))
            proc.start()
            try:
                proc.join(timeout=2.0)
                break
            except multiprocessing.TimeoutError:
                logger.warning("gTTS process killed, starting new one")
                proc.kill()

        yield filename

        os.remove(filename)
        cls.last_activity = now()
