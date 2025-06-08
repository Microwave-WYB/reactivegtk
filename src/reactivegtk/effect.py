import asyncio
from collections.abc import Awaitable, Callable
from typing import Generic, TypeVar

T = TypeVar("T")


class Effect(Generic[T]):
    def __init__(self, func: Callable[[], Awaitable[T]], event_loop: asyncio.AbstractEventLoop):
        self._func = func
        self._task = None
        self._event_loop = event_loop

    def cancel(self):
        """Cancel the currently running task, if any."""
        if self._task and not self._task.done():
            self._task.cancel()
        self._task = None

    async def _run(self) -> T:
        """Wrap the function call in an asyncio task."""
        return await self._func()

    def launch(self):
        """Launch the side effect in the event loop."""

        self.cancel()  # Cancel any existing task
        self._task = asyncio.run_coroutine_threadsafe(self._run(), self._event_loop)
