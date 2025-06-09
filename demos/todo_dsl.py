from collections.abc import Sequence
from typing import Callable

import gi

from reactivegtk import MutableState, Preview, State, WidgetLifecycle
from reactivegtk.widgets import Conditional, ReactiveSequence
from reactivegtk.dsl import apply, do, ui

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
    return ui(
        row := Adw.ActionRow(),
        lifecycle := WidgetLifecycle(row),
        task.title.bind(row, "title"),
        row.add_prefix(
            ui(
                checkbox := Gtk.CheckButton(
                    halign=Gtk.Align.CENTER,
                    valign=Gtk.Align.CENTER,
                ),
                task.bind_done_twoway(checkbox, "active"),
            )
        ),
        row.add_suffix(
            ui(
                remove_button := Gtk.Button(
                    icon_name="user-trash-symbolic",
                    valign=Gtk.Align.CENTER,
                    css_classes=["circular", "destructive-action"],
                    tooltip_text="Remove task",
                ),
                lifecycle.subscribe(remove_button, "clicked")(lambda _: on_remove(task)),
            )
        ),
    )


def TaskList(
    tasks: State[Sequence[TaskViewModel]],
    on_remove: Callable[[TaskViewModel], None],
) -> Gtk.Widget:
    return ui(
        overlay := Gtk.Overlay(),
        overlay.set_child(
            Conditional(
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

    def add_task(self, text: str) -> None:
        text = text.strip()
        if not text:
            return None
        new_task = TaskViewModel(text)
        new_task._done.watch(lambda _: self.update_stats(), init=True)

        self._tasks.update(lambda ts: [*ts, new_task])

    def remove_task(self, task: TaskViewModel):
        self._tasks.update(lambda ts: [t for t in ts if t is not task])

    def set_entry_text(self, text: str) -> None:
        self._entry_text.set(text)

    def clear_entry_text(self) -> None:
        self._entry_text.set("")


def TodoView(view_model: TodoViewModel) -> Gtk.Widget:
    return ui(
        clamp := Adw.Clamp(
            maximum_size=500,
            tightening_threshold=400,
            margin_start=12,
            margin_end=12,
        ),
        lifecycle := WidgetLifecycle(clamp),
        clamp.set_child(
            ui(
                box := Gtk.Box(
                    orientation=Gtk.Orientation.VERTICAL,
                    spacing=12,
                    valign=Gtk.Align.START,
                ),
                apply(box.append).foreach(
                    ui(
                        entry_box := Gtk.Box(
                            orientation=Gtk.Orientation.HORIZONTAL,
                            spacing=6,
                            css_classes=["linked"],
                        ),
                        apply(entry_box.append).foreach(
                            ui(
                                entry := Gtk.Entry(
                                    placeholder_text="Add a new task...",
                                    hexpand=True,
                                ),
                                view_model.bind_entry_text_twoway(entry, "text"),
                                lifecycle.subscribe(entry, "activate")(
                                    lambda _: do(
                                        view_model.add_task(view_model.entry_text.value),
                                        view_model.clear_entry_text(),
                                    )
                                ),
                            ),
                            ui(
                                add_button := Gtk.Button(
                                    icon_name="list-add-symbolic",
                                    tooltip_text="Add task",
                                    css_classes=["suggested-action"],
                                ),
                                view_model.entry_text.map(lambda t: bool(t.strip())).bind(
                                    add_button, "sensitive"
                                ),
                                lifecycle.subscribe(add_button, "clicked")(
                                    lambda _: do(
                                        view_model.add_task(view_model.entry_text.value),
                                        view_model.clear_entry_text(),
                                    )
                                ),
                            ),
                        ),
                    ),
                    ui(
                        scrolled := Gtk.ScrolledWindow(
                            hscrollbar_policy=Gtk.PolicyType.NEVER,
                            vscrollbar_policy=Gtk.PolicyType.AUTOMATIC,
                            has_frame=False,
                            propagate_natural_height=True,
                            vexpand=True,
                        ),
                        scrolled.set_child(
                            TaskList(view_model.tasks, on_remove=view_model.remove_task)
                        ),
                    ),
                ),
            )
        ),
    )


def TodoWindow() -> Adw.Window:
    view_model = TodoViewModel()

    return ui(
        window := Adw.Window(title="Todo App"),
        window.set_default_size(300, 600),
        window.set_resizable(True),
        window.set_content(
            ui(
                toolbar_view := Adw.ToolbarView(
                    top_bar_style=Adw.ToolbarStyle.FLAT,
                    bottom_bar_style=Adw.ToolbarStyle.RAISED,
                ),
                toolbar_view.add_top_bar(
                    Adw.HeaderBar(
                        title_widget=Adw.WindowTitle(title="Todo App"),
                        show_start_title_buttons=False,
                    )
                ),
                toolbar_view.set_content(TodoView(view_model)),
                toolbar_view.add_bottom_bar(
                    ui(
                        stats_label := Gtk.Label(css_classes=["caption"]),
                        view_model.stats.map(
                            lambda stats: f"Done: {stats[0]} / Total: {stats[1]}"
                        ).bind(stats_label, "label"),
                    )
                ),
            )
        ),
    )


if __name__ == "__main__":
    preview = Preview()

    @preview("TaskWidget")
    def _(_) -> Gtk.Widget:
        sample_task = TaskViewModel("Sample Task")

        return ui(
            listbox := Gtk.ListBox(
                selection_mode=Gtk.SelectionMode.NONE,
                css_classes=["boxed-list"],
                width_request=300,
                margin_bottom=4,
                margin_top=4,
                margin_start=4,
                margin_end=4,
            ),
            listbox.append(
                TaskWidget(sample_task, lambda task: print(f"Would remove: {task.title.value}"))
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
