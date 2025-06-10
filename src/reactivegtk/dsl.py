from typing import Any, Callable, Generic, TypeVar

from typing_extensions import TypeVarTuple, Unpack

T = TypeVar("T")
Ts = TypeVarTuple("Ts")


def build(target: T, action: Callable[[T], Any], /) -> T:
    """
    Apply actions to the target

    >>> build([], lambda lst: lst.append(1))
    [1]
    """
    action(target)
    return target


def do(*_: Any, ret: T = None) -> T:
    """
    Allow eager execution of actions, return ret if provided.

    >>> do(print("Hello"), ret=42)
    Hello
    42
    """
    return ret


class attempt(Generic[T]):
    def __init__(self, fn: Callable[[], T]) -> None:
        self._fn = fn

    def catch(self, handler: Callable[[Exception], T]) -> "T":
        """
        Catch exceptions and return a new attempt with the result of the handler.

        >>> attempt(lambda: 1 / 0).catch(lambda e: -1)
        -1
        """
        try:
            return self._fn()
        except Exception as e:
            return handler(e)

    def orelse(self, fallback: T) -> T:
        """
        Return the result of the function execution or the fallback value if an exception occurred.

        >>> attempt(lambda: 1 / 0).orelse(-1)
        -1
        """
        try:
            return self._fn()
        except Exception:
            return fallback

    def __call__(self) -> T:
        """
        Return the result of the function execution or raise the exception if it occurred.
        >>> attempt(lambda: 1)()
        1
        >>> attempt(lambda: 1 / 0)()
        Traceback (most recent call last):
        ...
        ZeroDivisionError: division by zero
        """
        return self._fn()


class apply(Generic[T]):
    """
    >>> nums = []
    >>> _ = apply(nums.append).foreach(1, 2, 3)
    >>> nums
    [1, 2, 3]
    """

    def __init__(self, fn: Callable[[T], Any]) -> None:
        self._fn = fn

    def foreach(self, *items: T) -> None:
        """Apply the function to each item in the iterable."""
        for item in items:
            self._fn(item)


class unpack_apply(Generic[Unpack[Ts]]):
    """
    >>> nums = []
    >>> _ = unpack_apply(nums.append).foreach((1,), (2,), (3,))
    >>> nums
    [1, 2, 3]
    """

    def __init__(self, fn: Callable[[Unpack[Ts]], Any]) -> None:
        self._fn = fn

    def foreach(self, *items: tuple[Unpack[Ts]]) -> None:
        for item in items:
            self._fn(*item)
