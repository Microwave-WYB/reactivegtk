import gi

from reactivegtk import MutableState

gi.require_versions({"Gtk": "4.0", "Adw": "1"})
from gi.repository import Adw, Gtk  # type: ignore # noqa: E402


class HelloWorldWidget(Gtk.Box):
    def __init__(self):
        super().__init__(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER,
        )

        # Use ReactiveGTK state management
        self.name = MutableState("")

        # Create and configure entry
        self.entry = Gtk.Entry(placeholder_text="Enter your name...", width_request=200)
        self.entry.connect("activate", self._on_entry_activate)
        self.append(self.entry)

        # Create label
        self.label = Gtk.Label(css_classes=["title-1"])
        self.append(self.label)

        # Set up reactive bindings
        self.name.bind_twoway(self.entry, "text")
        self.name.map(lambda x: f"Hello, {x or '...'}!").bind(self.label, "label")

    def _on_entry_activate(self, entry: Gtk.Entry) -> None:
        print(f"Entry activated with text: {self.name.value}")


class App(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.example.HelloWorld")
        self.connect("activate", self._on_activate)

    def _on_activate(self, app):
        window = Adw.ApplicationWindow(application=app, title="Hello ReactiveGTK (Imperative)")
        window.set_content(HelloWorldWidget())
        window.present()


if __name__ == "__main__":
    app = App()
    app.run([])
