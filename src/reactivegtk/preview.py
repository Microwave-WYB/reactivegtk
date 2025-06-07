import asyncio
import gi
from reactivegtk import State, WidgetLifecycle, into, MutableState
from typing import Callable, overload

from reactivegtk.utils import start_event_loop

gi.require_versions(
    {
        "Gtk": "4.0",
        "Adw": "1",
    }
)
from gi.repository import Gtk, Adw  # type: ignore # noqa: E402


class Preview:
    """
    A preview application with navigation tabs and widget previews.
    """

    def __init__(self):
        self.widgets: dict[str, Callable[[asyncio.AbstractEventLoop], Gtk.Widget]] = {}
        self.event_loop, _ = start_event_loop()

    @overload
    def __call__(
        self, func: Callable[[asyncio.AbstractEventLoop], Gtk.Widget], /
    ) -> Callable[[asyncio.AbstractEventLoop], Gtk.Widget]:
        """
        Register a widget factory function as a decorator.

        Usage:
            preview = Preview()

            @preview
            def MyWidget(event_loop) -> Gtk.Widget: ...
        """
        ...

    @overload
    def __call__(
        self, name: str, /
    ) -> Callable[
        [Callable[[asyncio.AbstractEventLoop], Gtk.Widget]],
        Callable[[asyncio.AbstractEventLoop], Gtk.Widget],
    ]:
        """
        Register a widget factory function with a specific name.

        Usage:
            preview = Preview()

            @preview("MyWidget")
            def my_widget_factory(event_loop) -> Gtk.Widget: ...
        """
        ...

    def __call__(
        self, name: Callable[[asyncio.AbstractEventLoop], Gtk.Widget] | str, /
    ) -> (
        Callable[[asyncio.AbstractEventLoop], Gtk.Widget]
        | Callable[
            [Callable[[asyncio.AbstractEventLoop], Gtk.Widget]],
            Callable[[asyncio.AbstractEventLoop], Gtk.Widget],
        ]
    ):
        if isinstance(name, str):
            # If a string is provided, return a decorator that registers the widget
            def decorator(
                widget_factory: Callable[[asyncio.AbstractEventLoop], Gtk.Widget],
            ) -> Callable[[asyncio.AbstractEventLoop], Gtk.Widget]:
                self.widgets[name] = widget_factory
                return widget_factory

            return decorator

        # If a function is provided, register it directly
        self.widgets[name.__name__] = name
        return name

    def _create_widget(self, widget_name: str) -> Gtk.Widget:
        """Create a widget from the factory."""

        widget_factory = self.widgets[widget_name]
        widget = widget_factory(self.event_loop)
        
        # If the widget is a window, create a launch button instead
        if isinstance(widget, Gtk.Window):
            # Don't hold onto the original window - destroy it immediately
            widget.destroy()
            return self._create_window_launch_button(widget_name)
        
        return widget

    def _create_window_launch_button(self, widget_name: str) -> Gtk.Widget:
        """Create a button that launches a window when clicked."""
        button_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER,
        )
        lifecycle = WidgetLifecycle(button_box)

        @into(button_box.append)
        def _():
            launch_button = Gtk.Button(
                label=f"Launch {widget_name}",
                css_classes=["suggested-action", "pill"],
            )

            @lifecycle.subscribe(launch_button, "clicked")
            def _(_):
                # Always create a fresh window instance
                widget_factory = self.widgets[widget_name]
                fresh_window = widget_factory(self.event_loop)
                
                # Ensure it's actually a window
                if not isinstance(fresh_window, Gtk.Window):
                    return
                
                # Present the window - GTK will handle lifecycle
                fresh_window.present()

            return launch_button

        @into(button_box.append)
        def _():
            return Gtk.Label(
                label="This is a window widget. Click the button above to launch it.",
                css_classes=["dim-label"],
                wrap=True,
                justify=Gtk.Justification.CENTER,
            )



        return button_box

    def run(self, argv: list[str] | None = None):
        """Run the application."""
        app = App(self)
        return app.run(argv)


