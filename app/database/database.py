import typing

from aioredis import Redis
from gino import Gino
from sqlalchemy.engine.url import URL

from app.base.accessor import BaseAccessor

if typing.TYPE_CHECKING:
    from app.web.app import Application

db = Gino()


def register_models() -> None:
    import app.store.users.models as m1
    import app.store.words.models as m2
    _ = m1
    _ = m2


class Database(BaseAccessor):
    redis: Redis

    def __init__(self, app: "Application"):
        super().__init__(app)
        self.db = db
        register_models()

    async def connect(self) -> None:
        config = self.app.config.database
        url = URL(drivername=config.driver,
                  username=config.username,
                  password=config.password,
                  host=config.host,
                  port=config.port,
                  database=config.database)
        await self.db.set_bind(url)
        await self.db.gino.create_all()

        self.redis = Redis(host=self.app.config.redis.host,
                           port=self.app.config.redis.port,
                           db=self.app.config.redis.db)

    async def disconnect(self) -> None:
        await self.db.pop_bind().close()
        await self.redis.close()
