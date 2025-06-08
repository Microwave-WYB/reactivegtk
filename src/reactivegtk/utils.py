import asyncio
import threading
from collections.abc import Callable, Iterable
from typing import TypeVar, TypeVarTuple

InnerT = TypeVar("InnerT")
OuterT = TypeVar("OuterT")


def into(
    outer_fn: Callable[[InnerT], OuterT],
) -> Callable[[Callable[[], InnerT]], Callable[[], InnerT]]:
    """
    Call a function immediately with the result of decorated function.

    >>> nums = [1, 2, 3]
    >>> @into(nums.append)
    ... def _():
    ...     return 4
    >>> nums
    [1, 2, 3, 4]
    """

    def decorator(inner_fn: Callable[[], InnerT]) -> Callable[[], InnerT]:
        result = inner_fn()
        outer_fn(result)
        return lambda: result

    return decorator


Ts = TypeVarTuple = TypeVarTuple("Ts")


def unpack_into(
    outer_fn: Callable[[*Ts], OuterT],
) -> Callable[[Callable[[], tuple[*Ts]]], Callable[[], tuple[*Ts]]]:
    """
    Call a function immediately with the unpacked result of decorated function.

    >>> nums = [1, 2, 3]
    >>> def append_max_of(a: int, b: int) -> None:
    ...     nums.append(max(a, b))

    >>> @unpack_into(append_max_of)
    ... def _() -> tuple[int, int]:
    ...     return 4, 5
    >>> nums
    [1, 2, 3, 5]
    """

    def decorator(inner_fn: Callable[[], tuple[*Ts]]) -> Callable[[], tuple[*Ts]]:
        result = inner_fn()
        outer_fn(*result)
        return lambda: result

    return decorator


def each(
    outer_fn: Callable[[Callable[[], InnerT]], Callable[[], InnerT]],
) -> Callable[[Callable[[], Iterable[InnerT]]], Callable[[], Iterable[InnerT]]]:
    """
    Transform a decorator to work on each item in an iterable.

    >>> nums = [1, 2, 3]
    >>> @each(into(nums.append))
    ... def _():
    ...     return [4, 5, 6]
    >>> nums
    [1, 2, 3, 4, 5, 6]

    >>> nums = [1, 2, 3]
    >>> @each(unpack_into(lambda a, b: nums.append(max(a, b))))
    ... def _() -> Iterable[tuple[int, int]]:
    ...     return [(4, 5), (6, 7), (8, 9)]
    >>> nums
    [1, 2, 3, 5, 7, 9]
    """

    def decorator(
        inner_fn: Callable[[], Iterable[InnerT]],
    ) -> Callable[[], Iterable[InnerT]]:
        result = inner_fn()
        for item in result:
            # Create a function that returns this single item
            def item_func():
                return item

            # Apply the original decorator to it
            outer_fn(item_func)
        return lambda: result

    return decorator


def start_event_loop() -> tuple[asyncio.AbstractEventLoop, threading.Thread]:
    """Start the asyncio event loop in a separate thread."""
    event_loop = asyncio.new_event_loop()
    thread = threading.Thread(target=event_loop.run_forever, daemon=True)
    thread.start()
    return event_loop, thread


if __name__ == "__main__":
    # Example usage
    nums = [1, 2, 3]

    @each(into(nums.append))
    def _():
        return [4, 5, 6]
