# ReactiveGTK

A reactive UI framework for GTK4 applications in Python, inspired by modern reactive programming patterns. Build dynamic, stateful GTK applications with declarative syntax and automatic UI updates.

## Features

- **Reactive State Management**: Automatic UI updates when state changes
- **Declarative UI**: Build UIs with functional, composable components
- **Type Safety**: Full type hints and type checking support
- **Efficient Updates**: Only re-render what actually changed
- **Data Binding**: Two-way binding between state and UI elements
- **GTK4 + Libadwaita**: Modern GTK4 widgets with Adwaita styling
- **Async Support**: Built-in async/await support for effects

## Installation

```bash
# with pip
pip install git+https://https://github.com/Microwave-WYB/reactivegtk.git
```

**Requirements:**
- Python 3.10+
- GTK4
- Libadwaita

## Quick Start: Hello World

Here's a minimal counter app to get you started:

```python
import gi
from reactivegtk import MutableState, WidgetLifecycle, into

gi.require_versions({"Gtk": "4.0", "Adw": "1"})
from gi.repository import Gtk, Adw

def HelloWorld():
    # Create reactive state
    count = MutableState(0)

    # Create container widget
    box = Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL,
        spacing=12,
        halign=Gtk.Align.CENTER,
        valign=Gtk.Align.CENTER
    )

    # Widget lifecycle management
    lifecycle = WidgetLifecycle(box)

    # Add label that automatically updates when count changes
    @into(box.append)
    def _():
        label = Gtk.Label(css_classes=["title-1"])
        count.map(lambda x: f"Count: {x}").bind(label, "label")
        return label

    # Add button that updates the count
    @into(box.append)
    def _():
        button = Gtk.Button(label="Click me!")

        @lifecycle.subscribe(button, "clicked")
        def _(_):
            count.update(lambda x: x + 1)

        return button

    return box

# Create and run the app
def App():
    app = Adw.Application(application_id="com.example.HelloWorld")

    @lambda f: app.connect("activate", f)
    def _(*_):
        window = Adw.ApplicationWindow(application=app, title="Hello ReactiveGTK")
        window.set_content(HelloWorld())
        window.present()

    return app

if __name__ == "__main__":
    App().run([])
```

## Core Concepts

### 1. Reactive State

State in ReactiveGTK is reactive - when it changes, all dependent UI elements automatically update.

```python
from reactivegtk import MutableState, State

# Mutable state that can be changed
count = MutableState(0)
count.set(5)  # Set value
count.update(lambda x: x + 1)  # Update with function

# Derived state that transforms another state
doubled = count.map(lambda x: x * 2)
text = count.map(lambda x: f"Value: {x}")
```

### 2. Data Binding

Bind state directly to widget properties:

```python
# One-way binding: state → widget (works with both State and MutableState)
name = MutableState("World")
label = Gtk.Label()
name.map(lambda x: f"Hello, {x}!").bind(label, "label")

# Two-way binding: state ↔ widget (only works with MutableState)
text_state = MutableState("")
entry = Gtk.Entry()
text_state.twoway_bind(entry, "text")
```

**Note**: Two-way binding (`.twoway_bind()`) only works with `MutableState`, not `State`. This is by design - if you want to expose read-only state in your component's API, you can expose it as `State` to prevent accidental modifications:

```python
class MyComponent:
    def __init__(self):
        self._count = MutableState(0)  # Private mutable state

    @property
    def count(self) -> State[int]:
        return self._count  # Expose as read-only State

    def increment(self):
        self._count.update(lambda x: x + 1)  # Only component can modify
```

### 3. Widget Lifecycle

Manage widget events, cleanup, and effects:

```python
from reactivegtk import WidgetLifecycle

box = Gtk.Box()
lifecycle = WidgetLifecycle(box)

# Subscribe to widget signals
@lifecycle.subscribe(button, "clicked")
def on_click(_):
    print("Button clicked!")

# Watch state changes
@lifecycle.watch(count, init=True)
def on_count_change(new_value):
    print(f"Count changed to: {new_value}")

# Cleanup when widget is destroyed
@lifecycle.on_cleanup()
def cleanup():
    print("Widget destroyed")
```

### 4. Declarative UI with `@into`

The `@into` decorator provides a clean way to build UI hierarchies:

```python
from reactivegtk import into

@into(parent.append)
def _():
    child = Gtk.Button(label="Child")
    # ... configure child ...
    return child
```

### 5. Sequence Binding

Automatically manage lists of widgets that sync with collections:

