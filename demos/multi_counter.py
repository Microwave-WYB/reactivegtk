import asyncio
from collections.abc import Sequence
from dataclasses import dataclass, field
from functools import partial
from typing import Callable

import gi

from reactivegtk import MutableState, State, apply, effect, start_event_loop
from reactivegtk.widgets import Conditional, ReactiveSequence

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
    auto_increment: MutableState[bool] = field(default_factory=lambda: MutableState(False))


def CounterWidget(
    model: CounterModel,
    event_loop: asyncio.AbstractEventLoop,
    on_remove: Callable[[CounterModel], None],
) -> Gtk.Widget:
    @model.auto_increment.watch
    @effect(event_loop)
    async def auto_increment_effect(enabled: bool):
        """Auto-increment effect that runs while auto is enabled"""
        while enabled:
            await asyncio.sleep(1)
            model.count.update(lambda x: x + 1)

    vbox = Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL,
        spacing=6,
        valign=Gtk.Align.CENTER,
        halign=Gtk.Align.CENTER,
    )

    @partial(vbox.connect, "destroy")
    def _(*_):
        print("Counter widget destroyed")

    # Count label
    @apply(vbox.append)
    def _():
        count_label = Gtk.Label(
            css_classes=["title-2"],
            margin_start=12,
            margin_end=12,
            valign=Gtk.Align.CENTER,
        )
        model.count.map(str).bind(count_label, "label")
        return count_label

    # Reset button
    @apply(vbox.append)
    def _():
        reset_button = Gtk.Button(label="Reset", css_classes=["destructive-action"])

        @partial(reset_button.connect, "clicked")
        def _(*_):
            model.count.set(0)

        return reset_button

    # Auto-increment toggle
    @apply(vbox.append)
    def _():
        auto_button = Gtk.Button()

        @partial(auto_button.connect, "clicked")
        def _(*_):
            model.auto_increment.update(lambda x: not x)

        model.auto_increment.map(lambda auto: "Stop Auto-increment" if auto else "Start Auto-increment").bind(
            auto_button, "label"
        )

        return auto_button

    # Remove button
    @apply(vbox.append)
    def _():
        remove_button = Gtk.Button(
            label="Remove Counter",
            css_classes=["destructive-action"],
            halign=Gtk.Align.CENTER,
        )

        @partial(remove_button.connect, "clicked")
        def _(*_):
            on_remove(model)

        return remove_button

    return vbox


def CounterFlowBoxChild(
    model: CounterModel,
    event_loop: asyncio.AbstractEventLoop,
    on_remove: Callable[[CounterModel], None],
) -> Gtk.FlowBoxChild:
    flowbox_child = Gtk.FlowBoxChild()

    @apply(flowbox_child.set_child)
    def _():
        container = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6,
            margin_top=12,
            margin_bottom=12,
            margin_start=12,
            margin_end=12,
        )
        container.append(CounterWidget(model, event_loop, on_remove))
        return container

    return flowbox_child


def CounterList(
    models: State[Sequence[CounterModel]],
    event_loop: asyncio.AbstractEventLoop,
    on_remove: Callable[[CounterModel], None],
) -> Gtk.Widget:
    return Conditional(
        models.map(bool),
        true=ReactiveSequence(
            Gtk.FlowBox(
                margin_top=12,
                margin_bottom=12,
                margin_start=12,
                margin_end=12,
                selection_mode=Gtk.SelectionMode.NONE,
                min_children_per_line=1,
                max_children_per_line=3,
                column_spacing=12,
                row_spacing=12,
                homogeneous=True,
            ),
            items=models,
            factory=lambda model: CounterFlowBoxChild(model, event_loop, on_remove),
        ),
        false=Gtk.Label(
            label="No counters yet. Click 'Add Counter' to get started!",
            css_classes=["dim-label"],
            margin_top=48,
            margin_bottom=48,
        ),
    )


def CounterWindow(event_loop: asyncio.AbstractEventLoop) -> Adw.ApplicationWindow:
    models: MutableState[Sequence[CounterModel]] = MutableState([CounterModel()])

    def add_counter():
        models.update(lambda ms: [*ms, CounterModel()])

    def remove_counter(model: CounterModel):
        models.update(lambda ms: [m for m in ms if m is not model])

    window = Adw.ApplicationWindow(
        title="Counter App",
        default_width=800,
        default_height=600,
    )

    @apply(window.set_content)
    def _():
        toolbar_view = Adw.ToolbarView()

        # Set main content
        @apply(toolbar_view.set_content)
        def _():
            scrolled = Gtk.ScrolledWindow(
                hexpand=True,
                vexpand=True,
                has_frame=False,
                hscrollbar_policy=Gtk.PolicyType.NEVER,
                vscrollbar_policy=Gtk.PolicyType.AUTOMATIC,
            )

            @apply(scrolled.set_child)
            def _():
                clamp = Adw.Clamp(
                    maximum_size=900,
                    tightening_threshold=600,
                )
                clamp.set_child(CounterList(models, event_loop, remove_counter))
                return clamp

            return scrolled

        # Header bar with add button
        @apply(toolbar_view.add_top_bar)
        def _():
            header_bar = Adw.HeaderBar()

            @apply(header_bar.pack_start)
            def _():
                add_button = Gtk.Button(label="Add Counter", css_classes=["suggested-action"])

                @partial(add_button.connect, "clicked")
                def _(*_):
                    add_counter()

                return add_button

            return header_bar

        return toolbar_view

    return window


def App() -> Adw.Application:
    event_loop, thread = start_event_loop()
    app = Adw.Application(application_id="com.example.CounterApp")

    @partial(app.connect, "activate")
    def _(*_):
        window = CounterWindow(event_loop)
        window.set_application(app)
        window.present()

    return app


if __name__ == "__main__":
    App().run([])
