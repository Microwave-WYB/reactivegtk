import asyncio
from collections.abc import Sequence
from dataclasses import dataclass, field

import gi

from reactivegtk import (
    MutableState,
    WidgetLifecycle,
    bind_sequence,
    into,
    start_event_loop,
)
from reactivegtk.lifecycle import subscribe

gi.require_versions(
    {
        "Gtk": "4.0",
        "Adw": "1",
    }
)
from gi.repository import Adw, Gtk  # type: ignore # noqa: E402


@dataclass
class CounterModel:
    count: MutableState[int] = field(default_factory=lambda: MutableState(0))
    auto: MutableState[bool] = field(default_factory=lambda: MutableState(False))


def Counter(model: CounterModel, event_loop: asyncio.AbstractEventLoop) -> Gtk.Widget:
    vbox = Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL,
        spacing=6,
        valign=Gtk.Align.CENTER,
        halign=Gtk.Align.CENTER,
    )
    lifecycle = WidgetLifecycle(vbox)

    @lifecycle.subscribe(vbox, "realize")
    def _(*_):
        print("Counter widget realized")

    @lifecycle.subscribe(vbox, "unrealize")
    def _(*_):
        print("Counter widget unrealized")

    @lifecycle.on_cleanup()
    def _():
        print("Counter widget destroyed")

    @lifecycle.watch(model.auto, init=True)
    @lifecycle.effect(event_loop)
    async def _():
        while model.auto.value:
            await asyncio.sleep(1)
            model.count.update(lambda x: x + 1)

    @into(vbox.append)
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
            def _(*_):
                model.count.update(lambda x: x - 1)

            return button

        @into(hbox.append)
        def _():
            label = Gtk.Label(
                css_classes=["title-2"],
                margin_start=12,
                margin_end=12,
                valign=Gtk.Align.CENTER,
            )

            @lifecycle.watch(model.count, init=True)
            def _(_):
                label.set_label(str(model.count.value))

            return label

        @into(hbox.append)
        def _():
            button = Gtk.Button(
                icon_name="list-add-symbolic",
                css_classes=["circular"],
                valign=Gtk.Align.CENTER,
            )

            @lifecycle.subscribe(button, "clicked")
            def _(*_):
                model.count.update(lambda x: x + 1)

            return button

        return hbox

    @into(vbox.append)
    def _():
        button = Gtk.Button(label="Reset", css_classes=["destructive-action"])

        @lifecycle.subscribe(button, "clicked")
        def _(*_):
            model.count.set(0)

        return button

    @into(vbox.append)
    def _():
        button = Gtk.Button()

        @lifecycle.subscribe(button, "clicked")
        def _(*_):
            model.auto.set(not model.auto.value)

        @lifecycle.watch(model.auto, init=True)
        def _(auto: bool):
            button.set_label("Stop Auto-increment" if auto else "Start Auto-increment")

        return button

    return vbox


def CounterBox(
    models: MutableState[Sequence[CounterModel]], event_loop: asyncio.AbstractEventLoop
) -> Gtk.Widget:
    box = Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL,
        margin_top=12,
        margin_bottom=12,
        margin_start=12,
        margin_end=12,
    )

    @bind_sequence(
        box,
        models,
        key_fn=lambda model: id(model),
    )
    def _(item: CounterModel) -> Gtk.Widget:
        # Row container - this will be automatically wrapped in ListBoxRow
        row_hbox = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=12,
            margin_top=6,
            margin_bottom=6,
            margin_start=6,
            margin_end=6,
        )

        # Counter takes up most of the space
        @into(row_hbox.append)
        def _():
            counter_widget = Counter(item, event_loop)
            counter_widget.set_hexpand(True)
            return counter_widget

        # Circular remove button on the right
        @into(row_hbox.append)
        def _():
            remove_button = Gtk.Button(
                icon_name="user-trash-symbolic",
                css_classes=["destructive-action", "circular"],
                valign=Gtk.Align.CENTER,
                tooltip_text="Remove Counter",
            )

            @subscribe(remove_button, remove_button, "clicked")
            def _(*_):
                current_models = list(models.value)
                try:
                    current_models.remove(item)
                    models.set(current_models)
                except ValueError:
                    pass

            return remove_button

        return row_hbox

    return box


