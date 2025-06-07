import asyncio
import weakref
from collections.abc import Awaitable
from typing import Any, Callable, Final, Generic, TypeVar, overload
import gi

from reactivegtk.state import State
from reactivegtk.connection import Connection
from reactivegtk.signal import Signal
from reactivegtk.effect import Effect

gi.require_version("Gtk", "4.0")
gi.require_version("GObject", "2.0")
gi.require_version("GLib", "2.0")
from gi.repository import GObject, Gtk  # type: ignore # noqa: E402

T = TypeVar("T")
R = TypeVar("R")


class LifecycleManager:
    """Manages the lifecycle of widgets and their associated resources."""

    # Class variable to track lifecycle managers
    _instances: weakref.WeakKeyDictionary[Gtk.Widget, "LifecycleManager"] = (
        weakref.WeakKeyDictionary()
    )

    def __init__(self, widget: Gtk.Widget):
        self._widget_ref = weakref.ref(widget)
        self._connections: list[Connection] = []
        self._effects: list["Effect"] = []
        self._cleanup_callbacks: list[Callable[[], None]] = []

        # Connect to destroy signal for definitive cleanup
        # Using weak reference to avoid circular dependency
        def cleanup_callback(*args):
            self.cleanup()

        # Store connection but don't add to managed connections to avoid circular ref
        widget.connect("destroy", cleanup_callback)

    def add_connection(
        self, obj: GObject.Object, signal_name: str, callback: Callable
    ) -> Connection:
        """Add a managed connection."""
        connection_id = obj.connect(signal_name, callback)
        connection = Connection(obj, connection_id)
        self._connections.append(connection)

        # If it's a State object, add to its weak set
        if isinstance(obj, State):
            obj._connections.add(connection)

        return connection

    def add_connection_ref(self, connection: Connection):
        """Add a connection reference for management."""
        self._connections.append(connection)

    def add_side_effect(self, side_effect: "Effect"):
        """Add a managed side effect."""
        self._effects.append(side_effect)

    def add_cleanup_callback(self, callback: Callable[[], None]):
        """Add a cleanup callback."""
        self._cleanup_callbacks.append(callback)

    def cleanup(self):
        """Clean up all managed resources."""
        # Cancel all side effects
        for side_effect in self._effects:
            side_effect.cancel()
        self._effects.clear()

        # Disconnect all connections
        for connection in self._connections:
            connection.disconnect()
        self._connections.clear()

        # Run cleanup callbacks
        for callback in self._cleanup_callbacks:
            try:
                callback()
            except Exception as e:
                print(f"Error in cleanup callback: {e}")
        self._cleanup_callbacks.clear()

    @classmethod
    def get_instance(cls, widget: Gtk.Widget) -> "LifecycleManager":
        """Get the lifecycle manager instance for a widget."""
        if widget not in cls._instances:
            cls._instances[widget] = cls(widget)
        return cls._instances[widget]


def effect(
    widget: Gtk.Widget,
    event_loop: asyncio.AbstractEventLoop,
    *signals: tuple[GObject.Object, str] | State,
) -> Callable[[Callable[[], Awaitable[T]]], "Effect[T]"]:
    """Bind the side effect to a widget with proper lifecycle management."""

    def decorator(func: Callable[[], Awaitable[T]]) -> "Effect[T]":
        """Decorator to create a SideEffect that can be called with the object."""
        side_effect = Effect(func, event_loop)
        lifecycle_manager = LifecycleManager.get_instance(widget)
        lifecycle_manager.add_side_effect(side_effect)

        # Launch immediately
        side_effect.launch()

        # Connect to signals
        for signal in signals:
            if isinstance(signal, State):
                obj, signal_name = signal._gobject, "notify::value"
            else:
                obj, signal_name = signal

            lifecycle_manager.add_connection(obj, signal_name, lambda *_: side_effect.launch())

        return side_effect

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
) -> Callable[[Callable[[tuple], None]], Callable[[tuple], None]]: ...


def subscribe(
    widget: Gtk.Widget, *args
) -> (
    Callable[[Callable[[T], None]], Callable[[T], None]]
    | Callable[[Callable[[tuple], None]], Callable[[tuple], None]]
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

        case (obj, signal_name) if isinstance(obj, GObject.Object) and isinstance(signal_name, str):

            def obj_name_decorator(func: Callable[[tuple], None]) -> Callable[[tuple], None]:
                """Decorator to create a subscription that can be called with the object."""
                lifecycle_manager = LifecycleManager.get_instance(widget)
                signal_instance = Signal.from_obj_and_name(obj, signal_name)
                connection = signal_instance.subscribe(func)
                signal_instance._connections.add(connection)
                lifecycle_manager.add_connection_ref(connection)
                return func

            return obj_name_decorator

        case _:
            raise TypeError("Invalid signal type. Must be Signal or (GObject.Object, str) tuple.")


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
    ) -> Callable[[Callable[[tuple], None]], Callable[[tuple], None]]: ...

    def subscribe(
        self, *args
    ) -> (
        Callable[[Callable[[T], None]], Callable[[T], None]]
        | Callable[[Callable[[tuple], None]], Callable[[tuple], None]]
    ):
        """Subscribe to a signal with proper lifecycle management."""
        return subscribe(self.widget, *args)

    def effect[T](
        self, *signals: tuple[GObject.Object, str] | State, event_loop: asyncio.AbstractEventLoop
    ) -> Callable[[Callable[[], Awaitable[T]]], Effect[T]]:
        """Create and launch an effect that can respond to GTK signals."""
        return effect(self.widget, event_loop, *signals)
