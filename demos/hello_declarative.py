from functools import partial

import gi

from reactivegtk import MutableState, apply

gi.require_versions({"Gtk": "4.0", "Adw": "1"})
from gi.repository import Adw, Gtk  # type: ignore # noqa: E402


def HelloWorld():
    # Create reactive state
    name = MutableState("")

    box = Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL,
        spacing=12,
        halign=Gtk.Align.CENTER,
        valign=Gtk.Align.CENTER,
    )

    @apply(box.append)
    def _():
        entry = Gtk.Entry(placeholder_text="Enter your name...", width_request=200)
        name.bind_twoway(entry, "text")
        entry.connect(
            "activate",
            lambda: print(f"Entry activated with text: {name.value}"),
        )
        return entry

    @apply(box.append)
    def _():
        label = Gtk.Label(css_classes=["title-1"])
        name.map(lambda x: f"Hello, {x or '...'}!").bind(label, "label")

        return label

    return box


# Create and run the app
def App():
    app = Adw.Application(application_id="com.example.HelloWorld")

    @partial(app.connect, "activate")
    def _(*_):
        window = Adw.ApplicationWindow(
            application=app,
            title="Hello ReactiveGTK (Declarative)",
            content=HelloWorld(),
        )
        window.present()

    return app


if __name__ == "__main__":
    App().run([])
