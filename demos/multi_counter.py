import asyncio
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Callable

import gi

from reactivegtk import MutableState, State, effect, start_event_loop
from reactivegtk.dsl import apply, build, do
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
    @effect(event_loop)
    async def auto_increment_effect(enabled: bool):
        """Auto-increment effect that runs while auto is enabled"""
        while enabled:
            await asyncio.sleep(1)
            model.count.update(lambda x: x + 1)

    model.auto_increment.watch(auto_increment_effect, init=True)

    return build(
        Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6,
            valign=Gtk.Align.CENTER,
            halign=Gtk.Align.CENTER,
        ),
        lambda vbox: do(
            vbox.connect("destroy", lambda *_: print("Counter widget destroyed")),
            # Counter controls and buttons
            apply(vbox.append).foreach(
                # Count label
                build(
                    Gtk.Label(
                        css_classes=["title-2"],
                        margin_start=12,
                        margin_end=12,
                        valign=Gtk.Align.CENTER,
                    ),
                    lambda count_label: model.count.map(str).bind(count_label, "label"),
                ),
                # Reset button
                build(
                    Gtk.Button(label="Reset", css_classes=["destructive-action"]),
                    lambda reset_button: reset_button.connect("clicked", lambda *_: model.count.set(0)),
                ),
                # Auto-increment toggle
                build(
                    Gtk.Button(),
                    lambda auto_button: do(
                        auto_button.connect("clicked", lambda *_: model.auto_increment.update(lambda x: not x)),
                        model.auto_increment.map(
                            lambda auto: "Stop Auto-increment" if auto else "Start Auto-increment"
                        ).bind(auto_button, "label"),
                    ),
                ),
                # Remove button
                build(
                    Gtk.Button(
                        label="Remove Counter",
                        css_classes=["destructive-action"],
                        halign=Gtk.Align.CENTER,
                    ),
                    lambda remove_button: remove_button.connect("clicked", lambda *_: on_remove(model)),
                ),
            ),
        ),
    )


def CounterFlowBoxChild(
    model: CounterModel,
    event_loop: asyncio.AbstractEventLoop,
    on_remove: Callable[[CounterModel], None],
) -> Gtk.FlowBoxChild:
    return Gtk.FlowBoxChild(
        child=build(
            Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL,
                spacing=6,
                margin_top=12,
                margin_bottom=12,
                margin_start=12,
                margin_end=12,
            ),
            lambda container: container.append(CounterWidget(model, event_loop, on_remove)),
        ),
    )


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

    return Adw.ApplicationWindow(
        title="Counter App",
        default_width=800,
        default_height=600,
        content=build(
            Adw.ToolbarView(
                content=Gtk.ScrolledWindow(
                    hexpand=True,
                    vexpand=True,
                    has_frame=False,
                    hscrollbar_policy=Gtk.PolicyType.NEVER,
                    vscrollbar_policy=Gtk.PolicyType.AUTOMATIC,
                    child=Adw.Clamp(
                        maximum_size=900,
                        tightening_threshold=600,
                        child=CounterList(models, event_loop, remove_counter),
                    ),
                ),
            ),
            lambda toolbar_view: do(
                # Header bar with add button
                toolbar_view.add_top_bar(
                    build(
                        Adw.HeaderBar(),
                        lambda header_bar: header_bar.pack_start(
                            build(
                                Gtk.Button(label="Add Counter", css_classes=["suggested-action"]),
                                lambda add_button: do(add_button.connect("clicked", lambda *_: add_counter())),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )


def App() -> Adw.Application:
    event_loop, _ = start_event_loop()
    return build(
        Adw.Application(application_id="com.example.CounterApp"),
        lambda app: do(
            app.connect(
                "activate",
                lambda *_: do(
                    event_loop,
                    window := CounterWindow(event_loop),
                    window.set_application(app),
                    window.present(),
                ),
            ),
        ),
    )


if __name__ == "__main__":
    App().run([])
