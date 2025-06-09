import asyncio
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Callable

import gi

from reactivegtk import MutableState, State, WidgetLifecycle, start_event_loop, effect
from reactivegtk.widgets import Conditional, ReactiveSequence
from reactivegtk.dsl import ui, do, apply

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
    vbox = Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL,
        spacing=6,
        valign=Gtk.Align.CENTER,
        halign=Gtk.Align.CENTER,
    )
    lifecycle = WidgetLifecycle(vbox)

    @lifecycle.watch(model.auto_increment, init=True)
    @lifecycle.effect(event_loop)
    async def auto_increment():
        """Auto-increment effect that runs while auto is enabled"""
        while model.auto_increment.value:
            await asyncio.sleep(1)
            model.count.update(lambda x: x + 1)

    return ui(
        vbox,
        # Lifecycle logging
        lifecycle.subscribe(vbox, "realize")(lambda *_: print("Counter widget realized")),
        lifecycle.subscribe(vbox, "unrealize")(lambda *_: print("Counter widget unrealized")),
        lifecycle.on_cleanup()(lambda: print("Counter widget destroyed")),
        # Counter controls and buttons
        apply(vbox.append).foreach(
            # Counter controls
            ui(
                hbox := Gtk.Box(
                    orientation=Gtk.Orientation.HORIZONTAL,
                    spacing=12,
                    halign=Gtk.Align.CENTER,
                    valign=Gtk.Align.CENTER,
                ),
                apply(hbox.append).foreach(
                    # Decrement button
                    ui(
                        dec_button := Gtk.Button(
                            icon_name="list-remove-symbolic",
                            css_classes=["circular"],
                            valign=Gtk.Align.CENTER,
                        ),
                        lifecycle.subscribe(dec_button, "clicked")(
                            lambda *_: model.count.update(lambda x: x - 1)
                        ),
                    ),
                    # Count label
                    ui(
                        label := Gtk.Label(
                            css_classes=["title-2"],
                            margin_start=12,
                            margin_end=12,
                            valign=Gtk.Align.CENTER,
                        ),
                        lifecycle.watch(model.count, init=True)(
                            lambda _: label.set_label(str(model.count.value))
                        ),
                    ),
                    # Increment button
                    ui(
                        inc_button := Gtk.Button(
                            icon_name="list-add-symbolic",
                            css_classes=["circular"],
                            valign=Gtk.Align.CENTER,
                        ),
                        lifecycle.subscribe(inc_button, "clicked")(
                            lambda *_: model.count.update(lambda x: x + 1)
                        ),
                    ),
                ),
            ),
            # Reset button
            ui(
                reset_button := Gtk.Button(label="Reset", css_classes=["destructive-action"]),
                lifecycle.subscribe(reset_button, "clicked")(lambda *_: model.count.set(0)),
            ),
            # Auto-increment toggle
            ui(
                auto_button := Gtk.Button(),
                lifecycle.subscribe(auto_button, "clicked")(
                    lambda *_: model.auto_increment.update(lambda x: not x)
                ),
                lifecycle.watch(model.auto_increment, init=True)(
                    lambda auto: auto_button.set_label(
                        "Stop Auto-increment" if auto else "Start Auto-increment"
                    )
                ),
            ),
            # Remove button
            ui(
                remove_button := Gtk.Button(
                    label="Remove Counter",
                    css_classes=["destructive-action"],
                    halign=Gtk.Align.CENTER,
                ),
                lifecycle.subscribe(remove_button, "clicked")(lambda *_: on_remove(model)),
            ),
        ),
    )


def CounterFlowBoxChild(
    model: CounterModel,
    event_loop: asyncio.AbstractEventLoop,
    on_remove: Callable[[CounterModel], None],
) -> Gtk.FlowBoxChild:
    return ui(
        child := Gtk.FlowBoxChild(),
        child.set_child(
            ui(
                container := Gtk.Box(
                    orientation=Gtk.Orientation.VERTICAL,
                    spacing=6,
                    margin_top=12,
                    margin_bottom=12,
                    margin_start=12,
                    margin_end=12,
                ),
                container.append(CounterWidget(model, event_loop, on_remove)),
            ),
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
            models,
            lambda model: CounterFlowBoxChild(model, event_loop, on_remove),
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
        current_models = list(models.value)
        current_models.append(CounterModel())
        models.set(current_models)

    def remove_counter(model: CounterModel):
        current_models = list(models.value)
        try:
            current_models.remove(model)
            models.set(current_models)
        except ValueError:
            pass

    return ui(
        window := Adw.ApplicationWindow(title="Counter App"),
        window.set_default_size(800, 600),
        window.set_content(
            ui(
                toolbar_view := Adw.ToolbarView(),
                # Header bar with add button
                toolbar_view.add_top_bar(
                    ui(
                        header_bar := Adw.HeaderBar(),
                        header_bar.pack_start(
                            ui(
                                add_button := Gtk.Button(
                                    label="Add Counter", css_classes=["suggested-action"]
                                ),
                                lifecycle := WidgetLifecycle(add_button),
                                lifecycle.subscribe(add_button, "clicked")(
                                    lambda *_: add_counter()
                                ),
                            ),
                        ),
                    ),
                ),
                # Main content area
                toolbar_view.set_content(
                    ui(
                        scrolled := Gtk.ScrolledWindow(hexpand=True, vexpand=True, has_frame=False),
                        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC),
                        scrolled.set_child(
                            ui(
                                clamp := Adw.Clamp(maximum_size=900, tightening_threshold=600),
                                clamp.set_child(CounterList(models, event_loop, remove_counter)),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )


def App() -> Adw.Application:
    event_loop, thread = start_event_loop()
    return do(
        app := Adw.Application(application_id="com.example.CounterApp"),
        app.connect(
            "activate",
            lambda *_: do(
                event_loop,
                window := CounterWindow(event_loop),
                window.set_application(app),
                window.present(),
            ),
        ),
        ret=app,
    )


if __name__ == "__main__":
    App().run([])
