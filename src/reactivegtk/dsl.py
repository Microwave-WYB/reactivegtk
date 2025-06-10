from collections.abc import Callable, Iterable
from typing import Any, Generic, ParamSpec, TypeVar

from typing_extensions import TypeVarTuple, Unpack

T = TypeVar("T")
Ts = TypeVarTuple("Ts")


class apply(Generic[T]):
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

    def __init__(self, outer_fn: Callable[[T], Any]) -> None:
        self.outer_fn = outer_fn

    def __call__(self, inner_fn: Callable[[], T]) -> Callable[[], T]:
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

    def foreach(self, inner_fn: Callable[[], Iterable[T]]) -> Callable[[], Iterable[T]]:
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


P = ParamSpec("P")


class attempt(Generic[P, T]):
    def __init__(self, fn: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> None:
        """
        Attempt to call a function and return its result or None if it fails.

        >>> def divide(a: int, b: int) -> float:
        ...     return a / b

        >>> @attempt(divide, 10, 2)
        ... def _() -> float:
        ...     return 5.0
        >>> _()
        5.0

        >>> @attempt(divide, 10, 0)
        ... def _() -> float:
        ...     return None
        >>> _() is None
        True
        """
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def __call__(self) -> T:
        return self.fn(*self.args, **self.kwargs)

    def orelse(self, fallback: T) -> T:
        """
        Return the result of the function or a fallback value if it fails.

        >>> @attempt(divide, 10, 0).orelse(0.0)
        ... def _() -> float:
        ...     return 0.0
        >>> _()
        0.0
        """
        try:
            return self.fn(*self.args, **self.kwargs)
        except Exception:
            return fallback

    def catch(self, handler: Callable[[Exception], T | Exception]) -> T:
        """
        Call a handler function if the original function raises an exception.

        >>> @attempt(divide, 10, 0).catch(lambda e: -1.0)
        ... def _() -> float:
        ...     return -1.0
        >>> _()
        -1.0
        """
        try:
            return self.fn(*self.args, **self.kwargs)
        except Exception as e:
            result = handler(e)
            if isinstance(result, Exception):
                raise result
            return result
