import asyncio
from collections.abc import Awaitable, Callable, Sequence
from typing import Any, Final, Generic, TypeVar, overload

import gi

from reactivegtk.connection import Connection
from reactivegtk.effect import Effect
from reactivegtk.lifecycle._lifecycle_manager import LifecycleManager
from reactivegtk.signal import Signal
from reactivegtk.state import State

gi.require_version("Gtk", "4.0")
gi.require_version("GObject", "2.0")
gi.require_version("GLib", "2.0")
from gi.repository import GObject, Gtk  # type: ignore # noqa: E402

T = TypeVar("T")
R = TypeVar("R")


def effect(
    event_loop: asyncio.AbstractEventLoop,
) -> Callable[[Callable[[], Awaitable]], Callable[..., None]]:
    """Create a launcher function that ignores arguments and launches the effect."""

    def decorator(func: Callable[[], Awaitable[T]]) -> Callable[..., None]:
        """Decorator to create a launcher function that can be called with any arguments."""
        effect = Effect(func, event_loop)

        def launcher(*args) -> None:
            """Launch the effect, ignoring all arguments."""
            effect.launch()

        return launcher

    return decorator


def watch(
    widget: Gtk.Widget, state: State[T], init: bool = False
) -> Callable[[Callable[[T], Any]], Callable[[T], Any]]:
    """Bind a callback to signals with proper lifecycle management."""

    def decorator(func: Callable[[T], Any]) -> Callable[[T], Any]:
        """Decorator to create a callback that can be called with the object."""
        lifecycle_manager = LifecycleManager.get_instance(widget)

        if init:
            func(state.value)

        lifecycle_manager.add_connection_ref(state.watch(func))
        return func

    return decorator


@overload
def subscribe(
    widget: Gtk.Widget, signal: Signal[T], /
) -> Callable[[Callable[[T], None]], Callable[[T], None]]: ...


@overload
def subscribe(
    widget: Gtk.Widget, obj: GObject.Object, signal_name: str, /
) -> Callable[[Callable[[Sequence], None]], Callable[[Sequence], None]]: ...


def subscribe(
    widget: Gtk.Widget, *args
) -> (
    Callable[[Callable[[T], None]], Callable[[T], None]]
    | Callable[[Callable[[Sequence], None]], Callable[[Sequence], None]]
):
    """Subscribe to a topic with proper lifecycle management."""

    match args:
        case (Signal(),):
            signal = args[0]

            def signal_decorator(func: Callable[[T], None]) -> Callable[[T], None]:
                """Decorator to create a subscription that can be called with the object."""
                lifecycle_manager = LifecycleManager.get_instance(widget)
                connection = signal.subscribe(func)

                def on_message(obj, message):
                    func(message)

                connection_id = signal._object.connect("message", on_message)
                connection = Connection(signal._object, connection_id)
                signal._connections.add(connection)
                lifecycle_manager.add_connection_ref(connection)
                return func

            return signal_decorator

        case (obj, signal_name) if isinstance(obj, GObject.Object) and isinstance(
            signal_name, str
        ):

            def obj_name_decorator(
                func: Callable[[Sequence], None],
            ) -> Callable[[Sequence], None]:
                """Decorator to create a subscription that can be called with the object."""
                lifecycle_manager = LifecycleManager.get_instance(widget)
                signal_instance = Signal.from_obj_and_name(obj, signal_name)
                connection = signal_instance.subscribe(func)
                signal_instance._connections.add(connection)
                lifecycle_manager.add_connection_ref(connection)
                lifecycle_manager.add_signal(signal_instance)
                return func

            return obj_name_decorator

        case _:
            raise TypeError(
                "Invalid signal type. Must be Signal or (GObject.Object, str) sequence."
            )


WidgetT = TypeVar("WidgetT", bound=Gtk.Widget, covariant=True)
T = TypeVar("T")


class WidgetLifecycle(Generic[WidgetT]):
    def __init__(self, widget: WidgetT):
        self.widget: Final[WidgetT] = widget

    def watch(
        self, state: State[T], init: bool = False
    ) -> Callable[[Callable[[T], Any]], Callable[[T], Any]]:
        """Create a watcher that can respond to State changes."""

        return watch(self.widget, state, init)

    @overload
    def subscribe(
        self, signal: Signal[T], /
    ) -> Callable[[Callable[[T], None]], Callable[[T], None]]: ...
    @overload
    def subscribe(
        self, obj: GObject.Object, signal_name: str, /
    ) -> Callable[[Callable[[Sequence], None]], Callable[[Sequence], None]]: ...

    def subscribe(
        self, *args
    ) -> (
        Callable[[Callable[[T], None]], Callable[[T], None]]
        | Callable[[Callable[[Sequence], None]], Callable[[Sequence], None]]
    ):
        """Subscribe to a signal with proper lifecycle management."""
        return subscribe(self.widget, *args)

    def effect[T](
        self, event_loop: asyncio.AbstractEventLoop
    ) -> Callable[[Callable[[], Awaitable]], Callable[..., None]]:
        """Create a launcher function that ignores arguments and launches the effect."""
        return effect(event_loop)

    def on_cleanup(self) -> Callable[[Callable[[], None]], Callable[[], None]]:
        """Subscribe to cleanup events for this widget."""

        def decorator(func: Callable[[], None]) -> Callable[[], None]:
            lifecycle_manager = LifecycleManager.get_instance(self.widget)
            lifecycle_manager.add_cleanup_callback(func)
            return func

        return decorator
