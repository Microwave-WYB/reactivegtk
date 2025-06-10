import asyncio
from collections.abc import Awaitable, Callable
from concurrent.futures import Future
from typing import Generic, TypeVar

from typing_extensions import ParamSpec

P = ParamSpec("P")
T = TypeVar("T")


class Effect(Generic[P, T]):
    def __init__(self, func: Callable[P, Awaitable[T]], event_loop: asyncio.AbstractEventLoop):
        self._func = func
        self._task: Future[T] | None = None
        self._event_loop = event_loop

    def cancel(self) -> bool:
        """Cancel the currently running task, if any."""
        return self._task.cancel() if self._task else True

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Future[T]:
        async def run_effect() -> T:
            """Run the effect function in the event loop."""
            return await self._func(*args, **kwargs)

        self.cancel()
        self._task = asyncio.run_coroutine_threadsafe(run_effect(), self._event_loop)
        return self._task


def effect(
    event_loop: asyncio.AbstractEventLoop,
) -> Callable[[Callable[P, Awaitable[T]]], Effect[P, T]]:
    """Create a launcher function that ignores arguments and launches the effect."""

    return lambda func: Effect(func, event_loop)
