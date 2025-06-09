import gi

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
        
        self.name = ""
        
        # Create and configure entry widget
        # WARNING: Circular reference memory leak!
        # HelloWorldWidget → self.entry → signal connection → self._on_entry_* → HelloWorldWidget
        # This widget will never be garbage collected without manual cleanup
        self.entry = Gtk.Entry(placeholder_text="Enter your name...", width_request=200)
        self.entry.connect("activate", self._on_entry_activate)
        self.entry.connect("changed", self._on_entry_changed)
        self.append(self.entry)
        
        # Create and configure label widget
        self.label = Gtk.Label(css_classes=["title-1"])
        self._update_label()
        self.append(self.label)
    
    def _on_entry_activate(self, entry: Gtk.Entry) -> None:
        print(f"Entry activated with text: {self.name}")
    
    def _on_entry_changed(self, entry: Gtk.Entry) -> None:
        self.name = entry.get_text()
        self._update_label()
    
    def _update_label(self) -> None:
        text = f"Hello, {self.name}!" if self.name else "Hello, ...!"
        self.label.set_text(text)


class HelloWorldApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.example.HelloWorld")
        self.connect("activate", self._on_activate)
    
    def _on_activate(self, app: Adw.Application) -> None:
        window = Adw.ApplicationWindow(application=app, title="Hello ReactiveGTK")
        window.set_content(HelloWorldWidget())
        window.present()


if __name__ == "__main__":
    HelloWorldApp().run([])