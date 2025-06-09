import asyncio
from typing import Callable, overload
from collections.abc import Sequence

import gi

from reactivegtk.dsl import apply, do, ui
from reactivegtk.lifecycle.core import WidgetLifecycle
from reactivegtk.state import MutableState, State
from reactivegtk.utils import start_event_loop
from reactivegtk.widgets import Conditional

gi.require_versions({"Gtk": "4.0", "Adw": "1"})
from gi.repository import Adw, Gtk


class PreviewViewModel:
    """ViewModel for the preview application state."""

    def __init__(self, widgets: dict[str, Callable]):
        self._widgets = widgets
        self._widget_names = list(widgets.keys())

        # Reactive state
        self._selected_widget = MutableState(self._widget_names[0] if self._widget_names else "")
        self._show_sidebar = MutableState(True)
        self._reload_trigger = MutableState(0)

    @property
    def selected_widget(self) -> State[str]:
        return self._selected_widget

    @property
    def show_sidebar(self) -> State[bool]:
        return self._show_sidebar

    @property
    def reload_trigger(self) -> State[int]:
        return self._reload_trigger

    @property
    def widget_names(self) -> Sequence[str]:
        return self._widget_names

    @property
    def has_widgets(self) -> bool:
        return bool(self._widgets)

    def select_widget(self, name: str) -> None:
        if name in self._widgets:
            self._selected_widget.set(name)

    def toggle_sidebar(self) -> None:
        self._show_sidebar.update(lambda x: not x)

    def set_sidebar_visible(self, visible: bool) -> None:
        self._show_sidebar.set(visible)

    def reload(self) -> None:
        self._reload_trigger.update(lambda x: x + 1)

    def create_widget(self, name: str, event_loop: asyncio.AbstractEventLoop) -> Gtk.Widget:
        """Create a widget instance from the factory."""
        if name not in self._widgets:
            return self._create_error_widget(f"Widget '{name}' not found")

        try:
            widget = self._widgets[name](event_loop)

            # If it's a window, create a launch button instead
            if isinstance(widget, Gtk.Window):
                widget.close()  # Don't keep the window around
                return self._create_window_launcher(name, event_loop)

            return widget

        except Exception as e:
            return self._create_error_widget(f"Error creating '{name}': {str(e)}")

    def _create_window_launcher(
        self, name: str, event_loop: asyncio.AbstractEventLoop
    ) -> Gtk.Widget:
        """Create a button that launches a window when clicked."""
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
                    button := Gtk.Button(
                        label=f"Launch {name}",
                        css_classes=["suggested-action", "pill"],
                        halign=Gtk.Align.CENTER,
                    ),
                    lifecycle.subscribe(button, "clicked")(
                        lambda *_: do(
                            window := self._widgets[name](event_loop),
                            window.present() if isinstance(window, Gtk.Window) else None,
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

    def _create_error_widget(self, error_message: str) -> Gtk.Widget:
        """Create an error display widget."""
        return ui(
            box := Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL,
                spacing=8,
                halign=Gtk.Align.CENTER,
                valign=Gtk.Align.CENTER,
            ),
            apply(box.append).foreach(
                Gtk.Label(
                    label="⚠️",
                    css_classes=["title-1"],
                ),
                Gtk.Label(
                    label="Widget Creation Error",
                    css_classes=["title-3"],
                ),
                Gtk.Label(
                    label=error_message,
                    css_classes=["dim-label"],
                    wrap=True,
                    justify=Gtk.Justification.CENTER,
                ),
            ),
        )


def HeaderBar(view_model: PreviewViewModel) -> Adw.HeaderBar:
    """Create the header bar with sidebar toggle and reload button."""
    return ui(
        header_bar := Adw.HeaderBar(),
        lifecycle := WidgetLifecycle(header_bar),
        # Sidebar toggle
        header_bar.pack_start(
            ui(
                toggle_button := Gtk.ToggleButton(
                    icon_name="sidebar-show-symbolic", tooltip_text="Toggle Sidebar"
                ),
                view_model.show_sidebar.bind(toggle_button, "active"),
                lifecycle.subscribe(toggle_button, "toggled")(
                    lambda *_: view_model.set_sidebar_visible(toggle_button.get_active())
                ),
            ),
        ),
        # Reload button
        header_bar.pack_end(
            ui(
                reload_button := Gtk.Button(
                    icon_name="view-refresh-symbolic",
                    tooltip_text="Reload Content",
                    sensitive=view_model.has_widgets,
                ),
                lifecycle.subscribe(reload_button, "clicked")(lambda *_: view_model.reload()),
            ),
        ),
    )


def Sidebar(view_model: PreviewViewModel) -> Gtk.Widget:
    """Create the sidebar with navigation list."""
    # Create a mapping of rows to widget names
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
                # Add rows for each widget and track them
                apply(listbox.append).foreach(
                    *[
                        widget_rows.setdefault(name, Adw.ActionRow(title=name, activatable=True))
                        for name in view_model.widget_names
                    ]
                ),
                # Handle selection
                lifecycle.subscribe(listbox, "row-selected")(
                    lambda *_: do(
                        selected_row := listbox.get_selected_row(),
                        widget_name := next(
                            (name for name, row in widget_rows.items() if row == selected_row), None
                        )
                        if selected_row
                        else None,
                        view_model.select_widget(widget_name) if widget_name else None,
                    )
                ),
                # Set initial selection when selected widget changes
                lifecycle.watch(view_model.selected_widget, init=True)(
                    lambda name: do(
                        target_row := widget_rows.get(name) if name else None,
                        listbox.select_row(target_row) if target_row else None,
                    )
                ),
            ),
        ),
    )


