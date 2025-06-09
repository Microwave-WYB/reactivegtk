import asyncio
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Callable

import gi

from reactivegtk import MutableState, State, WidgetLifecycle, start_event_loop
from reactivegtk.widgets import Conditional, ReactiveSequence
from reactivegtk.dsl import build, do, apply

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
    return build(
        Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6,
            valign=Gtk.Align.CENTER,
            halign=Gtk.Align.CENTER,
        ),
        lambda vbox: do(
            lifecycle := WidgetLifecycle(vbox),
            # Auto-increment effect
            lifecycle.watch(model.auto_increment, init=True)(
                lifecycle.effect(event_loop)(
                    lambda: auto_increment_effect(model)
                )
            ),
            # Lifecycle logging
            lifecycle.subscribe(vbox, "realize")(lambda *_: print("Counter widget realized")),
            lifecycle.subscribe(vbox, "unrealize")(lambda *_: print("Counter widget unrealized")),
            lifecycle.on_cleanup(lambda: print("Counter widget destroyed")),
            # Counter controls and buttons
            apply(vbox.append).foreach(
                # Counter controls
                build(
                    Gtk.Box(
                        orientation=Gtk.Orientation.HORIZONTAL,
                        spacing=12,
                        halign=Gtk.Align.CENTER,
                        valign=Gtk.Align.CENTER,
                    ),
                    lambda hbox: apply(hbox.append).foreach(
                        # Decrement button
                        build(
                            Gtk.Button(
                                icon_name="list-remove-symbolic",
                                css_classes=["circular"],
                                valign=Gtk.Align.CENTER,
                            ),
                            lambda dec_button: lifecycle.subscribe(dec_button, "clicked")(
                                lambda *_: model.count.update(lambda x: x - 1)
                            ),
                        ),
                        # Count label
                        build(
                            Gtk.Label(
                                css_classes=["title-2"],
                                margin_start=12,
                                margin_end=12,
                                valign=Gtk.Align.CENTER,
                            ),
                            lambda label: lifecycle.watch(model.count, init=True)(
                                lambda _: label.set_label(str(model.count.value))
                            ),
                        ),
                        # Increment button
                        build(
                            Gtk.Button(
                                icon_name="list-add-symbolic",
                                css_classes=["circular"],
                                valign=Gtk.Align.CENTER,
                            ),
                            lambda inc_button: lifecycle.subscribe(inc_button, "clicked")(
                                lambda *_: model.count.update(lambda x: x + 1)
                            ),
                        ),
                    ),
                ),
                # Reset button
                build(
                    Gtk.Button(label="Reset", css_classes=["destructive-action"]),
                    lambda reset_button: lifecycle.subscribe(reset_button, "clicked")(
                        lambda *_: model.count.set(0)
                    ),
                ),
                # Auto-increment toggle
                build(
                    Gtk.Button(),
                    lambda auto_button: do(
                        lifecycle.subscribe(auto_button, "clicked")(
                            lambda *_: model.auto_increment.update(lambda x: not x)
                        ),
                        lifecycle.watch(model.auto_increment, init=True)(
                            lambda auto: auto_button.set_label(
                                "Stop Auto-increment" if auto else "Start Auto-increment"
                            )
                        ),
                    ),
                ),
                # Remove button
                build(
                    Gtk.Button(
                        label="Remove Counter",
                        css_classes=["destructive-action"],
                        halign=Gtk.Align.CENTER,
                    ),
                    lambda remove_button: lifecycle.subscribe(remove_button, "clicked")(
                        lambda *_: on_remove(model)
                    ),
                ),
            ),
        ),
    )


async def auto_increment_effect(model: CounterModel):
    """Auto-increment effect that runs while auto is enabled"""
    while model.auto_increment.value:
        await asyncio.sleep(1)
        model.count.update(lambda x: x + 1)


def CounterFlowBoxChild(
    model: CounterModel,
    event_loop: asyncio.AbstractEventLoop,
    on_remove: Callable[[CounterModel], None],
) -> Gtk.FlowBoxChild:
    return build(
        Gtk.FlowBoxChild(),
        lambda child: child.set_child(
            build(
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

    return build(
        Adw.ApplicationWindow(title="Counter App"),
        lambda window: do(
            window.set_default_size(800, 600),
            window.set_content(
                build(
                    Adw.ToolbarView(),
                    lambda toolbar_view: do(
                        # Header bar with add button
                        toolbar_view.add_top_bar(
                            build(
                                Adw.HeaderBar(),
                                lambda header_bar: header_bar.pack_start(
                                    build(
                                        Gtk.Button(
                                            label="Add Counter", css_classes=["suggested-action"]
                                        ),
                                        lambda add_button: do(
                                            lifecycle := WidgetLifecycle(add_button),
                                            lifecycle.subscribe(add_button, "clicked")(
                                                lambda *_: add_counter()
                                            ),
                                        ),
                                    ),
                                ),
                            ),
                        ),
                        # Main content area
                        toolbar_view.set_content(
                            build(
                                Gtk.ScrolledWindow(hexpand=True, vexpand=True, has_frame=False),
                                lambda scrolled: do(
                                    scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC),
                                    scrolled.set_child(
                                        build(
                                            Adw.Clamp(maximum_size=900, tightening_threshold=600),
                                            lambda clamp: clamp.set_child(
                                                CounterList(models, event_loop, remove_counter)
                                            ),
                                        ),
                                    ),
                                ),
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