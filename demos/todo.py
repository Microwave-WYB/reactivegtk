from collections.abc import Sequence
from typing import Callable

import gi

from reactivegtk import MutableState, Preview, State
from reactivegtk.dsl import apply, build, do
from reactivegtk.widgets import Conditional, ReactiveSequence

gi.require_versions(
    {
        "Gtk": "4.0",
        "Adw": "1",
        "Gdk": "4.0",
    }
)
from gi.repository import Adw, GObject, Gtk  # type: ignore # noqa: E402


class TaskViewModel:
    def __init__(self, title: str):
        self._title: MutableState[str] = MutableState(title)
        self._done: MutableState[bool] = MutableState(False)

    @property
    def title(self) -> State[str]:
        return self._title

    @property
    def done(self) -> State[bool]:
        return self._done

    def set_title(self, title: str) -> None:
        self._title.set(title)

    def bind_done_twoway(self, obj: GObject.Object, property_name: str) -> GObject.Binding:
        """Bind done state to a GObject property with two-way binding"""
        return self._done.twoway_bind(obj, property_name)


def TaskWidget(task: TaskViewModel, on_remove: Callable[[TaskViewModel], None]) -> Adw.ActionRow:
    return build(
        Adw.ActionRow(),
        lambda row: do(
            task.title.bind(row, "title"),
            row.add_prefix(
                build(
                    Gtk.CheckButton(
                        halign=Gtk.Align.CENTER,
                        valign=Gtk.Align.CENTER,
                    ),
                    lambda checkbox: task.bind_done_twoway(checkbox, "active"),
                ),
            ),
            row.add_suffix(
                build(
                    Gtk.Button(
                        icon_name="user-trash-symbolic",
                        valign=Gtk.Align.CENTER,
                        css_classes=["circular", "destructive-action"],
                        tooltip_text="Remove task",
                    ),
                    lambda remove_button: remove_button.connect("clicked", lambda *_: on_remove(task)),
                ),
            ),
        ),
    )


