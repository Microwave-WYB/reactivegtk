import weakref
from typing import Any, Callable, Generic, TypeVar, cast

import gi

from reactivegtk.connection import Connection

gi.require_version("Gtk", "4.0")
gi.require_version("GObject", "2.0")
gi.require_version("GLib", "2.0")
from gi.repository import GLib, GObject  # type: ignore # noqa: E402

T = TypeVar("T")
U = TypeVar("U")
R = TypeVar("R")


class _StateData(GObject.GObject, Generic[T]):
    """Internal GObject to hold the actual state value."""

    value: T = cast(T, GObject.Property(type=object))

    def __init__(self, initial_value: T):
        super().__init__()
        self.value = initial_value


class State(Generic[T]):
    """A reactive state container that uses composition instead of inheritance."""

    def __init__(self, value: T):
        self._gobject: _StateData[T] = _StateData(value)
        self._connections: weakref.WeakSet[Connection] = weakref.WeakSet()
        self._bindings: weakref.WeakSet[GObject.Binding] = weakref.WeakSet()
        self._derived_states: weakref.WeakSet["State"] = weakref.WeakSet()

    @property
    def value(self) -> T:
        """Get the current state value."""
        return self._gobject.value

    def map(self, mapper: Callable[[T], R], /) -> "State[R]":
        """Create a new derived state that transforms this state's value."""
        # Create the derived state with initial transformed value
        derived = MutableState(mapper(self.value))

        # Connect to this state's changes
        def on_change(*args):
            derived.set(mapper(self.value))

        connection_id = self._gobject.connect("notify::value", on_change)
        connection = Connection(self._gobject, connection_id)

        # Track the connection in both states
        self._connections.add(connection)
        derived._connections.add(connection)

        # Track the derived state for cleanup
        self._derived_states.add(derived)

        return derived

    def filter(self, predicate: Callable[[T], bool], /) -> "State[T | None]":
        """Create a new derived state that only emits values matching the predicate."""
        # Create the derived state with initial value if it matches
        initial_value = self.value if predicate(self.value) else None
        derived = MutableState(initial_value)

        # Connect to this state's changes
        def on_change(*args):
            if predicate(self.value):
                derived.set(self.value)
            else:
                derived.set(None)

        connection_id = self._gobject.connect("notify::value", on_change)
        connection = Connection(self._gobject, connection_id)

        # Track the connection in both states
        self._connections.add(connection)
        derived._connections.add(connection)

        # Track the derived state for cleanup
        self._derived_states.add(derived)

        return derived

    def bind(
        self,
        target_object: GObject.Object,
        target_property: str,
    ) -> GObject.Binding:
        """Bind this state's value to a target object's property."""
        flags = GObject.BindingFlags.SYNC_CREATE
        biniding = self._gobject.bind_property(
            "value",
            target_object,
            target_property,
            flags,
            lambda binding, value: value,
            lambda binding, value: value,
        )
        self._bindings.add(biniding)
        return biniding

    def watch(
        self,
        callback: Callable[[T], R],
    ) -> Callable[[T], R]:
        """Subscribe to changes in this state, ignoring the connection ID."""
        self.connect(callback)
        return callback

    def connect(
        self,
        callback: Callable[[T], Any],
    ) -> int:
        """Connect a callback to changes in this state."""
        callback(self.value)
        connection_id = self._gobject.connect("notify::value", lambda *_: callback(self.value))
        connection = Connection(self._gobject, connection_id)
        self._connections.add(connection)
        return connection_id

    def disconnect(self, connection_id: int) -> None:
        """Disconnect a signal connection."""
        self._gobject.disconnect(connection_id)

    def cleanup(self):
        """Cleanup all connections and references."""
        # Cleanup all derived states first
        for derived_state in self._derived_states:
            if derived_state is not None:
                derived_state.cleanup()
        self._derived_states.clear()

        for binding in self._bindings:
            binding.unbind()

        # Disconnect any remaining connections
        for connection in self._connections:
            if connection.is_valid():
                connection.disconnect()
        self._connections.clear()

    def __repr__(self) -> str:
        return f"State({self.value!r})"


class MutableState(State[T]):
    def set(self, value: T) -> None:
        """Set the state value and notify listeners."""

        @GLib.idle_add
        def _():
            if self._gobject.value != value:
                self._gobject.value = value

    def update(self, fn: Callable[[T], T]) -> None:
        """Update the state value using a function."""
        self.set(fn(self.value))

    def twoway_bind(
        self,
        target_object: GObject.Object,
        target_property: str,
    ) -> GObject.Binding:
        """Create a two-way binding with a target object's property."""
        flags = GObject.BindingFlags.SYNC_CREATE | GObject.BindingFlags.BIDIRECTIONAL
        binding = self._gobject.bind_property(
            "value",
            target_object,
            target_property,
            flags,
            lambda binding, value: value,
            lambda binding, value: value,
        )
        self._bindings.add(binding)
        return binding
