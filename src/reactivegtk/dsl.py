from typing import Any, Callable, Generic, TypeVar

import gi
from typing_extensions import TypeVarTuple, Unpack

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk  # type: ignore # noqa: E402

WidgetT = TypeVar("WidgetT", bound="Gtk.Widget", covariant=True)
T = TypeVar("T")
Ts = TypeVarTuple("Ts")


def do(*actions: Any, ret: T = None) -> T:
    return ret


def ui(target: WidgetT, *actions: Any) -> WidgetT:
    return do(*actions, ret=target)


class apply(Generic[T]):
    def __init__(self, fn: Callable[[T], Any]) -> None:
        self._fn = fn

    def foreach(self, *items: T) -> None:
        """Apply the function to each item in the iterable."""
        for item in items:
            self._fn(item)


class unpack_apply(Generic[Unpack[Ts]]):
    def __init__(self, fn: Callable[[Unpack[Ts]], Any]) -> None:
        self._fn = fn

    def foreach(self, *items: tuple[Unpack[Ts]]) -> None:
        for item in items:
            self._fn(*item)
