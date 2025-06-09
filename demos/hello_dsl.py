import gi

from reactivegtk import MutableState, WidgetLifecycle
from reactivegtk.dsl import apply, do, ui

gi.require_versions({"Gtk": "4.0", "Adw": "1"})
from gi.repository import Adw, Gtk  # type: ignore # noqa: E402


def HelloWorld():
    # Create reactive state
    name = MutableState("")

    return ui(
        box := Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER,
        ),
        lifecycle := WidgetLifecycle(box),
        apply(box.append).foreach(
            ui(
                entry := Gtk.Entry(placeholder_text="Enter your name...", width_request=200),
                name.twoway_bind(entry, "text"),
                lifecycle.subscribe(entry, "activate")(
                    lambda *_: do(
                        print(f"Entry activated with text: {name.value}"),
                        print("Entry was activated!"),
                    ),
                ),
            ),
            ui(
                label := Gtk.Label(css_classes=["title-1"]),
                name.map(lambda x: f"Hello, {x}!" if x else "Hello, ...!").bind(label, "label"),
            ),
        ),
    )


# Create and run the app
def App():
    return do(
        app := Adw.Application(application_id="com.example.HelloWorld"),
        app.connect(
            "activate",
            lambda *_: do(
                window := Adw.ApplicationWindow(application=app, title="Hello ReactiveGTK"),
                window.set_content(HelloWorld()),
                window.present(),
            ),
        ),
        ret=app,
    )


if __name__ == "__main__":
    App().run([])
