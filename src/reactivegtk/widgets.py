from collections.abc import Callable, Sequence
from typing import Any, TypeVar, overload

import gi

from reactivegtk.sequence_binding.core import bind_sequence
from reactivegtk.state import State

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk  # type: ignore # noqa: E402


def Conditional(
    state: State[bool],
    true: Gtk.Widget,
    false: Gtk.Widget,
) -> Gtk.Overlay:
    """Create a Gtk.Overlay that conditionally shows one of two widgets based on the state."""
    overlay = Gtk.Overlay()
    state.map(lambda condition: true if condition else false).bind(overlay, "child")
    return overlay


ItemT = TypeVar("ItemT")
KeyT = TypeVar("KeyT")


@overload
def ReactiveSequence(
    container: Gtk.Box,
    items: State[Sequence[ItemT]],
    factory: Callable[[ItemT], Gtk.Widget],
    *,
    key_fn: Callable[[ItemT], KeyT] = id,
) -> Gtk.Box: ...


@overload
def ReactiveSequence(
    container: Gtk.ListBox,
    items: State[Sequence[ItemT]],
    factory: Callable[[ItemT], Gtk.ListBoxRow],
    *,
    key_fn: Callable[[ItemT], KeyT] = id,
) -> Gtk.ListBox: ...


@overload
def ReactiveSequence(
    container: Gtk.FlowBox,
    items: State[Sequence[ItemT]],
    factory: Callable[[ItemT], Gtk.FlowBoxChild],
    *,
    key_fn: Callable[[ItemT], KeyT] = id,
) -> Gtk.FlowBox: ...


def ReactiveSequence(
    container,
    items: State[Sequence[ItemT]],
    factory: Callable[[ItemT], Any],
    *,
    key_fn: Callable[[ItemT], KeyT] = id,
) -> Gtk.Widget:
    """Bind a sequence state to a GTK container with efficient diff updates."""
    bind_sequence(container, items, key_fn=key_fn)(factory)
    return container
