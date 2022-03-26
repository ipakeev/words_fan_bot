import asyncio
import multiprocessing
import os
import pathlib
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from gtts import gTTS

from app.logger import logger


def now() -> datetime:
    return datetime.now(tz=timezone.utc)


def generate_uuid() -> str:
    return str(uuid.uuid4())


def proc_generate_audio(foreign_lang_code: str, original: str, filename: str):
    audio = gTTS(original, lang=foreign_lang_code)
    try:
        audio.save(filename)
    except Exception as e:
        logger.warning(e)


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
            # генерация аудио имеет свойство зависать на 20 секунд, а затем выдавать ошибку,
            # поэтому запускаем в отдельном процессе и ждём нужное время
            # к тому же, нам нужна асинхронность
            proc = multiprocessing.Process(target=proc_generate_audio,
                                           args=(foreign_lang_code, original, str(filename)))
            proc.start()
            try:
                proc.join(timeout=5.0)
            except multiprocessing.TimeoutError:
                logger.warning("gTTS process killed, starting new one")
            proc.kill()

            if not filename.exists() or filename.stat().st_size == 0:
                logger.warning("gTTS error, file not saved")
                continue
            break

        yield filename

        os.remove(filename)
        cls.last_activity = now()