def TaskList(
    tasks: State[Sequence[TaskViewModel]],
    on_remove: Callable[[TaskViewModel], None],
) -> Gtk.Widget:
    return Conditional(
        tasks.map(bool),
        true=ReactiveSequence(
            Gtk.ListBox(
                selection_mode=Gtk.SelectionMode.NONE,
                css_classes=["boxed-list"],
                margin_top=4,
                margin_start=4,
                margin_end=4,
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


class TodoViewModel:
    def __init__(self):
        self._tasks = MutableState[Sequence[TaskViewModel]]([])
        self._entry_text = MutableState("")
        self._stats = MutableState[tuple[int, int]]((0, 0))
        self._tasks.watch(lambda _: self.update_stats(), init=True)

    @property
    def tasks(self) -> State[Sequence[TaskViewModel]]:
        return self._tasks

    @property
    def entry_text(self) -> State[str]:
        return self._entry_text

    def bind_entry_text_twoway(self, obj: GObject.Object, property_name: str) -> None:
        """Bind entry text to a GObject property with two-way binding"""
        self._entry_text.twoway_bind(obj, property_name)

    @property
    def stats(self) -> State[tuple[int, int]]:
        return self._stats

    def update_stats(self) -> None:
        done_count = sum(1 for task in self._tasks.value if task.done.value)
        total_count = len(self._tasks.value)
        self._stats.set((done_count, total_count))

    def add_task(self) -> None:
        text = self._entry_text.value.strip()
        if not text:
            return None
        new_task = TaskViewModel(text)
        new_task._done.watch(lambda _: self.update_stats(), init=True)

        self._tasks.update(lambda ts: [*ts, new_task])
        self._entry_text.set("")

    def remove_task(self, task: TaskViewModel):
        self._tasks.update(lambda ts: [t for t in ts if t is not task])

    def set_entry_text(self, text: str) -> None:
        self._entry_text.set(text)


def TodoView(view_model: TodoViewModel) -> Gtk.Widget:
    def TaskEntry() -> Gtk.Entry:
        return build(
            Gtk.Entry(
                placeholder_text="Add a new task...",
                hexpand=True,
            ),
            lambda entry: do(
                view_model.bind_entry_text_twoway(entry, "text"),
            ),
        )

    def TaskAddButton() -> Gtk.Button:
        return build(
            Gtk.Button(
                icon_name="list-add-symbolic",
                tooltip_text="Add task",
                css_classes=["suggested-action"],
            ),
            lambda add_button: do(
                view_model.entry_text.map(lambda t: bool(t.strip())).bind(add_button, "sensitive"),
            ),
        )

    return build(
        Adw.Clamp(
            maximum_size=500,
            tightening_threshold=400,
            margin_start=12,
            margin_end=12,
        ),
        lambda clamp: do(
            clamp.set_child(
                build(
                    Gtk.Box(
                        orientation=Gtk.Orientation.VERTICAL,
                        spacing=12,
                        valign=Gtk.Align.START,
                    ),
                    lambda box: apply(box.append).foreach(
                        build(
                            Gtk.Box(
                                orientation=Gtk.Orientation.HORIZONTAL,
                                spacing=6,
                                css_classes=["linked"],
                            ),
                            lambda entry_box: apply(entry_box.append).foreach(
                                build(
                                    TaskEntry(),
                                    lambda entry: entry.connect(
                                        "activate",
                                        lambda *_: view_model.add_task(),
                                    ),
                                ),
                                build(
                                    TaskAddButton(),
                                    lambda add_button: add_button.connect(
                                        "clicked",
                                        lambda *_: view_model.add_task(),
                                    ),
                                ),
                            ),
                        ),
                        build(
                            Gtk.ScrolledWindow(
                                hscrollbar_policy=Gtk.PolicyType.NEVER,
                                vscrollbar_policy=Gtk.PolicyType.AUTOMATIC,
                                has_frame=False,
                                propagate_natural_height=True,
                                vexpand=True,
                            ),
                            lambda scrolled: scrolled.set_child(
                                TaskList(view_model.tasks, on_remove=view_model.remove_task)
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )


def TodoWindow() -> Adw.Window:
    view_model = TodoViewModel()

    return build(
        Adw.Window(title="Todo App"),
        lambda window: do(
            window.set_default_size(300, 600),
            window.set_resizable(True),
            window.set_content(
                build(
                    Adw.ToolbarView(
                        top_bar_style=Adw.ToolbarStyle.FLAT,
                        bottom_bar_style=Adw.ToolbarStyle.RAISED,
                    ),
                    lambda toolbar_view: do(
                        toolbar_view.add_top_bar(
                            Adw.HeaderBar(
                                title_widget=Adw.WindowTitle(title="Todo App"),
                                show_start_title_buttons=False,
                            ),
                        ),
                        toolbar_view.set_content(TodoView(view_model)),
                        toolbar_view.add_bottom_bar(
                            build(
                                Gtk.Label(css_classes=["caption"]),
                                lambda stats_label: view_model.stats.map(
                                    lambda stats: f"Done: {stats[0]} / Total: {stats[1]}"
                                ).bind(stats_label, "label"),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )


if __name__ == "__main__":
    preview = Preview()

    @preview("TaskWidget")
    def _(_) -> Gtk.Widget:
        sample_task = TaskViewModel("Sample Task")

        return build(
            Gtk.ListBox(
                selection_mode=Gtk.SelectionMode.NONE,
                css_classes=["boxed-list"],
                width_request=300,
                margin_bottom=4,
                margin_top=4,
                margin_start=4,
                margin_end=4,
            ),
            lambda listbox: listbox.append(
                TaskWidget(sample_task, lambda task: print(f"Would remove: {task.title.value}")),
            ),
        )

    @preview("TaskList")
    def _(_) -> Gtk.Widget:
        sample_tasks = State[Sequence[TaskViewModel]](
            [
                TaskViewModel("Task 1"),
                TaskViewModel("Task 2"),
                TaskViewModel("Task 3"),
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
