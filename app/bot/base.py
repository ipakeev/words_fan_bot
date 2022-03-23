import typing

from aiogram import Bot, Dispatcher

from app.bot.managers import CoroutinesManager, TasksManager
from app.bot.messenger import Messenger
from app.bot.states import StateAccessor

if typing.TYPE_CHECKING:
    from app.web.app import Application
    from app.web.config import Config
    from app.store.store import Store

config: "Config"
store: "Store"
states: StateAccessor
messenger: Messenger
coroutines: CoroutinesManager
tasks: TasksManager
dp: Dispatcher
bot: Bot


def register_handlers(app: "Application", dispatcher: Dispatcher):
    global config, store, states, messenger, coroutines, tasks, dp, bot
    config = app.config
    store = app.store
    states = StateAccessor(app)
    messenger = Messenger(app, dispatcher.bot, states)
    coroutines = CoroutinesManager(app)
    tasks = TasksManager(app)
    dp = dispatcher
    bot = dp.bot

    import app.bot.handlers as h1
    _ = h1
