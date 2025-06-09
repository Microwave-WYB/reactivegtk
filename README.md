# ReactiveGTK

> [!WARNING]
> This project is in very early development stage and is not ready for production use.
> Breaking changes should be expected at any time. APIs, architecture, and core concepts
> may change significantly without notice. Use at your own risk.

A reactive UI framework for GTK4 applications in Python, inspired by modern reactive programming patterns. Build dynamic, stateful GTK applications with declarative syntax and automatic UI updates.

## Features

- 🔄 **Reactive State Management**: Automatic UI updates when state changes
- 🔗 **Two-way Data Binding**: Keep UI and state in sync effortlessly
- 📝 **Declarative Syntax**: Build UIs using a clean, intuitive DSL
- 🧬 **Component Lifecycle**: Automatic memory management and cleanup
- 🔌 **Type Safety**: Full type hints support
- 🎯 **Zero Dependencies**: Only GTK4 and Python 3.10+

## Installation

```bash
pip install reactive-gtk
```

## Two Approaches to GTK UI Development

> [!NOTE]
> The DSL Pattern (Approach 2) is the recommended and modern way to build ReactiveGTK applications.
> The traditional approach is shown for comparison only.

### 1. Traditional GTK (Object-Oriented, Imperative)

> [!CAUTION]
> This approach is shown for historical context only. Use the DSL Pattern for new applications.

Classic GTK widget development with manual state management:

```python
import gi
gi.require_versions({"Gtk": "4.0", "Adw": "1"})
from gi.repository import Adw, Gtk

class HelloWorldWidget(Gtk.Box):
    def __init__(self):
        super().__init__(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER,
        )

        self.name = ""

        # WARNING: Circular reference memory leak!
        # HelloWorldWidget → self.entry → signal connection → self._on_entry_* → HelloWorldWidget
        # This widget will never be garbage collected without manual cleanup
        self.entry = Gtk.Entry(placeholder_text="Enter your name...", width_request=200)
        self.entry.connect("activate", self._on_entry_activate)
        self.entry.connect("changed", self._on_entry_changed)
        self.append(self.entry)

        self.label = Gtk.Label(css_classes=["title-1"])
        self._update_label()
        self.append(self.label)

    def _on_entry_activate(self, entry: Gtk.Entry) -> None:
        print(f"Entry activated with text: {self.name}")

    def _on_entry_changed(self, entry: Gtk.Entry) -> None:
        self.name = entry.get_text()
        self._update_label()

    def _update_label(self) -> None:
        text = f"Hello, {self.name}!" if self.name else "Hello, ...!"
        self.label.set_text(text)
```

**Problems with Traditional Approach:**
- ❌ **Memory leaks** from circular references
- ❌ **Manual state synchronization** between widgets
- ❌ **Boilerplate code** for signal connections and cleanup
- ❌ **Error-prone** lifecycle management
- ❌ **Imperative** - you must tell GTK exactly what to do

### 2. DSL Pattern (Declarative)

The recommended way to build ReactiveGTK applications. This pattern provides a clean, declarative syntax that makes UI construction intuitive and maintainable:

```python
import gi
from reactivegtk import MutableState, WidgetLifecycle
from reactivegtk.dsl import ui, apply

gi.require_versions({"Gtk": "4.0", "Adw": "1"})
from gi.repository import Gtk, Adw

def HelloWorld():
    # Create reactive state
    name = MutableState("")

    return ui(
        box := Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER,
        ),
        lifecycle := WidgetLifecycle(box),
        apply(box.append).foreach(
            ui(
                entry := Gtk.Entry(placeholder_text="Enter your name...", width_request=200),
                name.twoway_bind(entry, "text"),
                lifecycle.subscribe(entry, "activate")(
                    lambda *_: print(f"Entry activated with text: {name.value}")
                ),
            ),
            ui(
                label := Gtk.Label(css_classes=["title-1"]),
                name.map(lambda x: f"Hello, {x}!" if x else "Hello, ...!").bind(label, "label"),
            ),
        ),
    )
```

**Benefits of DSL Pattern:**
- ✅ **Declarative syntax** - describe what you want, not how to do it
- ✅ **Automatic lifecycle management** - no memory leaks
- ✅ **Reactive state** - UI updates automatically
- ✅ **Two-way data binding** - no manual synchronization
- ✅ **Composable components** - build complex UIs from simple pieces
- ✅ **Type-safe** - catch errors at compile time

### App Setup

The basic application setup is the same for both approaches:

```python
import gi
gi.require_versions({"Gtk": "4.0", "Adw": "1"})
from gi.repository import Gtk, Adw

class App(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.example.HelloWorld")
        self.connect("activate", self._on_activate)

    def _on_activate(self, app):
        window = Adw.ApplicationWindow(application=app)
        window.set_content(HelloWorld())  # Use either approach here
        window.present()

app = App()
app.run(None)
```

For more complex applications with routing and multiple windows:

```python
from reactivegtk import Router

def App():
    router = Router()

    @router.route("/")
    def home():
        return HelloWorld()

    @router.route("/about")
    def about():
        return AboutView()

    @router.route("/settings")
    def settings():
        return SettingsView()

    return router

app = Adw.Application(application_id="com.example.HelloWorld")
app.connect("activate", lambda app: App().run(app))
app.run(None)
```

## Why ReactiveGTK?

GTK is a powerful toolkit for building native Linux applications, but its traditional object-oriented, imperative approach can lead to complex, hard-to-maintain code. ReactiveGTK brings modern reactive programming patterns to GTK development, making it easier to:

- Build complex, stateful UIs without getting lost in callback hell
- Keep UI and state in sync without manual event handling
- Avoid common memory leaks and lifecycle issues
- Write more maintainable, testable code
- Create reusable, composable components

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

