from functools import partial

import gi

from reactivegtk import MutableState, apply

gi.require_versions(
    {
        "Gtk": "4.0",
        "Adw": "1",
    }
)
from gi.repository import Adw, Gtk  # type: ignore # noqa: E402


def Counter() -> Gtk.Widget:
    count = MutableState(0)

    box = Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL,
        spacing=6,
        valign=Gtk.Align.CENTER,
        halign=Gtk.Align.CENTER,
    )

    @apply(box.append)
    def _():
        label = Gtk.Label(css_classes=["title-1"])
        count.map(str).bind(label, "label")
        return label

    @apply(box.append)
    def _():
        hbox = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=12,
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER,
        )

        @apply(hbox.append).foreach
        def _():
            button_remove = Gtk.Button(
                icon_name="list-remove-symbolic",
                css_classes=["circular"],
                valign=Gtk.Align.CENTER,
            )
            button_remove.connect("clicked", lambda *_: count.update(lambda x: x - 1))

            button_reset = Gtk.Button(
                icon_name="view-refresh-symbolic",
                css_classes=["circular", "destructive-action"],
                valign=Gtk.Align.CENTER,
            )
            button_reset.connect("clicked", lambda *_: count.set(0))

            button_add = Gtk.Button(
                icon_name="list-add-symbolic",
                css_classes=["circular"],
                valign=Gtk.Align.CENTER,
            )
            button_add.connect("clicked", lambda *_: count.update(lambda x: x + 1))

            return (
                button_remove,
                button_reset,
                button_add,
            )

        return hbox

    return box


def Window(app: Adw.Application) -> Adw.ApplicationWindow:
    window = Adw.ApplicationWindow(
        application=app,
        title="Counter App",
        default_width=300,
        default_height=400,
    )

    @apply(window.set_content)
    def _():
        toolbar_view = Adw.ToolbarView(top_bar_style=Adw.ToolbarStyle.FLAT)

        @apply(toolbar_view.add_top_bar)
        def _():
            header_bar = Adw.HeaderBar(
                title_widget=Adw.WindowTitle(title="Counter App"),
                show_start_title_buttons=False,
            )
            toolbar_view.set_content(Gtk.WindowHandle(child=Counter()))
            return header_bar

        @apply(toolbar_view.set_content)
        def _():
            return Gtk.WindowHandle(child=Counter())

        return toolbar_view

    return window


def App() -> Adw.Application:
    app = Adw.Application(application_id="com.example.CounterApp")

    @partial(app.connect, "activate")
    def _(*_):
        window = Window(app)
        window.present()

    return app


App().run(None)