def HeaderBar(
    selected_widget: MutableState[str],
    show_sidebar: MutableState[bool],
    reload_callback: Callable[[], None],
    widgets: dict[str, Callable],
) -> Adw.HeaderBar:
    """Create the header bar with sidebar toggle and reload button."""
    header_bar = Adw.HeaderBar()
    lifecycle = WidgetLifecycle(header_bar)

    @into(header_bar.pack_start)
    def _():
        # Sidebar toggle button
        toggle_button = Gtk.ToggleButton(
            icon_name="sidebar-show-symbolic", tooltip_text="Toggle Sidebar"
        )

        # Bind toggle button to sidebar visibility
        @lifecycle.watch(show_sidebar, init=True)
        def _(show: bool):
            toggle_button.set_active(show)

        @lifecycle.subscribe(toggle_button, "toggled")
        def _(_):
            show_sidebar.set(toggle_button.get_active())

        return toggle_button

    @into(header_bar.pack_end)
    def _():
        # Reload button
        reload_button = Gtk.Button(
            icon_name="view-refresh-symbolic",
            tooltip_text="Reload Content",
            sensitive=bool(widgets),
        )

        @lifecycle.subscribe(reload_button, "clicked")
        def _(_):
            reload_callback()

        @lifecycle.watch(selected_widget, init=True)
        def _(_):
            reload_button.set_sensitive(
                bool(selected_widget.value and selected_widget.value in widgets)
            )

        return reload_button

    return header_bar


def Sidebar(selected_widget: MutableState[str], widgets: dict[str, Callable]) -> Gtk.Widget:
    """Create the sidebar with navigation list."""
    scrolled = Gtk.ScrolledWindow(
        hscrollbar_policy=Gtk.PolicyType.NEVER,
        vscrollbar_policy=Gtk.PolicyType.AUTOMATIC,
    )
    lifecycle = WidgetLifecycle(scrolled)

    @into(scrolled.set_child)
    def _():
        # Create list box for navigation
        listbox = Gtk.ListBox(
            css_classes=["navigation-sidebar"],
            selection_mode=Gtk.SelectionMode.SINGLE,
        )

        # Add rows for each widget
        widget_rows = {}
        for widget_name in widgets.keys():

            @into(listbox.append)
            def _(name=widget_name):
                row = Adw.ActionRow(title=name, activatable=True)
                widget_rows[name] = row
                return row

        # Set initial selection and sync with state
        @lifecycle.watch(selected_widget, init=True)
        def _(_):
            # Find and select the row that matches current state
            target_row = None
            if selected_widget.value in widget_rows:
                target_row = widget_rows[selected_widget.value]
            elif widgets:
                # Fallback to first widget if current selection is invalid
                first_name = list(widgets.keys())[0]
                target_row = widget_rows[first_name]
                selected_widget.set(first_name)

            if target_row:
                listbox.select_row(target_row)

        # Handle row selection
        @lifecycle.subscribe(listbox, "row-selected")
        def _(_):
            selected_row = listbox.get_selected_row()
            if selected_row:
                for name, row in widget_rows.items():
                    if row == selected_row:
                        selected_widget.set(name)
                        break

        return listbox

    return scrolled