def PreviewArea(view_model: PreviewViewModel, event_loop: asyncio.AbstractEventLoop) -> Gtk.Widget:
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
                # Update preview when selected widget or reload trigger changes
                lifecycle.watch(view_model.selected_widget, init=True)(
                    lambda name: _update_preview_content(preview_box, name, view_model, event_loop)
                ),
                lifecycle.watch(view_model.reload_trigger)(
                    lambda _: _update_preview_content(
                        preview_box, view_model.selected_widget.value, view_model, event_loop
                    )
                ),
            ),
        ),
    )


def _update_preview_content(
    preview_box: Gtk.Box,
    widget_name: str,
    view_model: PreviewViewModel,
    event_loop: asyncio.AbstractEventLoop,
):
    """Helper to update preview content."""
    # Clear existing children
    child = preview_box.get_first_child()
    while child:
        next_child = child.get_next_sibling()
        preview_box.remove(child)
        child = next_child

    # Add new content
    if widget_name and view_model.has_widgets:
        preview_widget = view_model.create_widget(widget_name, event_loop)
        if preview_widget:
            # Remove from any existing parent
            if preview_widget.get_parent():
                preview_widget.unparent()
            preview_box.append(preview_widget)


def MainContent(view_model: PreviewViewModel, event_loop: asyncio.AbstractEventLoop) -> Gtk.Widget:
    """Create the main content area with sidebar and preview."""
    return ui(
        split_view := Adw.OverlaySplitView(
            min_sidebar_width=200, max_sidebar_width=300, sidebar_width_fraction=0.25
        ),
        # Bind sidebar visibility to state
        view_model.show_sidebar.bind(split_view, "show_sidebar"),
        # Set sidebar and content
        split_view.set_sidebar(Sidebar(view_model)),
        split_view.set_content(
            Conditional(
                view_model.selected_widget.map(bool),
                true=PreviewArea(view_model, event_loop),
                false=ui(
                    Gtk.Label(
                        label="No widgets available",
                        css_classes=["dim-label"],
                        halign=Gtk.Align.CENTER,
                        valign=Gtk.Align.CENTER,
                    )
                ),
            )
        ),
    )


def PreviewWindow(
    app: Adw.Application, view_model: PreviewViewModel, event_loop: asyncio.AbstractEventLoop
) -> Adw.ApplicationWindow:
    """Create the main application window."""
    return ui(
        window := Adw.ApplicationWindow(
            application=app, default_width=1000, default_height=700, title="Preview Widgets"
        ),
        window.set_content(
            ui(
                toolbar_view := Adw.ToolbarView(top_bar_style=Adw.ToolbarStyle.RAISED),
                toolbar_view.add_top_bar(HeaderBar(view_model)),
                toolbar_view.set_content(MainContent(view_model, event_loop)),
            ),
        ),
    )


def PreviewApp(preview: "Preview") -> Adw.Application:
    """Create the preview application."""
    view_model = PreviewViewModel(preview.widgets)

    return do(
        app := Adw.Application(application_id="com.example.PreviewApp"),
        app.connect(
            "activate",
            lambda *_: do(
                window := PreviewWindow(app, view_model, preview.event_loop),
                window.set_application(app),
                window.present(),
            ),
        ),
        ret=app,
    )


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

    def run(self, argv: list[str] | None = None):
        """Run the application."""
        app = PreviewApp(self)
        return app.run(argv)
