import gi

from reactivegtk import MutableState, WidgetLifecycle
from reactivegtk.dsl import apply, build, do

gi.require_versions(
    {
        "Gtk": "4.0",
        "Adw": "1",
    }
)
from gi.repository import Adw, Gtk  # type: ignore # noqa: E402


def Counter() -> Gtk.Widget:
    count = MutableState(0)

    return build(
        Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6,
            valign=Gtk.Align.CENTER,
            halign=Gtk.Align.CENTER,
        ),
        lambda box: do(
            lifecycle := WidgetLifecycle(box),
            apply(box.append).foreach(
                build(
                    Gtk.Label(css_classes=["title-1"]),
                    lambda label: count.map(str).bind(label, "label"),
                ),
                build(
                    Gtk.Box(
                        orientation=Gtk.Orientation.HORIZONTAL,
                        spacing=12,
                        halign=Gtk.Align.CENTER,
                        valign=Gtk.Align.CENTER,
                    ),
                    lambda hbox: apply(hbox.append).foreach(
                        build(
                            Gtk.Button(
                                icon_name="list-remove-symbolic",
                                css_classes=["circular"],
                                valign=Gtk.Align.CENTER,
                            ),
                            lambda button: lifecycle.subscribe(button, "clicked")(
                                lambda *_: count.update(lambda x: x - 1)
                            ),
                        ),
                        build(
                            Gtk.Button(
                                icon_name="view-refresh-symbolic",
                                css_classes=["circular", "destructive-action"],
                                valign=Gtk.Align.CENTER,
                            ),
                            lambda button: lifecycle.subscribe(button, "clicked")(
                                lambda *_: count.set(0)
                            ),
                        ),
                        build(
                            Gtk.Button(
                                icon_name="list-add-symbolic",
                                css_classes=["circular"],
                                valign=Gtk.Align.CENTER,
                            ),
                            lambda button: lifecycle.subscribe(button, "clicked")(
                                lambda *_: count.update(lambda x: x + 1)
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )


def Window(app: Adw.Application) -> Adw.ApplicationWindow:
    return build(
        Adw.ApplicationWindow(application=app, title="Counter App"),
        lambda window: do(
            window.set_content(
                build(
                    Adw.ToolbarView(top_bar_style=Adw.ToolbarStyle.FLAT),
                    lambda view: do(
                        view.add_top_bar(
                            Adw.HeaderBar(
                                title_widget=Adw.WindowTitle(title="Counter App"),
                                show_start_title_buttons=False,
                            ),
                        ),
                        view.set_content(
                            Gtk.WindowHandle(
                                child=Counter(),
                            ),
                        ),
                    ),
                ),
            ),
            window.set_default_size(300, 400),
        ),
    )


def App() -> Adw.Application:
    return build(
        Adw.Application(application_id="com.example.CounterApp"),
        lambda app: app.connect(
            "activate",
            lambda *_: do(
                window := Window(app),
                window.set_application(app),
                window.present(),
            ),
        ),
    )


App().run([])
