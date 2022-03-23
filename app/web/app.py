import pathlib
from collections.abc import Callable, Awaitable
from typing import Union

from app.logger import logger
from app.store.store import Store, setup_store
from app.web.config import Config, setup_config


class Application:
    config: Config
    store: Store

    def __init__(self):
        self.on_connect: list[Callable[[], Awaitable[None]]] = []
        self.on_disconnect: list[Callable[[], Awaitable[None]]] = []

    async def connect(self, *args, **kwargs):
        logger.info("connecting to the app")
        for func in self.on_connect:
            await func()

    async def disconnect(self, *args, **kwargs):
        logger.info("disconnecting from the app")
        for func in self.on_disconnect:
            await func()


def setup_app(config_file: Union[str, pathlib.Path]) -> Application:
    app = Application()
    setup_config(app, config_file)
    setup_store(app)
    return app
