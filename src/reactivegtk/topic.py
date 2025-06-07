import weakref
from typing import Callable, Generic, TypeVar, cast
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("GObject", "2.0")
gi.require_version("GLib", "2.0")
from gi.repository import GLib, GObject  # type: ignore # noqa: E402

from reactivegtk.state import Connection

T = TypeVar("T")


class _TopicData(GObject.GObject, Generic[T]):
    """Internal GObject to handle topic events."""

    value: T = cast(T, GObject.Property(type=object))

    def __init__(self):
        super().__init__()


class Topic(Generic[T]):
    """A pub-sub topic that always notifies subscribers when messages are published."""

    def __init__(self):
        self._gobject: _TopicData[T] = _TopicData()
        self._connections: weakref.WeakSet[Connection] = weakref.WeakSet()

    def publish(self, message: T) -> None:
        """Publish a message to all subscribers."""

        @GLib.idle_add
        def _():
            # Always emit, regardless of previous value
            self._gobject.value = message
            self._gobject.emit("notify::value")

    def subscribe(self, callback: Callable[[T], None]) -> "Connection":
        """Subscribe to messages on this topic."""

        def on_notify(*args):
            callback(self._gobject.value)

        connection_id = self._gobject.connect("notify::value", on_notify)
        connection = Connection(self._gobject, connection_id)
        self._connections.add(connection)
        return connection

    def connect(self, signal_name: str, callback: Callable) -> int:
        """Connect to the topic's signals (delegates to internal GObject)."""
        return self._gobject.connect(signal_name, callback)

    def disconnect(self, connection_id: int) -> None:
        """Disconnect a signal connection."""
        self._gobject.disconnect(connection_id)

    def cleanup(self):
        """Cleanup all connections and references."""
        # Disconnect all connections
        for connection in list(self._connections):
            if connection.is_valid():
                connection.disconnect()
        self._connections.clear()

    def __repr__(self) -> str:
        return f"Topic()"
