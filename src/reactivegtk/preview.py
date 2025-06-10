import asyncio
from collections.abc import Sequence
from typing import Callable, overload

import gi

from reactivegtk.dsl import apply, build, do
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
        return build(
            Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL,
                spacing=12,
                halign=Gtk.Align.CENTER,
                valign=Gtk.Align.CENTER,
            ),
            lambda box: apply(box.append).foreach(
                build(
                    Gtk.Button(
                        label=f"Launch {name}",
                        css_classes=["suggested-action", "pill"],
                        halign=Gtk.Align.CENTER,
                    ),
                    lambda button: button.connect(
                        "clicked",
                        lambda *_: do(
                            window := self._widgets[name](event_loop),
                            window.present() if isinstance(window, Gtk.Window) else None,
                        ),
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
        return build(
            Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL,
                spacing=8,
                halign=Gtk.Align.CENTER,
                valign=Gtk.Align.CENTER,
            ),
            lambda box: apply(box.append).foreach(
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
    return build(
        Adw.HeaderBar(),
        lambda header_bar: do(
            # Sidebar toggle
            header_bar.pack_start(
                build(
                    Gtk.ToggleButton(icon_name="sidebar-show-symbolic", tooltip_text="Toggle Sidebar"),
                    lambda toggle_button: do(
                        view_model.show_sidebar.bind(toggle_button, "active"),
                        toggle_button.connect("toggled", lambda btn: view_model.set_sidebar_visible(btn.get_active())),
                    ),
                ),
            ),
            # Reload button
            header_bar.pack_end(
                build(
                    Gtk.Button(
                        icon_name="view-refresh-symbolic",
                        tooltip_text="Reload Content",
                        sensitive=view_model.has_widgets,
                    ),
                    lambda reload_button: reload_button.connect("clicked", lambda *_: view_model.reload()),
                ),
            ),
        ),
    )


def Sidebar(view_model: PreviewViewModel) -> Gtk.Widget:
    """Create the sidebar with navigation list."""
    # Create a mapping of rows to widget names
    widget_rows: dict[str, Adw.ActionRow] = {}

    return build(
        Gtk.ScrolledWindow(
            hscrollbar_policy=Gtk.PolicyType.NEVER,
            vscrollbar_policy=Gtk.PolicyType.AUTOMATIC,
        ),
        lambda scrolled: scrolled.set_child(
            build(
                Gtk.ListBox(
                    css_classes=["navigation-sidebar"],
                    selection_mode=Gtk.SelectionMode.SINGLE,
                ),
                lambda listbox: do(
                    # Add rows for each widget and track them
                    apply(listbox.append).foreach(
                        *(
                            widget_rows.setdefault(name, Adw.ActionRow(title=name, activatable=True))
                            for name in view_model.widget_names
                        )
                    ),
                    # Handle selection
                    listbox.connect(
                        "row-selected",
                        lambda lb, row: do(
                            widget_name := next(
                                (name for name, r in widget_rows.items() if r == row),
                                None,
                            )
                            if row
                            else None,
                            view_model.select_widget(widget_name) if widget_name else None,
                        ),
                    ),
                    # Set initial selection and update when selected widget changes
                    view_model.selected_widget.watch(
                        lambda name: listbox.select_row(widget_rows.get(name)),
                        init=True,
                    ),
                ),
            )
        ),
    )


def PreviewArea(view_model: PreviewViewModel, event_loop: asyncio.AbstractEventLoop) -> Gtk.Widget:
    """Create the preview area for displaying widgets."""
    return build(
        Adw.Clamp(
            maximum_size=800,
            tightening_threshold=600,
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER,
        ),
        lambda clamp: clamp.set_child(
            build(
                Gtk.Box(
                    orientation=Gtk.Orientation.VERTICAL,
                    spacing=12,
                    margin_top=24,
                    margin_bottom=24,
                    margin_start=24,
                    margin_end=24,
                ),
                lambda preview_box: do(
                    # Update preview when selected widget changes
                    view_model.selected_widget.watch(
                        lambda name: _update_preview_content(preview_box, name, view_model, event_loop),
                        init=True,
                    ),
                    # Update preview when reload trigger changes
                    view_model.reload_trigger.watch(
                        lambda _: _update_preview_content(
                            preview_box,
                            view_model.selected_widget.value,
                            view_model,
                            event_loop,
                        )
                    ),
                ),
            )
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
    return build(
        Adw.OverlaySplitView(min_sidebar_width=200, max_sidebar_width=300, sidebar_width_fraction=0.25),
        lambda split_view: do(
            # Bind sidebar visibility to state
            view_model.show_sidebar.bind(split_view, "show-sidebar"),
            # Set sidebar and content
            split_view.set_sidebar(Sidebar(view_model)),
            split_view.set_content(
                build(
                    Gtk.Stack(),
                    lambda stack: do(
                        stack.add_named(PreviewArea(view_model, event_loop), "preview"),
                        stack.add_named(
                            Gtk.Label(
                                label="No widgets available",
                                css_classes=["dim-label"],
                                halign=Gtk.Align.CENTER,
                                valign=Gtk.Align.CENTER,
                            ),
                            "empty",
                        ),
                        # Update stack visibility based on selected widget
                        view_model.selected_widget.watch(
                            lambda name: stack.set_visible_child_name("preview" if name else "empty"),
                            init=True,
                        ),
                    ),
                )
            ),
        ),
    )


def PreviewWindow(
    app: Adw.Application, view_model: PreviewViewModel, event_loop: asyncio.AbstractEventLoop
) -> Adw.ApplicationWindow:
    """Create the main application window."""
    return build(
        Adw.ApplicationWindow(application=app, default_width=1000, default_height=700, title="Preview Widgets"),
        lambda window: window.set_content(
            build(
                Adw.ToolbarView(top_bar_style=Adw.ToolbarStyle.RAISED),
                lambda toolbar_view: do(
                    toolbar_view.add_top_bar(HeaderBar(view_model)),
                    toolbar_view.set_content(MainContent(view_model, event_loop)),
                ),
            ),
        ),
    )


def PreviewApp(preview: "Preview") -> Adw.Application:
    """Create the preview application."""
    return build(
        Adw.Application(application_id="com.example.PreviewApp"),
        lambda app: do(
            (view_model := PreviewViewModel(preview.widgets)),
            app.connect(
                "activate",
                lambda *_: do(
                    window := PreviewWindow(app, view_model, preview.event_loop),
                    window.set_application(app),
                    window.present(),
                ),
            ),
        ),
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
            return build(
                Gtk.Window(
                    title=title,
                    default_width=600,
                    default_height=400,
                ),
                lambda window: window.set_child(widget),
            )

        # Preserve the original function's name for registration
        window_factory.__name__ = widget_factory.__name__
        return window_factory

    def run(self, argv: list[str] | None = None):
        """Run the application."""
        app = PreviewApp(self)
        return app.run(argv)
