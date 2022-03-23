import asyncio
import typing
from collections.abc import Awaitable

from aiogram.utils.exceptions import InvalidQueryID

from app.base.accessor import BaseAccessor
from app.logger import logger
from app.utils import generate_uuid

if typing.TYPE_CHECKING:
    from app.web.app import Application


class CoroutinesManager(BaseAccessor):

    def __init__(self, app: "Application"):
        super().__init__(app)
        self.app = app
        self.queues: dict[int, asyncio.Queue] = {}
        self.qw_tasks: list[asyncio.Task] = []
        self.is_running = False

    async def connect(self):
        self.is_running = True

    async def disconnect(self):
        self.is_running = False
        for task in self.qw_tasks:
            await task

    async def queue_worker(self, queue: asyncio.Queue):
        seconds = self.app.config.common.queue_worker_sleep
        while self.is_running:
            while not queue.empty():
                coro = await queue.get()
                try:
                    await coro
                except InvalidQueryID:
                    logger.warning("InvalidQueryID")
                except Exception as e:
                    logger.exception(e)
                    raise e
            await asyncio.sleep(seconds)

    def get_queue(self, user_id: int) -> asyncio.Queue:
        queue = self.queues.get(user_id)
        if queue is None:
            queue = asyncio.Queue()
            self.queues[user_id] = queue
            qw_task = asyncio.create_task(self.queue_worker(queue))
            self.qw_tasks.append(qw_task)
        return queue

    async def add(self, user_id: int, coro: Awaitable) -> None:
        await self.get_queue(user_id).put(coro)


class TasksManager(BaseAccessor):
    gc_task: asyncio.Task

    def __init__(self, app: "Application"):
        super().__init__(app)
        self.tasks: dict[str, asyncio.Task] = {}
        self.is_running = False

    async def connect(self):
        self.is_running = True
        self.gc_task = asyncio.create_task(self.garbage_collector())

    async def disconnect(self):
        self.is_running = False
        while self.tasks:
            uid, task = self.tasks.popitem()
            if task.done() or task.cancelled():
                continue
            await task
        if not self.gc_task.done():
            await self.gc_task

    async def garbage_collector(self):
        seconds = self.app.config.common.tasks_gc_sleep
        while self.is_running:
            for uid in list(self.tasks.keys()):
                task = self.tasks.get(uid)
                if task.done() or task.cancelled():
                    del self.tasks[uid]
            await asyncio.sleep(seconds)

    def schedule_task(self, coro: Awaitable[None], delay=0.0) -> str:
        async def task():
            if delay > 0.0:
                await asyncio.sleep(delay)
            try:
                await coro
            except InvalidQueryID:
                logger.warning("InvalidQueryID")
            except Exception as e:
                logger.exception(e)
                raise e

        uid = generate_uuid()
        self.tasks[uid] = asyncio.create_task(task())
        return uid

    def cancel_task(self, uid: str):
        task = self.tasks.get(uid)
        if task:
            task.cancel()
