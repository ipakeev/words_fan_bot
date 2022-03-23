import typing

if typing.TYPE_CHECKING:
    from app.web.app import Application


class BaseAccessor:

    def __init__(self, app: "Application"):
        self.app = app
        self.app.on_connect.append(self.connect)
        self.app.on_disconnect.insert(0, self.disconnect)

    async def connect(self) -> None:
        pass

    async def disconnect(self) -> None:
        pass
