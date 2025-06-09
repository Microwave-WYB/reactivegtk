import asyncio
from typing import Callable, overload

import gi

from reactivegtk.dsl import apply, do, ui
from reactivegtk.lifecycle.core import WidgetLifecycle
from reactivegtk.state import MutableState, State
from reactivegtk.utils import start_event_loop

gi.require_versions(
    {
        "Gtk": "4.0",
        "Adw": "1",
    }
)
from gi.repository import Adw, Gtk  # type: ignore # noqa: E402


class Preview:
    """
    A preview application with navigation tabs and widget previews.
    """

    def __init__(self):
        self.widgets: dict[str, Callable[[asyncio.AbstractEventLoop], Gtk.Widget]] = {}
        self.event_loop, _ = start_event_loop()
        self._widget_cache: dict[str, Gtk.Widget] = {}

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

    @overload
    def as_window(
        self, func: Callable[[asyncio.AbstractEventLoop], Gtk.Widget], /
    ) -> Callable[[asyncio.AbstractEventLoop], Gtk.Widget]:
        """
        Register a widget factory function as a window decorator.

        Usage:
            preview = Preview()

            @preview.as_window
            def MyWidget(event_loop) -> Gtk.Widget: ...
        """
        ...

    @overload
    def as_window(
        self, name: str, /
    ) -> Callable[
        [Callable[[asyncio.AbstractEventLoop], Gtk.Widget]],
        Callable[[asyncio.AbstractEventLoop], Gtk.Widget],
    ]:
        """
        Register a widget factory function as a window with a specific name.

        Usage:
            preview = Preview()

            @preview.as_window("MyWidget")
            def my_widget_factory(event_loop) -> Gtk.Widget: ...
        """
        ...

    def as_window(
        self, name: Callable[[asyncio.AbstractEventLoop], Gtk.Widget] | str, /
    ) -> (
        Callable[[asyncio.AbstractEventLoop], Gtk.Widget]
        | Callable[
            [Callable[[asyncio.AbstractEventLoop], Gtk.Widget]],
            Callable[[asyncio.AbstractEventLoop], Gtk.Widget],
        ]
    ):
        if isinstance(name, str):
            # If a string is provided, return a decorator that registers the widget as window
            def decorator(
                widget_factory: Callable[[asyncio.AbstractEventLoop], Gtk.Widget],
            ) -> Callable[[asyncio.AbstractEventLoop], Gtk.Widget]:
                wrapped_factory = self._wrap_as_window(widget_factory, name)
                self.widgets[name] = wrapped_factory
                return wrapped_factory

            return decorator

        # If a function is provided, wrap it as window and register it directly
        wrapped_factory = self._wrap_as_window(name, name.__name__)
        self.widgets[name.__name__] = wrapped_factory
        return wrapped_factory

    def _wrap_as_window(
        self,
        widget_factory: Callable[[asyncio.AbstractEventLoop], Gtk.Widget],
        title: str,
    ) -> Callable[[asyncio.AbstractEventLoop], Gtk.Widget]:
        """Wrap a widget factory to create a window containing the widget."""

        def window_factory(event_loop: asyncio.AbstractEventLoop) -> Gtk.Window:
            # Create the widget first
            widget = widget_factory(event_loop)

            # If it's already a window, return it as-is
            if isinstance(widget, Gtk.Window):
                return widget

            # Otherwise, create a window and add the widget
            return ui(
                window := Gtk.Window(
                    title=title,
                    default_width=600,
                    default_height=400,
                ),
                window.set_child(widget),
            )

        # Preserve the original function's name for registration
        window_factory.__name__ = widget_factory.__name__
        return window_factory

    def _create_widget(self, widget_name: str) -> Gtk.Widget:
        """Create a widget from the factory, using cache if available."""

        # Check cache first (except for windows which should always create launch buttons)
        if widget_name in self._widget_cache:
            cached_widget = self._widget_cache[widget_name]
            # Verify the cached widget is still valid (not destroyed)
            try:
                # Try to access a property to check if widget is still valid
                _ = cached_widget.get_visible()
                return cached_widget
            except Exception:
                # Widget is no longer valid, remove from cache
                del self._widget_cache[widget_name]

        widget_factory = self.widgets[widget_name]
        widget = widget_factory(self.event_loop)

        # If the widget is a window, create a launch button instead
        if isinstance(widget, Gtk.Window):
            # Don't hold onto the original window - destroy it immediately
            widget.destroy()
            launch_button = self._create_window_launch_button(widget_name)
            # Cache the launch button, not the window
            self._widget_cache[widget_name] = launch_button
            return launch_button

        # Cache non-window widgets
        self._widget_cache[widget_name] = widget
        return widget

    def _create_window_launch_button(self, widget_name: str) -> Gtk.Widget:
        """Create a button that launches a window when clicked."""
        return ui(
            button_box := Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL,
                spacing=12,
                halign=Gtk.Align.CENTER,
                valign=Gtk.Align.CENTER,
            ),
            lifecycle := WidgetLifecycle(button_box),
            apply(button_box.append).foreach(
                ui(
                    launch_button := Gtk.Button(
                        label=f"Launch {widget_name}",
                        css_classes=["suggested-action", "pill"],
                        halign=Gtk.Align.CENTER,
                    ),
                    lifecycle.subscribe(launch_button, "clicked")(
                        lambda *_: do(
                            widget_factory := self.widgets[widget_name],
                            fresh_window := widget_factory(self.event_loop),
                            fresh_window.present()
                            if isinstance(fresh_window, Gtk.Window)
                            else None,
                        )
                    ),
                ),
                Gtk.Label(
                    label="This is a window widget. Click the button above to launch it.",
                    css_classes=["dim-label"],
                    wrap=True,
                    justify=Gtk.Justification.CENTER,
                ),
            ),
        )

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
    return ui(
        header_bar := Adw.HeaderBar(),
        lifecycle := WidgetLifecycle(header_bar),
        header_bar.pack_start(
            ui(
                toggle_button := Gtk.ToggleButton(
                    icon_name="sidebar-show-symbolic", tooltip_text="Toggle Sidebar"
                ),
                lifecycle.watch(show_sidebar, init=True)(
                    lambda show: toggle_button.set_active(show)
                ),
                lifecycle.subscribe(toggle_button, "toggled")(
                    lambda *_: show_sidebar.set(toggle_button.get_active())
                ),
            ),
        ),
        header_bar.pack_end(
            ui(
                reload_button := Gtk.Button(
                    icon_name="view-refresh-symbolic",
                    tooltip_text="Reload Content",
                    sensitive=bool(widgets),
                ),
                lifecycle.subscribe(reload_button, "clicked")(lambda *_: reload_callback()),
                lifecycle.watch(selected_widget, init=True)(
                    lambda _: reload_button.set_sensitive(
                        bool(selected_widget.value and selected_widget.value in widgets)
                    )
                ),
            ),
        ),
    )


