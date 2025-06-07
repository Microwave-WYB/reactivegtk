from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Callable
import gi
from reactivegtk import State, Topic, WidgetLifecycle, into, bind_sequence, Preview

gi.require_versions(
    {
        "Gtk": "4.0",
        "Adw": "1",
        "Gdk": "4.0",
    }
)
from gi.repository import Gtk, Adw  # type: ignore # noqa: E402


@dataclass(frozen=True)
class TaskModel:
    title: State[str]
    done: State[bool] = field(default_factory=lambda: State(False))


def TaskWidget(task: TaskModel, on_remove: Callable[[TaskModel], None]) -> Adw.ActionRow:
    row = Adw.ActionRow(title=task.title.value)
    lifecycle = WidgetLifecycle(row)

    @into(row.add_prefix)
    def _():
        checkbox = Gtk.CheckButton()

        task.done.bind(checkbox, "active")

        @lifecycle.watch((checkbox, "toggled"))
        def _():
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

        @lifecycle.watch((remove_button, "clicked"))
        def _():
            on_remove(task)

        return remove_button

    return row


def TaskList(
    tasks: State[Sequence[TaskModel]], on_remove: Callable[[TaskModel], None]
) -> Gtk.Widget:
    clamp = Adw.Clamp(maximum_size=800, tightening_threshold=400)

    @into(clamp.set_child)
    def _():
        listbox = Gtk.ListBox(
            width_request=300,
            selection_mode=Gtk.SelectionMode.NONE,
            css_classes=["boxed-list"],
        )

        @bind_sequence(listbox, tasks, key_fn=lambda t: t.title.value)
        def item_factory(task: TaskModel) -> Adw.ActionRow:
            return TaskWidget(task, on_remove)

        return listbox

    return clamp


def TodoApp() -> Gtk.Widget:
    box = Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL,
        spacing=12,
        margin_top=24,
        margin_bottom=24,
        margin_start=24,
        margin_end=24,
    )
    lifecycle = WidgetLifecycle(box)

    # Application state
    tasks = State[Sequence[TaskModel]](
        [
            TaskModel(State("Learn ReactiveGTK")),
            TaskModel(State("Build a todo app")),
            TaskModel(State("Write documentation")),
        ]
    )

    entry_text = State("")
    
    # Topics for event communication
    clear_entry_topic = Topic[None]()
    add_task_topic = Topic[str]()

    # Add task function
    def add_task(text: str = None):
        if text is None:
            text = entry_text.value.strip()
        if text:
            new_task = TaskModel(State(text))
            tasks.update(lambda ts: [*ts, new_task])
            clear_entry_topic.publish(None)

    # Remove task function
    def remove_task(task: TaskModel):
        tasks.update(lambda ts: [t for t in ts if t is not task])

    # Subscribe to add task events
    @lifecycle.subscribe(add_task_topic)
    def _(text: str):
        add_task(text)

    # Entry and add button
    @into(box.append)
    def _():
        entry_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=6, css_classes=["linked"]
        )

        @into(entry_box.append)
        def _():
            entry = Gtk.Entry(placeholder_text="Add a new task...", hexpand=True)

            @lifecycle.watch((entry, "changed"))
            def _():
                entry_text.set(entry.get_text())

            @lifecycle.watch((entry, "activate"))
            def _():
                add_task_topic.publish(entry_text.value.strip())

            # Subscribe to clear entry events
            @lifecycle.subscribe(clear_entry_topic)
            def _(_):
                entry.set_text("")
                entry_text.set("")

            return entry

        @into(entry_box.append)
        def _():
            add_button = Gtk.Button(
                icon_name="list-add-symbolic",
                tooltip_text="Add task",
            )

            @lifecycle.watch((add_button, "clicked"))
            def _():
                add_task_topic.publish(entry_text.value.strip())

            @lifecycle.watch(entry_text, init=True)
            def _():
                add_button.set_sensitive(bool(entry_text.value.strip()))

            return add_button

        return entry_box

    # Task list
    @into(box.append)
    def _():
        return TaskList(tasks, remove_task)

    # Task statistics
    @into(box.append)
    def _():
        stats_label = Gtk.Label(css_classes=["caption"])

        @lifecycle.watch(tasks, init=True)
        def _():
            total = len(tasks.value)
            completed = sum(1 for task in tasks.value if task.done.value)
            remaining = total - completed

            if total == 0:
                text = "No tasks"
            else:
                text = f"{completed}/{total} completed, {remaining} remaining"

            stats_label.set_text(text)

        return stats_label

    return box


if __name__ == "__main__":
    preview = Preview()

    @preview("TaskWidget")
    def _(_) -> Gtk.Widget:
        # Sample task for preview
        sample_task = TaskModel(State("Sample Task"))

        def dummy_remove(task):
            print(f"Would remove: {task.title.value}")

        listbox = Gtk.ListBox(
            selection_mode=Gtk.SelectionMode.NONE,
            css_classes=["boxed-list"],
            width_request=300,
        )

        listbox.append(TaskWidget(sample_task, dummy_remove))
        return listbox

    @preview("TaskList")
    def _(_) -> Gtk.Widget:
        # Sample tasks for preview
        sample_tasks = State[Sequence[TaskModel]](
            [
                TaskModel(State("Task 1")),
                TaskModel(State("Task 2")),
                TaskModel(State("Task 3")),
            ]
        )

        def dummy_remove(task):
            print(f"Would remove: {task.title.value}")

        return TaskList(sample_tasks, dummy_remove)

    @preview("TodoApp")
    def _(_) -> Gtk.Widget:
        return TodoApp()

    preview.run()
