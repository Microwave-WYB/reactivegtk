import gi
from reactivegtk import WidgetLifecycle, into, MutableState

gi.require_versions(
    {
        "Gtk": "4.0",
        "Adw": "1",
    }
)
from gi.repository import Gtk, Adw  # type: ignore # noqa: E402


def Counter() -> Gtk.Widget:
    mainbox = Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL,
        spacing=6,
        valign=Gtk.Align.CENTER,
        halign=Gtk.Align.CENTER,
    )
    lifecycle = WidgetLifecycle(mainbox)
    count = MutableState(0)

    @into(mainbox.append)
    def _():
        label = Gtk.Label(css_classes=["title-1"])
        count.map(str).bind(label, "label")

        return label

    @into(mainbox.append)
    def _():
        hbox = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=12,
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER,
        )

        @into(hbox.append)
        def _():
            button = Gtk.Button(
                icon_name="list-remove-symbolic",
                css_classes=["circular"],
                valign=Gtk.Align.CENTER,
            )

            @lifecycle.subscribe(button, "clicked")
            def _(_):
                count.update(lambda x: x - 1)

            return button

        @into(hbox.append)
        def _():
            button = Gtk.Button(
                icon_name="view-refresh-symbolic",
                css_classes=["circular", "destructive-action"],
                valign=Gtk.Align.CENTER,
            )

            @lifecycle.subscribe(button, "clicked")
            def _(_):
                count.set(0)

            return button

        @into(hbox.append)
        def _():
            button = Gtk.Button(
                icon_name="list-add-symbolic",
                css_classes=["circular"],
                valign=Gtk.Align.CENTER,
            )

            @lifecycle.subscribe(button, "clicked")
            def _(_):
                count.update(lambda x: x + 1)

            return button

        return hbox

    return mainbox


def Window(app: Adw.Application) -> Adw.ApplicationWindow:
    window = Adw.ApplicationWindow(application=app)

    @into(window.set_content)
    def _():
        view = Adw.ToolbarView(top_bar_style=Adw.ToolbarStyle.FLAT)
        view.add_top_bar(
            Adw.HeaderBar(
                title_widget=Adw.WindowTitle(title="Counter App"),
                show_start_title_buttons=False,
            )
        )
        view.set_content(
            Gtk.WindowHandle(
                child=Counter(),
            )
        )
        return view

    return window


def App() -> Adw.Application:
    app = Adw.Application(application_id="com.example.CounterApp")

    @lambda f: app.connect("activate", f)
    def _(*_):
        window = Window(app)
        window.set_application(app)
        window.present()

    return app


App().run([])