def Sidebar(selected_widget: MutableState[str], widgets: dict[str, Callable]) -> Gtk.Widget:
    """Create the sidebar with navigation list."""
    widget_rows = {}

    return ui(
        scrolled := Gtk.ScrolledWindow(
            hscrollbar_policy=Gtk.PolicyType.NEVER,
            vscrollbar_policy=Gtk.PolicyType.AUTOMATIC,
        ),
        lifecycle := WidgetLifecycle(scrolled),
        scrolled.set_child(
            ui(
                listbox := Gtk.ListBox(
                    css_classes=["navigation-sidebar"],
                    selection_mode=Gtk.SelectionMode.SINGLE,
                ),
                # Add rows for each widget
                apply(listbox.append).foreach(
                    *[
                        widget_rows.setdefault(
                            widget_name, _ := Adw.ActionRow(title=widget_name, activatable=True)
                        )
                        for widget_name in widgets.keys()
                    ]
                ),
                # Set initial selection and sync with state
                lifecycle.watch(selected_widget, init=True)(
                    lambda _: do(
                        target_row := (
                            widget_rows.get(selected_widget.value)
                            or (
                                widget_rows[first_name]
                                if (first_name := list(widgets.keys())[0] if widgets else None)
                                and selected_widget.set(first_name) is None
                                else None
                            )
                        ),
                        listbox.select_row(target_row) if target_row else None,
                    )
                ),
                # Handle row selection
                lifecycle.subscribe(listbox, "row-selected")(
                    lambda *_: do(
                        selected_row := listbox.get_selected_row(),
                        selected_widget.set(name)
                        if selected_row
                        and (
                            name := next(
                                (name for name, row in widget_rows.items() if row == selected_row),
                                None,
                            )
                        )
                        else None,
                    )
                ),
            ),
        ),
    )


def PreviewArea(
    selected_widget: State[str], create_widget_func: Callable[[str], Gtk.Widget]
) -> Gtk.Widget:
    """Create the preview area for displaying widgets."""
    return ui(
        clamp := Adw.Clamp(
            maximum_size=800,
            tightening_threshold=600,
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER,
        ),
        lifecycle := WidgetLifecycle(clamp),
        clamp.set_child(
            ui(
                preview_box := Gtk.Box(
                    orientation=Gtk.Orientation.VERTICAL,
                    spacing=12,
                    margin_top=24,
                    margin_bottom=24,
                    margin_start=24,
                    margin_end=24,
                ),
                # Update preview when selected widget changes
                lifecycle.watch(selected_widget, init=True)(
                    lambda _: _update_preview_content(
                        preview_box, selected_widget.value, create_widget_func
                    )
                ),
            ),
        ),
    )


