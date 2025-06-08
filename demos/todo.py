from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Callable

import gi

from reactivegtk import MutableState, Preview, State, WidgetLifecycle, bind_sequence, into

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
    title: State[str]
    done: State[bool] = field(default_factory=lambda: State(False))


def TaskWidget(task: TaskModel, on_remove: Callable[[TaskModel], None]) -> Adw.ActionRow:
    row = Adw.ActionRow(title=task.title.value)
    lifecycle = WidgetLifecycle(row)

    @lifecycle.on_cleanup()
    def _():
        print(f"TaskWidget: Destroying task '{task.title.value}'")

    @into(row.add_prefix)
    def _():
        checkbox = Gtk.CheckButton()
        task.done.bind(checkbox, "active", two_way=True)

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
    clamp = Adw.Clamp(maximum_size=800, tightening_threshold=400)
    lifecycle = WidgetLifecycle(clamp)

    listbox = Gtk.ListBox(
        width_request=300,
        selection_mode=Gtk.SelectionMode.NONE,
        css_classes=["boxed-list"],
    )

    @bind_sequence(listbox, tasks)
    def _(task: TaskModel) -> Adw.ActionRow:
        return TaskWidget(task, on_remove=on_remove)

    @lifecycle.watch(tasks, init=True)
    def _(value: Sequence[TaskModel]):
        if not value:
            clamp.set_child(None)
        else:
            clamp.set_child(listbox)

    return clamp


class TodoViewModel:
    def __init__(self):
        self.tasks = MutableState[Sequence[TaskModel]]([])
        self.entry_text = MutableState("")
        self.stats = MutableState[tuple[int, int]]((0, 0))
        self.tasks.watch(lambda _: self.update_stats(), init=True)

    def update_stats(self) -> None:
        """Update statistics based on current tasks."""
        done_count = sum(1 for task in self.tasks.value if task.done.value)
        total_count = len(self.tasks.value)
        self.stats.set((done_count, total_count))

    def add_task(self, text: str) -> None:
        text = text.strip()
        if not text:
            return None
        new_task = TaskModel(State(text))
        new_task.done.watch(lambda _: self.update_stats(), init=True)

        self.tasks.update(lambda ts: [*ts, new_task])
        self.entry_text.set("")

    def remove_task(self, task: TaskModel):
        self.tasks.update(lambda ts: [t for t in ts if t is not task])


def TodoView(view_model: TodoViewModel) -> Gtk.Widget:
    box = Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL,
        spacing=12,
        margin_top=24,
        margin_bottom=24,
        margin_start=24,
        margin_end=24,
    )
    lifecycle = WidgetLifecycle(box)

    @into(box.append)
    def _():
        entry_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=6, css_classes=["linked"]
        )

        @into(entry_box.append)
        def _():
            entry = Gtk.Entry(placeholder_text="Add a new task...", hexpand=True, width_request=300)

            view_model.entry_text.bind(entry, "text", two_way=True)

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
        return TaskList(view_model.tasks, on_remove=view_model.remove_task)

    @into(box.append)
    def _():
        stats_label = Gtk.Label(css_classes=["caption"])
        view_model.stats.map(lambda stats: f"Done: {stats[0]} / Total: {stats[1]}").bind(
            stats_label, "label"
        )

        return stats_label

    return box


def TodoWindow() -> Adw.Window:
    """Create the main application window for the Todo app."""
    window = Adw.Window(title="Todo App")
    window.set_default_size(400, 600)

    @into(window.set_content)
    def _():
        toolbar_view = Adw.ToolbarView(top_bar_style=Adw.ToolbarStyle.FLAT)
        toolbar_view.add_top_bar(Adw.HeaderBar())
        toolbar_view.set_content(TodoView(TodoViewModel()))

        return toolbar_view

    return window


if __name__ == "__main__":
    preview = Preview()

    @preview("TaskWidget")
    def _(_) -> Gtk.Widget:
        sample_task = TaskModel(State("Sample Task"))

        def dummy_remove(task):
            print(f"TaskWidget: Would remove: {task.title.value}")

        listbox = Gtk.ListBox(
            selection_mode=Gtk.SelectionMode.NONE,
            css_classes=["boxed-list"],
            width_request=300,
        )

        listbox.append(TaskWidget(sample_task, dummy_remove))
        return listbox

    @preview("TaskList")
    def _(_) -> Gtk.Widget:
        sample_tasks = State[Sequence[TaskModel]](
            [
                TaskModel(State("Task 1")),
                TaskModel(State("Task 2")),
                TaskModel(State("Task 3")),
            ]
        )

        def dummy_remove(task):
            print(f"TaskList: Would remove: {task.title.value}")

        return TaskList(sample_tasks, dummy_remove)

    @preview("TodoView")
    def _(_) -> Gtk.Widget:
        return TodoView(TodoViewModel())

    @preview("TodoWindow")
    def _(_) -> Adw.Window:
        return TodoWindow()

    preview.run()
