from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Callable

import gi

from reactivegtk import MutableState, Preview, State, WidgetLifecycle, into
from reactivegtk.widgets import Conditional, ReactiveSequence

gi.require_versions(
    {
        "Gtk": "4.0",
        "Adw": "1",
        "Gdk": "4.0",
    }
)
from gi.repository import Adw, Gtk  # type: ignore # noqa: E402


@dataclass(frozen=True)
class TaskModel:
    title: MutableState[str]
    done: MutableState[bool] = field(default_factory=lambda: MutableState(False))


def TaskWidget(task: TaskModel, on_remove: Callable[[TaskModel], None]) -> Adw.ActionRow:
    row = Adw.ActionRow()
    task.title.bind(row, "title")
    lifecycle = WidgetLifecycle(row)

    @into(row.add_prefix)
    def _():
        checkbox = Gtk.CheckButton(
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER,
        )

        @lifecycle.subscribe(checkbox, "toggled")
        def _(_):
            task.done.set(checkbox.get_active())

        return checkbox

    @into(row.add_suffix)
    def _():
        remove_button = Gtk.Button(
            icon_name="user-trash-symbolic",
            valign=Gtk.Align.CENTER,
            css_classes=["circular", "destructive-action"],
            tooltip_text="Remove task",
        )

        @lifecycle.subscribe(remove_button, "clicked")
        def _(_):
            on_remove(task)

        return remove_button

    return row


def TaskList(
    tasks: State[Sequence[TaskModel]],
    on_remove: Callable[[TaskModel], None],
) -> Gtk.Widget:
    overlay = Gtk.Overlay()

    @into(overlay.set_child)
    def _():
        return Conditional(
            tasks.map(bool),
            true=ReactiveSequence(
                Gtk.ListBox(
                    selection_mode=Gtk.SelectionMode.NONE,
                    css_classes=["boxed-list"],
                    margin_bottom=12,
                ),
                tasks,
                lambda task: TaskWidget(task, on_remove=on_remove),
            ),
            false=Gtk.Label(
                label="No tasks yet",
                css_classes=["dim-label"],
                margin_top=48,
                margin_bottom=48,
            ),
        )

    return overlay


class TodoViewModel:
    def __init__(self):
        self.tasks = MutableState[Sequence[TaskModel]]([])
        self.entry_text = MutableState("")
        self.stats = MutableState[tuple[int, int]]((0, 0))
        self.tasks.watch(lambda _: self.update_stats(), init=True)

    def update_stats(self) -> None:
        done_count = sum(1 for task in self.tasks.value if task.done.value)
        total_count = len(self.tasks.value)
        self.stats.set((done_count, total_count))

    def add_task(self, text: str) -> None:
        text = text.strip()
        if not text:
            return None
        new_task = TaskModel(MutableState(text))
        new_task.done.watch(lambda _: self.update_stats(), init=True)

        self.tasks.update(lambda ts: [*ts, new_task])
        self.entry_text.set("")

    def remove_task(self, task: TaskModel):
        self.tasks.update(lambda ts: [t for t in ts if t is not task])


def TodoView(view_model: TodoViewModel) -> Gtk.Widget:
    clamp = Adw.Clamp(
        maximum_size=500,
        tightening_threshold=400,
        margin_start=12,
        margin_end=12,
    )

    @into(clamp.set_child)
    def _() -> Gtk.Widget:
        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
            valign=Gtk.Align.START,
        )
        lifecycle = WidgetLifecycle(clamp)

        @into(box.append)
        def _():
            entry_box = Gtk.Box(
                orientation=Gtk.Orientation.HORIZONTAL, spacing=6, css_classes=["linked"]
            )

            @into(entry_box.append)
            def _():
                entry = Gtk.Entry(
                    placeholder_text="Add a new task...",
                    hexpand=True,
                )

                view_model.entry_text.twoway_bind(entry, "text")

                @lifecycle.subscribe(entry, "activate")
                def _(_):
                    view_model.add_task(view_model.entry_text.value.strip())

                return entry

            @into(entry_box.append)
            def _():
                add_button = Gtk.Button(
                    icon_name="list-add-symbolic",
                    tooltip_text="Add task",
                    css_classes=["suggested-action"],
                )

                view_model.entry_text.map(lambda t: bool(t.strip())).bind(add_button, "sensitive")

                @lifecycle.subscribe(add_button, "clicked")
                def _(_):
                    view_model.add_task(view_model.entry_text.value.strip())

                return add_button

            return entry_box

        @into(box.append)
        def _():
            scrolled = Gtk.ScrolledWindow(
                hscrollbar_policy=Gtk.PolicyType.NEVER,
                vscrollbar_policy=Gtk.PolicyType.AUTOMATIC,
                has_frame=False,
                propagate_natural_height=True,
                vexpand=True,
            )

            scrolled.set_child(TaskList(view_model.tasks, on_remove=view_model.remove_task))
            return scrolled

        return box

    return clamp


def TodoWindow() -> Adw.Window:
    window = Adw.Window(title="Todo App")
    window.set_default_size(300, 600)
    window.set_resizable(True)

    toolbar_view = Adw.ToolbarView(
        top_bar_style=Adw.ToolbarStyle.FLAT, bottom_bar_style=Adw.ToolbarStyle.RAISED
    )
    toolbar_view.add_top_bar(Adw.HeaderBar())

    view_model = TodoViewModel()
    toolbar_view.set_content(TodoView(view_model))

    stats_label = Gtk.Label(css_classes=["caption"])
    view_model.stats.map(lambda stats: f"Done: {stats[0]} / Total: {stats[1]}").bind(
        stats_label, "label"
    )
    toolbar_view.add_bottom_bar(stats_label)

    window.set_content(toolbar_view)
    return window


if __name__ == "__main__":
    preview = Preview()

    @preview("TaskWidget")
    def _(_) -> Gtk.Widget:
        sample_task = TaskModel(MutableState("Sample Task"))

        listbox = Gtk.ListBox(
            selection_mode=Gtk.SelectionMode.NONE,
            css_classes=["boxed-list"],
            width_request=300,
        )

        listbox.append(
            TaskWidget(sample_task, lambda task: print(f"Would remove: {task.title.value}"))
        )
        return listbox

    @preview("TaskList")
    def _(_) -> Gtk.Widget:
        sample_tasks = State[Sequence[TaskModel]](
            [
                TaskModel(MutableState("Task 1")),
                TaskModel(MutableState("Task 2")),
                TaskModel(MutableState("Task 3")),
            ]
        )

        return Gtk.Overlay(
            width_request=300,
            child=TaskList(sample_tasks, lambda task: print(f"Would remove: {task.title.value}")),
        )

    @preview("TodoView")
    def _(_) -> Gtk.Widget:
        return Gtk.Overlay(
            width_request=300,
            child=TodoView(TodoViewModel()),
        )

    @preview("TodoWindow")
    def _(_) -> Adw.Window:
        return TodoWindow()

    preview.run()
