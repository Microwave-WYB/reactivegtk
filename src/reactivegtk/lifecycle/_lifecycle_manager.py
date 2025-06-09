import weakref
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import TypeVar

import gi

from reactivegtk.connection import Connection
from reactivegtk.effect import Effect
from reactivegtk.signal import Signal
from reactivegtk.state import State

gi.require_version("Gtk", "4.0")
gi.require_version("GObject", "2.0")
gi.require_version("GLib", "2.0")
from gi.repository import GObject, Gtk  # type: ignore # noqa: E402

T = TypeVar("T")
R = TypeVar("R")


@dataclass(frozen=True)
class SignalSpec:
    """Immutable specification for a signal connection."""

    obj: GObject.Object
    signal_name: str


@dataclass(frozen=True)
class LifecycleState:
    """Immutable state representing the lifecycle of a widget."""

    connections: Sequence[Connection] = field(default_factory=tuple)
    effects: Sequence[Effect] = field(default_factory=tuple)
    signals: Sequence[Signal] = field(default_factory=tuple)
    cleanup_callbacks: Sequence[Callable[[], None]] = field(default_factory=tuple)
    cleaned_up: bool = False

    def add_connection(self, connection: Connection) -> "LifecycleState":
        """Return new state with connection added."""
        return LifecycleState(
            connections=(*self.connections, connection),
            effects=self.effects,
            signals=self.signals,
            cleanup_callbacks=self.cleanup_callbacks,
            cleaned_up=self.cleaned_up,
        )

    def add_effect(self, effect: Effect) -> "LifecycleState":
        """Return new state with effect added."""
        return LifecycleState(
            connections=self.connections,
            effects=(*self.effects, effect),
            signals=self.signals,
            cleanup_callbacks=self.cleanup_callbacks,
            cleaned_up=self.cleaned_up,
        )

    def add_signal(self, signal: Signal) -> "LifecycleState":
        """Return new state with signal added."""
        return LifecycleState(
            connections=self.connections,
            effects=self.effects,
            signals=(*self.signals, signal),
            cleanup_callbacks=self.cleanup_callbacks,
            cleaned_up=self.cleaned_up,
        )

    def add_cleanup_callback(self, callback: Callable[[], None]) -> "LifecycleState":
        """Return new state with cleanup callback added."""
        return LifecycleState(
            connections=self.connections,
            effects=self.effects,
            signals=self.signals,
            cleanup_callbacks=(*self.cleanup_callbacks, callback),
            cleaned_up=self.cleaned_up,
        )

    def mark_cleaned_up(self) -> "LifecycleState":
        """Return new state marked as cleaned up."""
        return LifecycleState(
            connections=(),
            effects=(),
            signals=(),
            cleanup_callbacks=(),
            cleaned_up=True,
        )

    def perform_cleanup(self) -> "LifecycleState":
        """Perform cleanup operations and return new cleaned up state."""
        if self.cleaned_up:
            return self

        # Execute cleanup operations (side effects)
        for callback in self.cleanup_callbacks:
            try:
                callback()
            except Exception as e:
                print(f"Error in cleanup callback: {e}")

        for effect in self.effects:
            effect.cancel()

        for signal in self.signals:
            signal.cleanup()

        for connection in self.connections:
            connection.disconnect()

        return self.mark_cleaned_up()

    def process_signal_specs(self, signals: Sequence[SignalSpec | State]) -> Sequence[SignalSpec]:
        """Convert mixed signal specifications to SignalSpec objects."""
        result = []
        for signal in signals:
            if isinstance(signal, State):
                result.append(SignalSpec(signal._gobject, "notify::value"))
            else:
                result.append(signal)
        return tuple(result)


class LifecycleManager:
    """Manages the lifecycle of widgets using immutable state transitions."""

    # Class variable to track lifecycle managers
    _instances: weakref.WeakKeyDictionary[Gtk.Widget, "LifecycleManager"] = (
        weakref.WeakKeyDictionary()
    )

    def __init__(self, widget: Gtk.Widget):
        self._widget_ref = weakref.ref(widget)
        self.state = LifecycleState()

        widget.connect("destroy", lambda *_: self.cleanup())

    def add_connection(
        self, obj: GObject.Object, signal_name: str, callback: Callable
    ) -> Connection:
        """Add a managed connection."""
        connection_id = obj.connect(signal_name, callback)
        connection = Connection(obj, connection_id)
        self.state = self.state.add_connection(connection)

        # If it's a State object, add to its weak set
        if isinstance(obj, State):
            obj._connections.add(connection)

        return connection

    def add_connection_ref(self, connection: Connection):
        """Add a connection reference for management."""
        self.state = self.state.add_connection(connection)

    def add_effect(self, side_effect: Effect):
        """Add a managed side effect."""
        self.state = self.state.add_effect(side_effect)

    def add_signal(self, signal: Signal):
        """Add a managed signal."""
        self.state = self.state.add_signal(signal)

    def add_cleanup_callback(self, callback: Callable[[], None]):
        """Add a cleanup callback."""
        self.state = self.state.add_cleanup_callback(callback)

    def trigger_cleanup(self):
        """Manually trigger cleanup."""
        if not self.state.cleaned_up:
            self.cleanup()

    def cleanup(self):
        """Clean up all managed resources."""
        self.state = self.state.perform_cleanup()

    def create_signal_connection(self, signal_spec: SignalSpec, callback: Callable) -> None:
        """Create a signal connection."""
        self.add_connection(signal_spec.obj, signal_spec.signal_name, callback)

    @classmethod
    def has_instance(cls, widget: Gtk.Widget) -> bool:
        """Check if a lifecycle manager instance exists for a widget."""
        return widget in cls._instances

    @classmethod
    def get_instance(cls, widget: Gtk.Widget) -> "LifecycleManager":
        """Get the lifecycle manager instance for a widget."""
        if widget not in cls._instances:
            manager = cls(widget)
            cls._instances[widget] = manager
        return cls._instances[widget]
