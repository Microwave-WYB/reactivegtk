import asyncio
from collections.abc import Sequence
from functools import partial
from typing import Callable, overload

import gi

from reactivegtk.dsl import apply
from reactivegtk.state import MutableState, State
from reactivegtk.utils import start_event_loop

gi.require_versions({"Gtk": "4.0", "Adw": "1"})
from gi.repository import Adw, Gtk  # type: ignore # noqa: E402


class PreviewViewModel:
    """ViewModel for the preview application state."""

    def __init__(self, widgets: dict[str, Callable]):
        self._widgets = widgets
        self._widget_names = list(widgets.keys())

        # State properties
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

    def _create_window_launcher(self, name: str, event_loop: asyncio.AbstractEventLoop) -> Gtk.Widget:
        """Create a button that launches a window when clicked."""
        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER,
        )

        @apply(box.append)
        def _():
            button = Gtk.Button(
                label=f"Launch {name}",
                css_classes=["suggested-action", "pill"],
                halign=Gtk.Align.CENTER,
            )

            @partial(button.connect, "clicked")
            def _(*_):
                window = self._widgets[name](event_loop)
                if isinstance(window, Gtk.Window):
                    window.present()

            return button

        @apply(box.append)
        def _():
            return Gtk.Label(
                label="This is a window widget. Click the button above to launch it.",
                css_classes=["dim-label"],
                wrap=True,
                justify=Gtk.Justification.CENTER,
            )

        return box

    def _create_error_widget(self, error_message: str) -> Gtk.Widget:
        """Create an error display widget."""
        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=8,
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER,
        )

        @apply(box.append).foreach
        def _():
            return (
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
            )

        return box


def HeaderBar(view_model: PreviewViewModel) -> Adw.HeaderBar:
    """Create the header bar with sidebar toggle and reload button."""
    header_bar = Adw.HeaderBar()

    # Sidebar toggle
    @apply(header_bar.pack_start)
    def _():
        toggle_button = Gtk.ToggleButton(icon_name="sidebar-show-symbolic", tooltip_text="Toggle Sidebar")
        view_model.show_sidebar.bind(toggle_button, "active")

        @partial(toggle_button.connect, "toggled")
        def _(btn):
            view_model.set_sidebar_visible(btn.get_active())

        return toggle_button

    # Reload button
    @apply(header_bar.pack_end)
    def _():
        reload_button = Gtk.Button(
            icon_name="view-refresh-symbolic",
            tooltip_text="Reload Content",
            sensitive=view_model.has_widgets,
        )

        @partial(reload_button.connect, "clicked")
        def _(*_):
            view_model.reload()

        return reload_button

    return header_bar


def Sidebar(view_model: PreviewViewModel) -> Gtk.Widget:
    """Create the sidebar with navigation list."""
    # Create a mapping of rows to widget names
    widget_rows: dict[str, Adw.ActionRow] = {}

    scrolled = Gtk.ScrolledWindow(
        hscrollbar_policy=Gtk.PolicyType.NEVER,
        vscrollbar_policy=Gtk.PolicyType.AUTOMATIC,
    )

    @apply(scrolled.set_child)
    def _():
        listbox = Gtk.ListBox(
            css_classes=["navigation-sidebar"],
            selection_mode=Gtk.SelectionMode.SINGLE,
        )

        # Add rows for each widget and track them
        @apply(listbox.append).foreach
        def _():
            return tuple(
                widget_rows.setdefault(name, Adw.ActionRow(title=name, activatable=True))
                for name in view_model.widget_names
            )

        # Handle selection
        @partial(listbox.connect, "row-selected")
        def _(lb, row):
            if row:
                widget_name = next(
                    (name for name, r in widget_rows.items() if r == row),
                    None,
                )
                if widget_name:
                    view_model.select_widget(widget_name)

        # Set initial selection and update when selected widget changes
        @view_model.selected_widget.watch
        def _(name: str):
            listbox.select_row(widget_rows.get(name))

        return listbox

    return scrolled


