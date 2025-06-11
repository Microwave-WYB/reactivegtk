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
E = TypeVar("E", bound=type[Exception])


class catcher(Generic[P, T, E]):
    def __init__(
        self,
        _exc_type: E,
        fn: Callable[P, T],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        self.exc_type = _exc_type
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def fallback(self, value: T) -> T:
        try:
            return self.fn(*self.args, **self.kwargs)
        except self.exc_type:
            return value

    def recover(self, handler: Callable[[E], T]) -> T:
        try:
            return self.fn(*self.args, **self.kwargs)
        except self.exc_type as e:
            return handler(e)


class attempt(Generic[P, T]):
    def __init__(self, fn: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> None:
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def __call__(self) -> T:
        """
        >>> attempt(lambda: 1 / 0)()
        Traceback (most recent call last):
        ...
        ZeroDivisionError: division by zero
        """
        return self.fn(*self.args, **self.kwargs)

    def catch(self, exc_type: E) -> catcher[P, T, E]:
        """
        Catch specific exceptions and handle them.

        >>> attempt(lambda: 1 / 0).catch(ZeroDivisionError).orelse(-1)
        -1
        >>> attempt(lambda: 1 / 0).catch(ZeroDivisionError).recover(lambda e: -1)
        -1
        """
        return catcher(exc_type, self.fn, *self.args, **self.kwargs)