```python
from reactivegtk import bind_sequence

items = MutableState(["Apple", "Banana", "Cherry"])
listbox = Gtk.ListBox()

@bind_sequence(listbox, items)
def create_item(item: str) -> Gtk.Widget:
    return Gtk.Label(label=item)

# Adding/removing items from the state automatically updates the UI
items.update(lambda lst: lst + ["Date"])  # Adds new widget
```

### 6. Async Effects

Run async operations that respond to state changes:

```python
import asyncio
from reactivegtk import start_event_loop

# Start async event loop
event_loop, thread = start_event_loop()

@lifecycle.watch(auto_increment, init=True)
@lifecycle.effect(event_loop)
async def auto_counter():
    while auto_increment.value:
        await asyncio.sleep(1)
        count.update(lambda x: x + 1)
```

## Advanced Example: Todo App

```python
from dataclasses import dataclass, field
from collections.abc import Sequence
from reactivegtk import MutableState, State, WidgetLifecycle, into

@dataclass(frozen=True)
class Task:
    title: MutableState[str]
    done: MutableState[bool] = field(default_factory=lambda: MutableState(False))

class TodoApp:
    def __init__(self):
        self.tasks = MutableState[Sequence[Task]]([])
        self.new_task_text = MutableState("")

    def add_task(self, text: str):
        if text.strip():
            task = Task(MutableState(text.strip()))
            self.tasks.update(lambda tasks: [*tasks, task])
            self.new_task_text.set("")

    def remove_task(self, task: Task):
        self.tasks.update(lambda tasks: [t for t in tasks if t is not task])

def TodoView(app: TodoApp) -> Gtk.Widget:
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    lifecycle = WidgetLifecycle(box)

    # Add task entry
    @into(box.append)
    def _():
        entry = Gtk.Entry(placeholder_text="Add a task...")
        app.new_task_text.twoway_bind(entry, "text")

        @lifecycle.subscribe(entry, "activate")
        def _(_):
            app.add_task(app.new_task_text.value)

        return entry

    # Task list
    @into(box.append)
    def _():
        listbox = Gtk.ListBox()

        @bind_sequence(listbox, app.tasks)
        def create_task_widget(task: Task) -> Gtk.Widget:
            row = Gtk.ListBoxRow()
            task_box = Gtk.Box(spacing=12)
            row.set_child(task_box)

            # Checkbox
            checkbox = Gtk.CheckButton()
            task.done.twoway_bind(checkbox, "active")
            task_box.append(checkbox)

            # Label
            label = Gtk.Label()
            task.title.bind(label, "label")
            task_box.append(label)

            # Remove button
            remove_btn = Gtk.Button(icon_name="user-trash-symbolic")
            task_lifecycle = WidgetLifecycle(row)

            @task_lifecycle.subscribe(remove_btn, "clicked")
            def _(_):
                app.remove_task(task)

            task_box.append(remove_btn)
            return row

        return listbox

    return box
```

## Preview System

ReactiveGTK includes a built-in preview system for rapid prototyping:

```python
from reactivegtk import Preview

preview = Preview()

@preview("Counter")
def _(_) -> Gtk.Widget:
    return Counter()

@preview("TodoApp")
def _(_) -> Gtk.Widget:
    return TodoView(TodoApp())

preview.run()  # Shows preview window with component selector
```

## API Reference

### State Classes

- **`State[T]`**: Immutable reactive state
- **`MutableState[T]`**: Mutable reactive state with `.set()` and `.update()` methods

### State Methods

- **`.map(fn)`**: Transform state value
- **`.bind(widget, property)`**: One-way binding to widget property
- **`.twoway_bind(widget, property)`**: Two-way binding with widget property
- **`.watch(callback)`**: Subscribe to state changes

### Lifecycle Management

- **`WidgetLifecycle(widget)`**: Manages widget lifecycle
- **`.subscribe(widget, signal)`**: Subscribe to widget signals
- **`.watch(state)`**: Watch state changes
- **`.effect(event_loop)`**: Run async effects
- **`.on_cleanup()`**: Register cleanup callbacks

### Utilities

- **`@into(method)`**: Declarative UI builder decorator
- **`bind_sequence(container, state, key_fn?)`**: Bind collections to UI
- **`start_event_loop()`**: Start async event loop for effects

## Examples

Check out the `demos/` directory for complete examples:

- **[`counter.py`](demos/counter.py)**: Simple counter with increment/decrement
- **[`calc.py`](demos/calc.py)**: Calculator with complex state management
- **[`todo.py`](demos/todo.py)**: Todo app with dynamic lists
- **[`multi_counter.py`](demos/multi_counter.py)**: Multiple counters with async auto-increment

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

## License

This project is under [MIT License](LICENSE)

## Requirements

- Python ≥ 3.10
- PyGObject ≥ 3.52.3
- GTK4
- Libadwaita
