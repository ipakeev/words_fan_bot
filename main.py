import pathlib

from aiogram import Bot, Dispatcher, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import ParseMode

from app.bot.base import register_handlers

from app.web.app import setup_app


def main():
    config_file = pathlib.Path(__file__).resolve().parent / "config.yml"
    app = setup_app(config_file)

    bot = Bot(app.config.bot.token, parse_mode=ParseMode.HTML)
    dp = Dispatcher(bot, storage=MemoryStorage(), throttling_rate_limit=0.5)
    register_handlers(app, dp)
    executor.start_polling(dp, skip_updates=True,
                           on_startup=app.connect,
                           on_shutdown=app.disconnect)


if __name__ == "__main__":
    main()