def _get_all_children(container):
    """Helper to get all children from a container"""
    children = []
    child = container.get_first_child()
    while child:
        children.append(child)
        child = child.get_next_sibling()
    return children


def _update_preview_content(preview_box, widget_name, create_widget_func):
    """Helper to update preview content"""
    # Clear existing children safely
    children = _get_all_children(preview_box)
    for child in children:
        # Only remove if it's actually a child of this container
        if child.get_parent() == preview_box:
            preview_box.remove(child)

    if widget_name:
        try:
            preview_widget = create_widget_func(widget_name)
            if preview_widget:
                # If widget has a parent, remove it first (for cached widgets)
                current_parent = preview_widget.get_parent()
                if current_parent:
                    preview_widget.unparent()
                preview_box.append(preview_widget)
            else:
                raise Exception("Failed to create widget")
        except Exception as e:
            # Show error if widget creation fails
            error_box = ui(
                error_container := Gtk.Box(
                    orientation=Gtk.Orientation.VERTICAL,
                    spacing=8,
                    halign=Gtk.Align.CENTER,
                    valign=Gtk.Align.CENTER,
                ),
                apply(error_container.append).foreach(
                    Gtk.Label(
                        label="⚠️",
                        css_classes=["title-1"],
                    ),
                    Gtk.Label(
                        label="Widget Creation Error",
                        css_classes=["title-3"],
                    ),
                    Gtk.Label(
                        label=str(e),
                        css_classes=["dim-label"],
                        wrap=True,
                        justify=Gtk.Justification.CENTER,
                    ),
                ),
            )
            preview_box.append(error_box)


def MainContent(
    selected_widget: MutableState[str],
    show_sidebar: State[bool],
    widgets: dict[str, Callable],
    create_widget_func: Callable[[str], Gtk.Widget],
) -> Gtk.Widget:
    """Create the main content area with sidebar and preview."""
    return ui(
        split_view := Adw.OverlaySplitView(
            min_sidebar_width=200, max_sidebar_width=300, sidebar_width_fraction=0.25
        ),
        lifecycle := WidgetLifecycle(split_view),
        # Bind sidebar visibility to state
        lifecycle.watch(show_sidebar, init=True)(
            lambda _: split_view.set_show_sidebar(show_sidebar.value)
        ),
        # Set sidebar and content
        split_view.set_sidebar(Sidebar(selected_widget, widgets)),
        split_view.set_content(PreviewArea(selected_widget, create_widget_func)),
    )


def Window(app: Adw.Application, preview: Preview) -> Adw.ApplicationWindow:
    """Create the main application window."""
    # State to track selected widget
    selected_widget = MutableState[str](list(preview.widgets.keys())[0] if preview.widgets else "")
    # State to control sidebar visibility
    show_sidebar = MutableState[bool](True)

    def reload_content():
        # Clear widget cache to force recreation
        preview._widget_cache.clear()
        # Remember current selection
        current_selection = selected_widget.value
        # Clear current content
        toolbar_view.set_content(None)
        # Recreate content
        toolbar_view.set_content(
            MainContent(
                selected_widget,
                show_sidebar,
                preview.widgets,
                preview._create_widget,
            )
        )
        # Restore selection
        if current_selection and current_selection in preview.widgets:
            selected_widget.set(current_selection)

    return ui(
        window := Adw.ApplicationWindow(
            application=app, default_width=1000, default_height=700, title="Preview Widgets"
        ),
        window.set_content(
            ui(
                toolbar_view := Adw.ToolbarView(top_bar_style=Adw.ToolbarStyle.RAISED),
                # Add header bar
                toolbar_view.add_top_bar(
                    HeaderBar(selected_widget, show_sidebar, reload_content, preview.widgets)
                ),
                # Set initial content
                toolbar_view.set_content(
                    MainContent(
                        selected_widget, show_sidebar, preview.widgets, preview._create_widget
                    )
                ),
            ),
        ),
    )


def App(preview: Preview) -> Adw.Application:
    """Create the preview application."""
    return do(
        app := Adw.Application(application_id="com.example.PreviewApp"),
        app.connect(
            "activate",
            lambda *_: do(
                window := Window(app, preview),
                window.set_application(app),
                window.present(),
            ),
        ),
        ret=app,
    )