def PreviewArea(view_model: PreviewViewModel, event_loop: asyncio.AbstractEventLoop) -> Gtk.Widget:
    """Create the preview area for displaying widgets."""
    clamp = Adw.Clamp(
        maximum_size=800,
        tightening_threshold=600,
        halign=Gtk.Align.CENTER,
        valign=Gtk.Align.CENTER,
    )

    @apply(clamp.set_child)
    def _():
        preview_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
            margin_top=24,
            margin_bottom=24,
            margin_start=24,
            margin_end=24,
        )

        # Update preview when selected widget changes
        view_model.selected_widget.watch(
            lambda name: _update_preview_content(
                preview_box,
                name,
                view_model,
                event_loop,
            ),
        )

        # Update preview when reload trigger changes
        view_model.reload_trigger.watch(
            lambda _: _update_preview_content(
                preview_box,
                view_model.selected_widget.value,
                view_model,
                event_loop,
            )
        )

        return preview_box

    return clamp


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
    split_view = Adw.OverlaySplitView(min_sidebar_width=200, max_sidebar_width=300, sidebar_width_fraction=0.25)

    # Bind sidebar visibility to state
    view_model.show_sidebar.bind(split_view, "show-sidebar")

    # Set sidebar
    split_view.set_sidebar(Sidebar(view_model))

    # Set content
    @apply(split_view.set_content)
    def _():
        stack = Gtk.Stack()

        stack.add_named(PreviewArea(view_model, event_loop), "preview")
        stack.add_named(
            Gtk.Label(
                label="No widgets available",
                css_classes=["dim-label"],
                halign=Gtk.Align.CENTER,
                valign=Gtk.Align.CENTER,
            ),
            "empty",
        )

        # Update stack visibility based on selected widget
        view_model.selected_widget.watch(
            lambda name: stack.set_visible_child_name("preview" if name else "empty"),
        )

        return stack

    return split_view


def PreviewWindow(
    app: Adw.Application, view_model: PreviewViewModel, event_loop: asyncio.AbstractEventLoop
) -> Adw.ApplicationWindow:
    """Create the main application window."""
    window = Adw.ApplicationWindow(application=app, default_width=1000, default_height=700, title="Preview Widgets")

    @apply(window.set_content)
    def _():
        toolbar_view = Adw.ToolbarView(top_bar_style=Adw.ToolbarStyle.RAISED)

        toolbar_view.add_top_bar(HeaderBar(view_model))
        toolbar_view.set_content(MainContent(view_model, event_loop))

        return toolbar_view

    return window


def PreviewApp(preview: "Preview") -> Adw.Application:
    """Create the preview application."""
    app = Adw.Application(application_id="com.example.PreviewApp")
    view_model = PreviewViewModel(preview.widgets)

    @partial(app.connect, "activate")
    def _(*_):
        window = PreviewWindow(app, view_model, preview.event_loop)
        window.set_application(app)
        window.present()

    return app


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
        self, arg: Callable[[asyncio.AbstractEventLoop], Gtk.Widget] | str, /
    ) -> (
        Callable[[asyncio.AbstractEventLoop], Gtk.Widget]
        | Callable[
            [Callable[[asyncio.AbstractEventLoop], Gtk.Widget]],
            Callable[[asyncio.AbstractEventLoop], Gtk.Widget],
        ]
    ):
        if isinstance(arg, str):
            # If a string is provided, return a decorator that registers the widget as window
            def decorator(
                widget_factory: Callable[[asyncio.AbstractEventLoop], Gtk.Widget],
            ) -> Callable[[asyncio.AbstractEventLoop], Gtk.Widget]:
                wrapped_factory = self._wrap_as_window(widget_factory, arg)
                self.widgets[arg] = wrapped_factory
                return wrapped_factory

            return decorator

        # If a function is provided, wrap it as window and register it directly
        wrapped_factory = self._wrap_as_window(arg, arg.__name__)
        self.widgets[arg.__name__] = wrapped_factory
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
            window = Gtk.Window(
                title=title,
                default_width=600,
                default_height=400,
            )
            window.set_child(widget)
            return window

        # Preserve the original function's name for registration
        window_factory.__name__ = widget_factory.__name__
        return window_factory

    def run(self, argv: list[str] | None = None):
        """Run the application."""
        app = PreviewApp(self)
        return app.run(argv)
