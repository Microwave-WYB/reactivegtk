import gi

from reactivegtk import MutableState, WidgetLifecycle
from reactivegtk.dsl import apply, ui

gi.require_versions(
    {
        "Gtk": "4.0",
        "Adw": "1",
    }
)
from gi.repository import Adw, Gtk  # type: ignore # noqa: E402


def Counter() -> Gtk.Widget:
    count = MutableState(0)

    return ui(
        box := Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6,
            valign=Gtk.Align.CENTER,
            halign=Gtk.Align.CENTER,
        ),
        lifecycle := WidgetLifecycle(box),
        apply(box.append).foreach(
            ui(
                label := Gtk.Label(css_classes=["title-1"]),
                count.map(str).bind(label, "label"),
            ),
            ui(
                hbox := Gtk.Box(
                    orientation=Gtk.Orientation.HORIZONTAL,
                    spacing=12,
                    halign=Gtk.Align.CENTER,
                    valign=Gtk.Align.CENTER,
                ),
                apply(hbox.append).foreach(
                    ui(
                        button := Gtk.Button(
                            icon_name="list-remove-symbolic",
                            css_classes=["circular"],
                            valign=Gtk.Align.CENTER,
                        ),
                        lifecycle.subscribe(button, "clicked")(
                            lambda _: count.update(lambda x: x - 1)
                        ),
                    ),
                    ui(
                        button := Gtk.Button(
                            icon_name="view-refresh-symbolic",
                            css_classes=["circular", "destructive-action"],
                            valign=Gtk.Align.CENTER,
                        ),
                        lifecycle.subscribe(button, "clicked")(lambda _: count.set(0)),
                    ),
                    ui(
                        button := Gtk.Button(
                            icon_name="list-add-symbolic",
                            css_classes=["circular"],
                            valign=Gtk.Align.CENTER,
                        ),
                        lifecycle.subscribe(button, "clicked")(
                            lambda _: count.update(lambda x: x + 1)
                        ),
                    ),
                ),
            ),
        ),
    )


def Window(app: Adw.Application) -> Adw.ApplicationWindow:
    return ui(
        window := Adw.ApplicationWindow(application=app, title="Counter App"),
        window.set_content(
            ui(
                view := Adw.ToolbarView(top_bar_style=Adw.ToolbarStyle.FLAT),
                view.add_top_bar(
                    Adw.HeaderBar(
                        title_widget=Adw.WindowTitle(title="Counter App"),
                        show_start_title_buttons=False,
                    )
                ),
                view.set_content(
                    Gtk.WindowHandle(
                        child=Counter(),
                    ),
                ),
            )
        ),
        window.set_default_size(300, 400),
    )


def App() -> Adw.Application:
    app = Adw.Application(application_id="com.example.CounterApp")

    @lambda f: app.connect("activate", f)
    def _(*_):
        window = Window(app)
        window.set_application(app)
        window.present()

    return app


App().run([])