def CounterListBox(
    models: MutableState[Sequence[CounterModel]], event_loop: asyncio.AbstractEventLoop
) -> Gtk.Widget:
    listbox = Gtk.ListBox(
        margin_top=12,
        margin_bottom=12,
        margin_start=12,
        margin_end=12,
        show_separators=False,  # Clean look without separators
        selection_mode=Gtk.SelectionMode.NONE,  # No selection needed
    )

    # Add some styling for a cleaner look
    listbox.add_css_class("boxed-list")  # Nice rounded corners

    @bind_sequence(
        listbox,
        models,
        key_fn=lambda model: id(model),
    )
    def _(item: CounterModel) -> Gtk.ListBoxRow:
        # Create ListBoxRow directly
        row = Gtk.ListBoxRow()
        lifecycle = WidgetLifecycle(row)

        # Row container inside the ListBoxRow
        row_hbox = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=12,
            margin_top=6,
            margin_bottom=6,
            margin_start=6,
            margin_end=6,
        )
        row.set_child(row_hbox)

        # Counter takes up most of the space
        @into(row_hbox.append)
        def _():
            counter_widget = Counter(item, event_loop)
            counter_widget.set_hexpand(True)
            return counter_widget

        # Circular remove button on the right
        @into(row_hbox.append)
        def _():
            remove_button = Gtk.Button(
                icon_name="user-trash-symbolic",
                css_classes=["destructive-action", "circular"],
                valign=Gtk.Align.CENTER,
                tooltip_text="Remove Counter",
            )

            @lifecycle.subscribe(remove_button, "clicked")
            def _(*_):
                current_models = list(models.value)
                current_models.remove(item)
                models.set(current_models)

            return remove_button

        return row

    return listbox


def CounterFlowBox(
    models: MutableState[Sequence[CounterModel]], event_loop: asyncio.AbstractEventLoop
) -> Gtk.Widget:
    flowbox = Gtk.FlowBox(
        margin_top=12,
        margin_bottom=12,
        margin_start=12,
        margin_end=12,
        selection_mode=Gtk.SelectionMode.NONE,  # No selection needed
        min_children_per_line=1,
        max_children_per_line=3,
        column_spacing=12,
        row_spacing=12,
        homogeneous=True,
    )

    @bind_sequence(
        flowbox,
        models,
        key_fn=lambda model: id(model),
    )
    def _(item: CounterModel) -> Gtk.FlowBoxChild:
        child = Gtk.FlowBoxChild()
        child_lifecycle = WidgetLifecycle(child)

        # Container for the counter content
        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6,
            margin_top=12,
            margin_bottom=12,
            margin_start=12,
            margin_end=12,
        )
        child.set_child(box)

        # Counter widget
        @into(box.append)
        def _():
            counter_widget = Counter(item, event_loop)
            return counter_widget

        # Remove button at the bottom
        @into(box.append)
        def _():
            remove_button = Gtk.Button(
                label="Remove",
                css_classes=["destructive-action"],
                halign=Gtk.Align.CENTER,
                tooltip_text="Remove Counter",
            )

            @child_lifecycle.subscribe(remove_button, "clicked")
            def _(*_):
                current_models = list(models.value)
                try:
                    current_models.remove(item)
                    models.set(current_models)
                except ValueError:
                    pass

            return remove_button

        return child

    return flowbox


def Window(event_loop: asyncio.AbstractEventLoop) -> Adw.ApplicationWindow:
    window = Adw.ApplicationWindow(title="Counter")
    window.set_default_size(800, 600)
    models: MutableState[Sequence[CounterModel]] = MutableState([CounterModel()])

    @into(window.set_content)
    def _():
        toolbar_view = Adw.ToolbarView()

        # Header bar with add button
        @into(toolbar_view.add_top_bar)
        def _():
            header_bar = Adw.HeaderBar()

            # Add Counter button in header
            @into(header_bar.pack_start)
            def _():
                add_button = Gtk.Button(label="Add Counter", css_classes=["suggested-action"])

                @subscribe(add_button, add_button, "clicked")
                def _(*_):
                    current_models = list(models.value)
                    current_models.append(CounterModel())
                    models.set(current_models)

                return add_button

            return header_bar

        # Main content area
        @into(toolbar_view.set_content)
        def _():
            scrolled = Gtk.ScrolledWindow(hexpand=True, vexpand=True, has_frame=False)
            scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

            @into(scrolled.set_child)
            def _():
                clamp = Adw.Clamp(maximum_size=600, tightening_threshold=400)

                @into(clamp.set_child)
                def _():
                    return CounterListBox(models, event_loop)

                return clamp

            return scrolled

        return toolbar_view

    return window


def App() -> Adw.Application:
    app = Adw.Application(application_id="com.example.CounterApp")

    @lambda f: app.connect("activate", f)
    def _(*_):
        event_loop, thread = start_event_loop()
        window = Window(event_loop)
        window.set_application(app)
        window.present()

    return app


if __name__ == "__main__":
    App().run([])
