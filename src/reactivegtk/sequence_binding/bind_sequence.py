from collections.abc import Iterator, Sequence
from functools import singledispatch
from typing import Callable, TypeVar, overload, Any

import gi

from reactivegtk.state import State
from reactivegtk.lifecycle import watch
from reactivegtk.sequence_binding.diff import diff_update

gi.require_version("Gtk", "4.0")
gi.require_version("GObject", "2.0")
gi.require_version("GLib", "2.0")
from gi.repository import Gtk  # type: ignore # noqa: E402

ItemT = TypeVar("ItemT")
KeyT = TypeVar("KeyT", bound=Any)


@overload
def bind_sequence(
    container: Gtk.ListBox, items: State[Sequence[ItemT]], *, key_fn: Callable[[ItemT], KeyT] = id
) -> Callable[[Callable[[ItemT], Gtk.ListBoxRow]], None]: ...


@overload
def bind_sequence(
    container: Gtk.Box, items: State[Sequence[ItemT]], *, key_fn: Callable[[ItemT], KeyT] = id
) -> Callable[[Callable[[ItemT], Gtk.Widget]], None]: ...


@overload
def bind_sequence(
    container: Gtk.FlowBox, items: State[Sequence[ItemT]], *, key_fn: Callable[[ItemT], KeyT] = id
) -> Callable[[Callable[[ItemT], Gtk.FlowBoxChild]], None]: ...


def bind_sequence(
    container: Gtk.Widget, items: State[Sequence[ItemT]], *, key_fn: Callable[[ItemT], KeyT] = id
) -> Callable[[Callable[[ItemT], Any]], None]:
    """Bind a sequence state to a GTK container using efficient diff updates."""

    def decorator(item_factory: Callable[[ItemT], Any]) -> None:
        # Keep track of current state
        current_items: Sequence[ItemT] = tuple()

        # Container adapter to interface with diff_update
        class ContainerAdapter:
            def __init__(self, container: Gtk.Widget):
                self.container = container
                self._widget_by_key: dict[KeyT, Gtk.Widget] = {}

            def get_items(self) -> Iterator[Gtk.Widget]:
                """Get current widgets in order."""
                child = self.container.get_first_child()
                while child:
                    yield child
                    child = child.get_next_sibling()

            def remove_widget(self, widget: Gtk.Widget) -> None:
                """Remove widget from container."""
                remove_widget(self.container, widget)
                # Remove from our tracking dict
                key_to_remove = None
                for key, tracked_widget in self._widget_by_key.items():
                    if tracked_widget is widget:
                        key_to_remove = key
                        break
                if key_to_remove is not None:
                    del self._widget_by_key[key_to_remove]

            def insert_widget(self, widget: Gtk.Widget, position: int) -> None:
                """Insert widget at position."""
                insert_widget_at(self.container, widget, position)

            def create_widget(self, item: ItemT) -> Gtk.Widget:
                """Create and track a new widget for an item."""
                widget = item_factory(item)
                key = key_fn(item)
                self._widget_by_key[key] = widget
                return widget

            def get_widget_for_key(self, key: KeyT) -> Gtk.Widget | None:
                """Get tracked widget for a key."""
                return self._widget_by_key.get(key)

            def track_widget(self, key: KeyT, widget: Gtk.Widget) -> None:
                """Track a widget by its key."""
                self._widget_by_key[key] = widget

        adapter = ContainerAdapter(container)

        def sync_items():
            """Sync container using efficient diff algorithm."""
            nonlocal current_items
            new_items = tuple(items.value)

            def widget_factory(item: ItemT) -> Gtk.Widget:
                return adapter.create_widget(item)

            def find_widget_by_key(
                widgets: Sequence[Gtk.Widget], old_items: Sequence[ItemT], target_key: KeyT
            ) -> Gtk.Widget | None:
                """Find widget corresponding to key in old items."""
                for i, old_item in enumerate(old_items):
                    if key_fn(old_item) == target_key and i < len(widgets):
                        return widgets[i]
                return None

            # Use diff_update to efficiently sync the container
            diff_update(
                container=adapter,
                old_source=current_items,
                new_source=new_items,
                key_func=key_fn,
                factory=widget_factory,
                remove=lambda container_adapter, widget: container_adapter.remove_widget(widget),
                insert=lambda container_adapter, widget, pos: container_adapter.insert_widget(
                    widget, pos
                ),
                get_container_items=lambda container_adapter: tuple(container_adapter.get_items()),
            )

            current_items = new_items

        # Set up the watch
        @watch(container, items, init=True)
        def _():
            sync_items()

    return decorator


@singledispatch
def insert_widget_at(container: Gtk.Widget, widget: Gtk.Widget, index: int) -> None:
    """Insert widget at specific index."""
    raise NotImplementedError(f"bind_sequence not implemented for {type(container).__name__}")


@insert_widget_at.register
def _(container: Gtk.ListBox, widget: Gtk.Widget, index: int) -> None:
    """Insert widget at index in ListBox."""
    if widget.get_parent() is not None:
        widget.unparent()
    container.insert(widget, index)


@insert_widget_at.register
def _(container: Gtk.Box, widget: Gtk.Widget, index: int) -> None:
    """Insert widget at index in Box."""
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
    """Insert widget at index in FlowBox."""
    if widget.get_parent() is not None:
        widget.unparent()
    container.insert(widget, index)


@singledispatch
def remove_widget(container: Gtk.Widget, widget: Gtk.Widget) -> None:
    """Remove widget from container."""
    widget.unparent()


@remove_widget.register
def _(container: Gtk.ListBox, widget: Gtk.Widget) -> None:
    """Remove widget from ListBox."""
    container.remove(widget)
    if widget.get_parent() is not None:
        widget.unparent()


@remove_widget.register
def _(container: Gtk.FlowBox, widget: Gtk.Widget) -> None:
    """Remove widget from FlowBox."""
    container.remove(widget)
    if widget.get_parent() is not None:
        widget.unparent()
