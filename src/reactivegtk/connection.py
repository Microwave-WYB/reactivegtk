import weakref
from typing import TYPE_CHECKING
import gi

gi.require_version("GObject", "2.0")
from gi.repository import GObject  # type: ignore # noqa: E402

if TYPE_CHECKING:
    pass


class Connection:
    """Wrapper for GObject connections that can be managed and cleaned up."""

    def __init__(self, obj: GObject.Object, connection_id: int):
        self._obj_ref = weakref.ref(obj)
        self._connection_id = connection_id
        self._disconnected = False

    def disconnect(self):
        """Disconnect the signal connection."""
        if not self._disconnected:
            obj = self._obj_ref()
            if obj is not None:
                obj.disconnect(self._connection_id)
            self._disconnected = True

    def is_valid(self) -> bool:
        """Check if the connection is still valid."""
        return not self._disconnected and self._obj_ref() is not None