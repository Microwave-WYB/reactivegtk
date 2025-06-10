from collections.abc import Callable, Iterable
from typing import Any, Generic, TypeVar

from typing_extensions import TypeVarTuple, Unpack

InnerT = TypeVar("InnerT")
Ts = TypeVarTuple("Ts")


class apply(Generic[InnerT]):
    class unpack(Generic[Unpack[Ts]]):
        def __init__(self, outer_fn: Callable[[Unpack[Ts]], Any]) -> None:
            self.outer_fn = outer_fn

        def __call__(self, inner_fn: Callable[[], tuple[Unpack[Ts]]]) -> Callable[[], tuple[Unpack[Ts]]]:
            """
            Call a function immediately with the unpacked result of decorated function.

            >>> nums = [1, 2, 3]
            >>> def append_max_of(a: int, b: int) -> None:
            ...     nums.append(max(a, b))

            >>> @apply.unpack(append_max_of)
            ... def _() -> tuple[int, int]:
            ...     return 4, 5
            >>> nums
            [1, 2, 3, 5]
            """
            result = inner_fn()
            self.outer_fn(*result)
            return lambda: result

        def foreach(
            self, inner_fn: Callable[[], Iterable[tuple[Unpack[Ts]]]]
        ) -> Callable[[], Iterable[tuple[Unpack[Ts]]]]:
            """
            Transform a decorator to work on each item in an iterable.

            >>> nums = [1, 2, 3]
            >>> def append_max_of(a: int, b: int) -> None:
            ...     nums.append(max(a, b))

            >>> @apply.unpack(append_max_of).foreach
            ... def _() -> Iterable[tuple[int, int]]:
            ...     return [(4, 5), (6, 7), (8, 9)]
            >>> nums
            [1, 2, 3, 5, 7, 9]
            """
            result = inner_fn()
            for item in result:
                self.outer_fn(*item)
            return lambda: result

    def __init__(self, outer_fn: Callable[[InnerT], Any]) -> None:
        self.outer_fn = outer_fn

    def __call__(self, inner_fn: Callable[[], InnerT]) -> Callable[[], InnerT]:
        """
        Call a function immediately with the result of decorated function.

        >>> nums = [1, 2, 3]
        >>> @apply(nums.append)
        ... def _():
        ...     return 4
        >>> nums
        [1, 2, 3, 4]
        """
        result = inner_fn()
        self.outer_fn(result)
        return lambda: result

    def foreach(self, inner_fn: Callable[[], Iterable[InnerT]]) -> Callable[[], Iterable[InnerT]]:
        """
        Transform a decorator to work on each item in an iterable.

        >>> nums = [1, 2, 3]
        >>> @apply(nums.append).foreach
        ... def _():
        ...     return [4, 5, 6]
        >>> nums
        [1, 2, 3, 4, 5, 6]
        """
        result = inner_fn()
        for item in result:
            self.outer_fn(item)
        return lambda: result
