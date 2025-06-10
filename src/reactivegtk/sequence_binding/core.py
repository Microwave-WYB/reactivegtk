from collections.abc import Iterator, Sequence
from functools import singledispatch
from typing import Any, Callable, TypeVar, overload

import gi

from reactivegtk.sequence_binding._diff import diff_update
from reactivegtk.state import State

gi.require_version("Gtk", "4.0")
gi.require_version("GObject", "2.0")
gi.require_version("GLib", "2.0")
from gi.repository import Gtk  # type: ignore # noqa: E402

ItemT = TypeVar("ItemT")
KeyT = TypeVar("KeyT", bound=Any)


@overload
def bind_sequence(
    container: Gtk.ListBox,
    items: State[Sequence[ItemT]],
    *,
    key_fn: Callable[[ItemT], KeyT] = id,
) -> Callable[[Callable[[ItemT], Gtk.ListBoxRow]], None]: ...


@overload
def bind_sequence(
    container: Gtk.Box,
    items: State[Sequence[ItemT]],
    *,
    key_fn: Callable[[ItemT], KeyT] = id,
) -> Callable[[Callable[[ItemT], Gtk.Widget]], None]: ...


@overload
def bind_sequence(
    container: Gtk.FlowBox,
    items: State[Sequence[ItemT]],
    *,
    key_fn: Callable[[ItemT], KeyT] = id,
) -> Callable[[Callable[[ItemT], Gtk.FlowBoxChild]], None]: ...


def bind_sequence(
    container: Gtk.Widget,
    items: State[Sequence[ItemT]],
    *,
    key_fn: Callable[[ItemT], KeyT] = id,
) -> Callable[[Callable[[ItemT], Any]], None]:
    """Bind a sequence state to a GTK container using efficient diff updates."""

    def decorator(item_factory: Callable[[ItemT], Any]) -> None:
        # Use a dict to store mutable state
        state = {"current_items": tuple(), "widget_by_key": {}}

        def get_container_widgets() -> Iterator[Gtk.Widget]:
            """Get current widgets in container in order."""
            child = container.get_first_child()
            while child:
                yield child
                child = child.get_next_sibling()

        def remove_widget_from_container(widget: Gtk.Widget) -> None:
            """Remove widget from container and clean up tracking."""
            remove_widget(container, widget)

            # Remove from tracking dict
            for key, tracked_widget in list(state["widget_by_key"].items()):
                if tracked_widget is widget:
                    del state["widget_by_key"][key]
                    break

        def insert_widget_in_container(widget: Gtk.Widget, position: int) -> None:
            """Insert widget at position in container."""
            insert_widget_at(container, widget, position)

        def create_and_track_widget(item: ItemT) -> Gtk.Widget:
            """Create widget and track it by key."""
            widget = item_factory(item)
            state["widget_by_key"][key_fn(item)] = widget
            return widget

        def sync_items(new_items: Sequence[ItemT]):
            """Sync container using efficient diff algorithm."""

            diff_update(
                container=None,  # We don't actually need this if we pass functions directly
                old_source=state["current_items"],
                new_source=new_items,
                key_func=key_fn,
                factory=create_and_track_widget,
                remove=lambda _container, widget: remove_widget_from_container(widget),
                insert=lambda _container, widget, pos: insert_widget_in_container(widget, pos),
                get_container_items=lambda _container: tuple(get_container_widgets()),
            )

            state["current_items"] = new_items

        items.watch(sync_items, init=True)

    return decorator


@singledispatch
def insert_widget_at(container: Gtk.Widget, widget: Gtk.Widget, index: int) -> None:
    """Insert widget at specific index."""
    raise NotImplementedError(f"bind_sequence not implemented for {type(container).__name__}")


@insert_widget_at.register
def _(container: Gtk.ListBox, widget: Gtk.Widget, index: int) -> None:
    if widget.get_parent() is not None:
        widget.unparent()
    container.insert(widget, index)


@insert_widget_at.register
def _(container: Gtk.Box, widget: Gtk.Widget, index: int) -> None:
    if index == 0:
        container.prepend(widget)
    else:
        current_child = container.get_first_child()
        for _ in range(index - 1):
            if current_child:
                current_child = current_child.get_next_sibling()
            else:
                break

        if current_child:
            container.insert_child_after(widget, current_child)
        else:
            container.append(widget)


@insert_widget_at.register
def _(container: Gtk.FlowBox, widget: Gtk.Widget, index: int) -> None:
    if widget.get_parent() is not None:
        widget.unparent()
    container.insert(widget, index)


@singledispatch
def remove_widget(container: Gtk.Widget, widget: Gtk.Widget) -> None:
    """Remove widget from container."""
    widget.unparent()


@remove_widget.register
def _(container: Gtk.ListBox, widget: Gtk.Widget) -> None:
    container.remove(widget)
    if widget.get_parent() is not None:
        widget.unparent()


@remove_widget.register
def _(container: Gtk.FlowBox, widget: Gtk.Widget) -> None:
    container.remove(widget)
    if widget.get_parent() is not None:
        widget.unparent()