def PreviewArea(
    selected_widget: State[str], create_widget_func: Callable[[str], Gtk.Widget]
) -> Gtk.Widget:
    """Create the preview area for displaying widgets."""
    clamp = Adw.Clamp(
        maximum_size=800,
        tightening_threshold=600,
        halign=Gtk.Align.CENTER,
        valign=Gtk.Align.CENTER,
    )
    lifecycle = WidgetLifecycle(clamp)

    @into(clamp.set_child)
    def _():
        # Container that will hold the preview widget
        preview_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
            margin_top=24,
            margin_bottom=24,
            margin_start=24,
            margin_end=24,
        )

        # Update preview when selected widget changes
        @lifecycle.watch(selected_widget, init=True)
        def _(_):
            # Clear existing children
            child = preview_box.get_first_child()
            while child:
                next_child = child.get_next_sibling()
                preview_box.remove(child)
                child = next_child

            # Create and add the preview widget
            if selected_widget.value:
                try:
                    preview_widget = create_widget_func(selected_widget.value)

                    if preview_widget:
                        preview_box.append(preview_widget)
                    else:
                        raise Exception("Failed to create widget")

                except Exception as e:
                    # Show error if widget creation fails
                    error_box = Gtk.Box(
                        orientation=Gtk.Orientation.VERTICAL,
                        spacing=8,
                        halign=Gtk.Align.CENTER,
                        valign=Gtk.Align.CENTER,
                    )

                    error_icon = Gtk.Label(
                        label="⚠️",
                        css_classes=["title-1"],
                    )

                    error_title = Gtk.Label(
                        label="Widget Creation Error",
                        css_classes=["title-3"],
                    )

                    error_message = Gtk.Label(
                        label=str(e),
                        css_classes=["dim-label"],
                        wrap=True,
                        justify=Gtk.Justification.CENTER,
                    )

                    error_box.append(error_icon)
                    error_box.append(error_title)
                    error_box.append(error_message)
                    preview_box.append(error_box)

        return preview_box

    return clamp


def MainContent(
    selected_widget: MutableState[str],
    show_sidebar: State[bool],
    widgets: dict[str, Callable],
    create_widget_func: Callable[[str], Gtk.Widget],
) -> Gtk.Widget:
    """Create the main content area with sidebar and preview."""
    split_view = Adw.OverlaySplitView(
        min_sidebar_width=200, max_sidebar_width=300, sidebar_width_fraction=0.25
    )
    lifecycle = WidgetLifecycle(split_view)

    # Bind sidebar visibility to state
    @lifecycle.watch(show_sidebar, init=True)
    def _(_):
        split_view.set_show_sidebar(show_sidebar.value)

    # Set sidebar and content
    split_view.set_sidebar(Sidebar(selected_widget, widgets))
    split_view.set_content(PreviewArea(selected_widget, create_widget_func))

    return split_view


def Window(app: Adw.Application, preview: Preview) -> Adw.ApplicationWindow:
    """Create the main application window."""
    window = Adw.ApplicationWindow(
        application=app, default_width=1000, default_height=700, title="Preview Widgets"
    )

    # State to track selected widget
    selected_widget = MutableState[str](list(preview.widgets.keys())[0] if preview.widgets else "")

    # State to control sidebar visibility
    show_sidebar = MutableState[bool](True)

    @into(window.set_content)
    def _():
        # Create ToolbarView as the main container
        toolbar_view = Adw.ToolbarView(top_bar_style=Adw.ToolbarStyle.RAISED)

        def reload_content():
            # Remember current selection
            current_selection = selected_widget.value
            # Clear current content
            toolbar_view.set_content(None)
            # Recreate content
            toolbar_view.set_content(
                MainContent(selected_widget, show_sidebar, preview.widgets, preview._create_widget)
            )
            # Restore selection
            if current_selection and current_selection in preview.widgets:
                selected_widget.set(current_selection)

        # Add header bar
        toolbar_view.add_top_bar(
            HeaderBar(selected_widget, show_sidebar, reload_content, preview.widgets)
        )

        # Set initial content
        toolbar_view.set_content(
            MainContent(selected_widget, show_sidebar, preview.widgets, preview._create_widget)
        )

        return toolbar_view

    return window


def App(preview: Preview) -> Adw.Application:
    """Create the preview application."""
    app = Adw.Application(application_id="com.example.PreviewApp")

    @lambda f: app.connect("activate", f)
    def _(*_):
        window = Window(app, preview)
        window.set_application(app)
        window.present()

    return app
