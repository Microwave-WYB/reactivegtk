import gi

from reactivegtk import MutableState
from reactivegtk.dsl import apply, build, do

gi.require_versions({"Gtk": "4.0", "Adw": "1"})
from gi.repository import Adw, Gtk  # type: ignore # noqa: E402


def HelloWorld():
    # Create reactive state
    name = MutableState("")

    return build(
        Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER,
        ),
        lambda box: do(
            apply(box.append).foreach(
                build(
                    Gtk.Entry(placeholder_text="Enter your name...", width_request=200),
                    lambda entry: do(
                        name.twoway_bind(entry, "text"),
                        entry.connect(
                            "activate",
                            lambda *_: do(
                                print(f"Entry activated with text: {name.value}"),
                                print("Multiple prints are possible with do function"),
                            ),
                        ),
                    ),
                ),
                build(
                    Gtk.Label(css_classes=["title-1"]),
                    lambda label: name.map(lambda x: f"Hello, {x}!" if x else "Hello, ...!").bind(label, "label"),
                ),
            ),
        ),
    )


# Create and run the app
def App():
    return build(
        Adw.Application(application_id="com.example.HelloWorld"),
        lambda app: do(
            app.connect(
                "activate",
                lambda *_: do(
                    window := Adw.ApplicationWindow(application=app, title="Hello ReactiveGTK (Declarative)"),
                    window.set_content(HelloWorld()),
                    window.present(),
                ),
            ),
        ),
    )


if __name__ == "__main__":
    App().run([])
