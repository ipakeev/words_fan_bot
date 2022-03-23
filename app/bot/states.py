from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional

import orjson
from aioredis import Redis

from app.base.accessor import BaseAccessor


@dataclass
class PreviousMessageInfo:
    user_id: int
    message_id: int
    audio_id: Optional[str]
    posted_at: datetime


@dataclass
class WordsNavigationState:
    swap: bool
    random: bool


class States:
    previous_msg = "words_pmi"
    words_navigation = "words_nav"
    words_remember_idx = "words_mem_idx"
    words_recall_idx = "words_rec_idx"


class StateAccessor(BaseAccessor):
    redis: Redis

    async def connect(self) -> None:
        self.redis = self.app.store.database.redis

    async def set_previous_msg_info(self, data: PreviousMessageInfo):
        await self.redis.set(States.previous_msg + str(data.user_id), orjson.dumps(asdict(data)))

    async def delete_previous_msg_info(self, user_id: int):
        await self.redis.delete(States.previous_msg + str(user_id))

    async def get_previous_msg_info(self, user_id: int) -> Optional[PreviousMessageInfo]:
        data = await self.redis.get(States.previous_msg + str(user_id))
        if data is None:
            return None
        return PreviousMessageInfo(**orjson.loads(data))

    async def set_words_remember_state(self, user_id: int, data: WordsNavigationState):
        await self.redis.set(States.words_navigation + str(user_id), orjson.dumps(asdict(data)))

    async def get_words_remember_state(self, user_id: int) -> WordsNavigationState:
        data = await self.redis.get(States.words_navigation + str(user_id))
        return WordsNavigationState(**orjson.loads(data))

    async def set_words_remember_order(self, user_id: int, idx: list[int]):
        await self.redis.set(States.words_remember_idx + str(user_id), orjson.dumps(idx))

    async def get_words_remember_order(self, user_id: int) -> list[int]:
        data = await self.redis.get(States.words_remember_idx + str(user_id))
        return orjson.loads(data)

    async def set_words_recall_order(self, user_id: int, idx: list[tuple[int, bool]]):
        await self.redis.set(States.words_recall_idx + str(user_id), orjson.dumps(idx))

    async def get_words_recall_order(self, user_id: int) -> list[tuple[int, bool]]:
        data = await self.redis.get(States.words_recall_idx + str(user_id))
        return orjson.loads(data)
