import gi

from reactivegtk import MutableState, WidgetLifecycle, into

gi.require_versions({"Gtk": "4.0", "Adw": "1"})
from gi.repository import Adw, Gtk  # type: ignore # noqa: E402


def HelloWorld():
    # Create reactive state
    name = MutableState("")

    # Create container widget
    box = Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL,
        spacing=12,
        halign=Gtk.Align.CENTER,
        valign=Gtk.Align.CENTER,
    )

    # Widget lifecycle management
    lifecycle = WidgetLifecycle(box)

    # Add entry for name input
    @into(box.append)
    def _():
        entry = Gtk.Entry(placeholder_text="Enter your name...", width_request=200)

        name.twoway_bind(entry, "text")

        @lifecycle.subscribe(entry, "activate")
        def _(_):
            print(f"Entry activated with text: {name.value}")

        return entry

    # Add label that automatically updates when name changes
    @into(box.append)
    def _():
        label = Gtk.Label(css_classes=["title-1"])
        name.map(lambda x: f"Hello, {x}!" if x else "Hello, ...!").bind(label, "label")
        return label

    return box


# Create and run the app
def App():
    app = Adw.Application(application_id="com.example.HelloWorld")

    @lambda f: app.connect("activate", f)
    def _(*_):
        window = Adw.ApplicationWindow(application=app, title="Hello ReactiveGTK")
        window.set_content(HelloWorld())
        window.present()

    return app


if __name__ == "__main__":
    App().run([])