Manage widget events, cleanup, and effects while preventing memory leaks:

```python
from reactivegtk import WidgetLifecycle

box = Gtk.Box()
lifecycle = WidgetLifecycle(box)

# Subscribe to widget signals
@lifecycle.subscribe(button, "clicked")
def on_click(*_):
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

**Key Benefit**: `WidgetLifecycle` automatically manages signal connections using weak references, preventing the circular reference memory leaks common in traditional GTK development.

### 4. Declarative UI

ReactiveGTK provides a declarative Domain-Specific Language (DSL) for building UIs. This allows you to describe your interface structure in a clear, hierarchical manner:

```python
from reactivegtk.dsl import ui, apply

def MyApp():
    count = MutableState(0)

    return ui(
        box := Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12
        ),
        lifecycle := WidgetLifecycle(box),
        apply(box.append).foreach(
            ui(
                label := Gtk.Label(),
                count.map(lambda x: f"Count: {x}").bind(label, "label")
            ),
            ui(
                button := Gtk.Button(label="Increment"),
                lifecycle.subscribe(button, "clicked")(
                    lambda *_: count.update(lambda x: x + 1)
                )
            )
        )
    )
```

The DSL approach:
- ✅ Eliminates boilerplate code
- ✅ Makes the UI structure immediately apparent
- ✅ Uses Python's standard syntax in a natural way
- ✅ Provides automatic lifecycle management
- ✅ Enables composable and reusable components

### 5. Sequence Binding

Bind lists and sequences to automatically update the UI when items are added or removed:

```python
from reactivegtk import MutableSequence, State

items = MutableSequence[str]([])
items.append("New Item")  # UI automatically updates

def create_item(text: str):
    return ui(
        Gtk.Label(label=text)
    )

items.map(create_item).bind_foreach(box)
```

### 6. Async Effects

Handle asynchronous operations with reactive effects:

```python
import asyncio
from reactivegtk import async_effect

@async_effect
async def auto_counter(set_count):
    while True:
        await asyncio.sleep(1)
        set_count(lambda x: x + 1)
```

## Advanced Example: Counter

A complete counter application demonstrating reactive state, events, and async effects:

## Preview System

ReactiveGTK includes a hot-reload preview system for rapid development:

```python
@preview
def counter_preview():
    return Counter()
```

Run the preview server:

```bash
python -m reactivegtk.preview examples/counter.py
```

## API Reference

### State Classes

- `State[T]`: Base class for all reactive state
- `MutableState[T]`: Mutable reactive state that can be changed
- `DerivedState[T]`: Read-only state derived from other state
- `MutableSequence[T]`: Reactive list that can be modified

### State Methods

- `state.value`: Get current value
- `state.set(value)`: Set new value (MutableState only)
- `state.update(fn)`: Update value with function (MutableState only)
- `state.map(fn)`: Create derived state
- `state.bind(widget, prop)`: One-way binding to widget property
- `state.twoway_bind(widget, prop)`: Two-way binding (MutableState only)

### Lifecycle Management

- `WidgetLifecycle`: Manages widget lifecycle and cleanup
- `lifecycle.subscribe(widget, signal)`: Subscribe to widget signals
- `lifecycle.watch(state)`: Watch state changes
- `lifecycle.on_cleanup()`: Register cleanup functions
- `lifecycle.dispose()`: Manual cleanup

### Utilities

- `async_effect`: Create async effects
- `derived`: Create derived state
- `untracked`: Access state without tracking

### DSL (Domain Specific Language)

- `ui`: Create UI components
- `apply`: Apply functions to widgets
- `foreach`: Create multiple widgets
- `once`: Apply one-time setup

Example counter component using all major features:

```python
def Counter():
    count = MutableState(0)
    doubled = count.map(lambda x: x * 2)

    return ui(
        box := Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
            margin_start=12,
            margin_end=12,
            margin_top=12,
            margin_bottom=12,
        ),
        lifecycle := WidgetLifecycle(box),

        # Auto-increment effect
        async_effect(lambda: auto_counter(count.set)),

        apply(box.append).foreach(
            # Counter display
            ui(
                label := Gtk.Label(css_classes=["title-1"]),
                count.map(lambda x: f"Count: {x}").bind(label, "label"),
            ),

            # Doubled value
            ui(
                label2 := Gtk.Label(),
                doubled.map(lambda x: f"Doubled: {x}").bind(label2, "label"),
            ),

            # Control buttons
            ui(
                buttons := Gtk.Box(
                    orientation=Gtk.Orientation.HORIZONTAL,
                    spacing=6,
                    halign=Gtk.Align.CENTER,
                ),
                apply(buttons.append).foreach(
                    ui(
                        button := Gtk.Button(label="Increment"),
                        lifecycle.subscribe(button, "clicked")(
                            lambda *_: count.update(lambda x: x + 1)
                        ),
                    ),
                    ui(
                        button2 := Gtk.Button(label="Reset"),
                        lifecycle.subscribe(button2, "clicked")(
                            lambda *_: count.set(0)
                        ),
                    ),
                ),
            ),
        ),
    )
```

## Examples

Check out the `demos` directory for more complete examples:

- Hello World (`demos/hello.py`)
- Counter (`demos/counter.py`)
- To-Do List (`demos/todo.py`)
- Multiple Auto-incrementing Counters (`demos/multi_counter.py`)

## Contributing

Contributions are welcome! Please read our contributing guidelines before submitting pull requests.

## License

MIT License - see LICENSE for details

## Requirements

- Python 3.10+
- GTK 4.0+
- PyGObject
