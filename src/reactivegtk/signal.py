import weakref
from typing import Any, Callable, Generic, TypeVar

import gi

from reactivegtk.connection import Connection

gi.require_version("Gtk", "4.0")
gi.require_version("GObject", "2.0")
gi.require_version("GLib", "2.0")
from gi.repository import GLib, GObject  # type: ignore # noqa: E402

T = TypeVar("T")


class _SignalData(GObject.GObject, Generic[T]):
    """Internal GObject to handle topic events."""

    __gsignals__ = {
        "message": (GObject.SIGNAL_RUN_FIRST, None, (object,)),
    }

    def __init__(self):
        super().__init__()


class Signal(Generic[T]):
    """A pub-sub topic that always notifies subscribers when messages are published."""

    def __init__(self):
        self._object: _SignalData[T] = _SignalData()
        self._connections: weakref.WeakSet[Connection] = weakref.WeakSet()

    def emit(self, message: T) -> None:
        """Publish a message to all subscribers."""

        @GLib.idle_add
        def _():
            # Always emit custom signal with message
            self._object.emit("message", message)

    def subscribe(self, callback: Callable[[T], Any]) -> "Connection":
        """Subscribe to messages on this topic."""

        def on_message(obj, message):
            if isinstance(message, tuple):
                callback(*message)
            else:
                callback(message)

        connection_id = self._object.connect("message", on_message)
        connection = Connection(self._object, connection_id)
        self._connections.add(connection)
        return connection

    def connect(self, signal_name: str, callback: Callable) -> int:
        """Connect to the topic's signals (delegates to internal GObject)."""
        return self._object.connect(signal_name, callback)

    def disconnect(self, connection_id: int) -> None:
        """Disconnect a signal connection."""
        self._object.disconnect(connection_id)

    def cleanup(self):
        """Cleanup all connections and references."""
        # Disconnect all internal signal connections
        for connection in self._connections:
            if connection.is_valid():
                connection.disconnect()
        self._connections.clear()
