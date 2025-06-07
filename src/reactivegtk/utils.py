import asyncio
import threading
from typing import Callable, TypeVar

InnerT = TypeVar("InnerT")
OuterT = TypeVar("OuterT")


def into(
    outer_fn: Callable[[InnerT], OuterT],
) -> Callable[[Callable[[], InnerT]], InnerT]:
    """Call a function immediately with the result of decorated function."""

    def decorator(inner_fn: Callable[[], InnerT]) -> InnerT:
        result = inner_fn()
        outer_fn(result)
        return result

    return decorator


def start_event_loop() -> tuple[asyncio.AbstractEventLoop, threading.Thread]:
    """Start the asyncio event loop in a separate thread."""
    event_loop = asyncio.new_event_loop()
    thread = threading.Thread(target=event_loop.run_forever, daemon=True)
    thread.start()
    return event_loop, thread
