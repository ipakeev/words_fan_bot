import typing
from typing import Optional

from aiogram import types, Bot
from aiogram.utils.exceptions import MessageNotModified

from app.bot.states import StateAccessor, PreviousMessageInfo
from app.logger import logger
from app.utils import now

if typing.TYPE_CHECKING:
    from app.web.app import Application


class Messenger:

    def __init__(self, app: "Application", bot: Bot, states: StateAccessor):
        self.app = app
        self.bot = bot
        self.states = states
        self._previous_msg_info_cache: dict[int, PreviousMessageInfo] = {}

    async def set_previous_msg_info(self, user_id: int, message_id: int, audio_id: Optional[str]):
        data = PreviousMessageInfo(user_id=user_id,
                                   message_id=message_id,
                                   audio_id=audio_id,
                                   posted_at=now())
        self._previous_msg_info_cache[user_id] = data
        await self.states.set_previous_msg_info(data)

    async def get_previous_msg_info(self, user_id: int) -> Optional[PreviousMessageInfo]:
        result = self._previous_msg_info_cache.get(user_id)
        if result is None:
            result = await self.states.get_previous_msg_info(user_id)
        return result

    async def delete_previous(self, user_id: int):
        info = await self.get_previous_msg_info(user_id)
        if info is None:
            return
        await self.bot.delete_message(info.user_id, info.message_id)
        await self.states.delete_previous_msg_info(user_id)

    async def send(self,
                   user_id: int,
                   text: str,
                   audio_id: Optional[str] = None,
                   keyboard: Optional[types.InlineKeyboardMarkup] = None,
                   delete_previous=True):
        text = text[:1024]
        if delete_previous:
            await self.delete_previous(user_id)

        if audio_id:
            msg = await self.bot.send_audio(user_id, audio_id, caption=text, reply_markup=keyboard)
        else:
            msg = await self.bot.send_message(user_id, text, reply_markup=keyboard)
        await self.set_previous_msg_info(user_id, msg.message_id, audio_id=audio_id)
        logger.debug(f"sent msg to {user_id}")

    async def edit(self,
                   user_id: int,
                   text: str,
                   audio_id: Optional[str] = None,
                   keyboard: Optional[types.InlineKeyboardMarkup] = None):
        text = text[:1024]
        info = await self.get_previous_msg_info(user_id)
        if info is None or info.audio_id != audio_id:
            return await self.send(user_id, text, audio_id=audio_id, keyboard=keyboard)

        try:
            if audio_id:
                await self.bot.edit_message_caption(user_id, info.message_id, caption=text, reply_markup=keyboard)
            else:
                await self.bot.edit_message_text(text, user_id, info.message_id, reply_markup=keyboard)
            logger.debug(f"edited msg to {user_id}")
        except MessageNotModified:
            logger.warning("Message is not modified")
