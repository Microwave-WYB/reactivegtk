from dataclasses import dataclass, replace
from enum import Enum, auto
from typing import Callable, Final, Literal, Optional

import gi

from reactivegtk import MutableState, Preview, apply, State

gi.require_versions(
    {
        "Gtk": "4.0",
        "Adw": "1",
        "Pango": "1.0",
        "Gdk": "4.0",
    }
)
from gi.repository import Adw, Gdk, Gtk, Pango  # type: ignore # noqa: E402


@dataclass(frozen=True)
class Digit:
    value: int


@dataclass(frozen=True)
class Operator:
    symbol: Literal["+", "-", "*", "/"]


class Control(Enum):
    CLEAR = auto()
    BACKSPACE = auto()
    EVAL = auto()
    DECIMAL = auto()


CalculatorAction = Digit | Operator | Control

ERROR: Final[str] = "Error!"


@dataclass(frozen=True)
class CalculatorState:
    current_expression: str = "0"
    result: str = "0"
    error: bool = False

    def sync_result(self) -> "CalculatorState":
        try:
            result = eval(self.current_expression)
            return replace(self, result=str(result), error=False)
        except Exception:
            return self

    def update(self, action: CalculatorAction) -> "CalculatorState":
        match action:
            case Digit(value):
                match self.current_expression:
                    case "0":
                        new_expression = str(value)
                    case _:
                        new_expression = self.current_expression + str(value)
                return replace(self, current_expression=new_expression).sync_result()

            case Operator(symbol):
                match symbol:
                    case "-":
                        if self.current_expression == "0":
                            return replace(self, current_expression="-")
                        return replace(self, current_expression=self.current_expression + symbol)
                    case _:
                        return replace(self, current_expression=self.current_expression + symbol)

            case Control.CLEAR:
                return CalculatorState()

            case Control.BACKSPACE:
                return replace(
                    self,
                    current_expression=self.current_expression[:-1] if self.current_expression else "",
                ).sync_result()

            case Control.DECIMAL:
                match self.current_expression[-1]:
                    case ".":
                        return self
                    case operator if not operator.isdigit():
                        return replace(self, current_expression=self.current_expression + "0.")
                    case _:
                        return replace(self, current_expression=self.current_expression + ".")

            case Control.EVAL:
                try:
                    result = eval(self.current_expression)
                    return replace(self, current_expression=str(result), result=str(result), error=False)
                except Exception:
                    return replace(self, current_expression=self.current_expression, result=ERROR, error=True)


class CalculatorViewModel:
    def __init__(self):
        self._state = MutableState(CalculatorState())

    @property
    def state(self) -> State[CalculatorState]:
        return self._state

    def enter(self, action: CalculatorAction) -> None:
        """Perform an action on the calculator state."""
        self._state.update(lambda state: state.update(action))


def ResultsDisplay(view_model: CalculatorViewModel) -> Gtk.WindowHandle:
    window_handle = Gtk.WindowHandle()

    @apply(window_handle.set_child)
    def _():
        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6,
            margin_start=12,
            margin_end=12,
            margin_top=12,
            margin_bottom=6,
        )

        @apply(box.append)
        def _():
            expression_label = Gtk.Label(
                label="",
                halign=Gtk.Align.END,
                ellipsize=Pango.EllipsizeMode.END,
            )
            view_model.state.map(lambda state: state.current_expression).bind(expression_label, "label")
            return expression_label

        @apply(box.append)
        def _():
            result_label = Gtk.Label(
                label="0",
                halign=Gtk.Align.END,
                css_classes=["title-1"],
                ellipsize=Pango.EllipsizeMode.END,
            )
            # view_model.result.bind(result_label, "label")
            view_model.state.map(lambda state: state.result).bind(result_label, "label")

            @view_model.state.map(lambda state: state.error).watch
            def _(has_error):
                if has_error:
                    result_label.add_css_class("error")
                else:
                    result_label.remove_css_class("error")

            return result_label

        return box

    return window_handle


def CalcButton(
    label_or_icon: str,
    on_click: Callable[[], None],
    css_classes: Optional[list[str]] = None,
    width_request: Optional[int] = None,
    icon: bool = False,
) -> Gtk.Button:
    button = Gtk.Button(
        hexpand=True,
        vexpand=True,
        can_focus=False,
    )

    if icon:
        button.set_icon_name(label_or_icon)
    else:
        button.set_label(label_or_icon)

    for css_class in css_classes or []:
        button.add_css_class(css_class)

    if width_request:
        button.set_size_request(width_request, -1)

    button.connect("clicked", lambda *_: on_click())

    return button


def Keypad(view_model: CalculatorViewModel) -> Gtk.Grid:
    grid = Gtk.Grid(
        row_spacing=6,
        column_spacing=6,
        margin_top=12,
        margin_start=12,
        margin_end=12,
        margin_bottom=12,
        hexpand=True,
        vexpand=True,
    )

    @apply.unpack(grid.attach).foreach
    def _():
        return (
            # Row 0: Clear and backspace
            (CalcButton("C", lambda: view_model.enter(Control.CLEAR), ["destructive-action"]), 0, 0, 3, 1),
            (
                CalcButton("edit-clear-symbolic", lambda: view_model.enter(Control.BACKSPACE), ["flat"], icon=True),
                3,
                0,
                1,
                1,
            ),
            # Row 1: 7, 8, 9, /
            (CalcButton("7", lambda: view_model.enter(Digit(7))), 0, 1, 1, 1),
            (CalcButton("8", lambda: view_model.enter(Digit(8))), 1, 1, 1, 1),
            (CalcButton("9", lambda: view_model.enter(Digit(9))), 2, 1, 1, 1),
            (
                CalcButton("÷", lambda: view_model.enter(Operator("/")), ["suggested-action"]),
                3,
                1,
                1,
                1,
            ),
            # Row 2: 4, 5, 6, *
            (CalcButton("4", lambda: view_model.enter(Digit(4))), 0, 2, 1, 1),
            (CalcButton("5", lambda: view_model.enter(Digit(5))), 1, 2, 1, 1),
            (CalcButton("6", lambda: view_model.enter(Digit(6))), 2, 2, 1, 1),
            (
                CalcButton("×", lambda: view_model.enter(Operator("*")), ["suggested-action"]),
                3,
                2,
                1,
                1,
            ),
            # Row 3: 1, 2, 3, -
            (CalcButton("1", lambda: view_model.enter(Digit(1))), 0, 3, 1, 1),
            (CalcButton("2", lambda: view_model.enter(Digit(2))), 1, 3, 1, 1),
            (CalcButton("3", lambda: view_model.enter(Digit(3))), 2, 3, 1, 1),
            (
                CalcButton("−", lambda: view_model.enter(Operator("-")), ["suggested-action"]),
                3,
                3,
                1,
                1,
            ),
            # Row 4: 0, ., +
            (CalcButton("0", lambda: view_model.enter(Digit(0))), 0, 4, 2, 1),
            (CalcButton(".", lambda: view_model.enter(Control.DECIMAL)), 2, 4, 1, 1),
            (
                CalcButton("+", lambda: view_model.enter(Operator("+")), ["suggested-action"]),
                3,
                4,
                1,
                1,
            ),
            # Row 5: Equals
            (CalcButton("=", lambda: view_model.enter(Control.EVAL), ["suggested-action"]), 0, 5, 4, 1),
        )

    return grid


def CalculatorView(view_model: CalculatorViewModel) -> Gtk.Box:
    box = Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL,
        spacing=0,
    )

    @apply(box.append)
    def _():
        return ResultsDisplay(view_model)

    @apply(box.append)
    def _():
        return Gtk.Separator()

    @apply(box.append)
    def _():
        return Keypad(view_model)

    return box


def CalculatorWindow() -> Adw.Window:
    view_model = CalculatorViewModel()

    def handle_key_press(controller, keyval, keycode, state) -> bool:
        key_name = Gdk.keyval_name(keyval)

        match key_name:
            # Handle digit keys
            case "0":
                view_model.enter(Digit(0))
                return True
            case "1":
                view_model.enter(Digit(1))
                return True
            case "2":
                view_model.enter(Digit(2))
                return True
            case "3":
                view_model.enter(Digit(3))
                return True
            case "4":
                view_model.enter(Digit(4))
                return True
            case "5":
                view_model.enter(Digit(5))
                return True
            case "6":
                view_model.enter(Digit(6))
                return True
            case "7":
                view_model.enter(Digit(7))
                return True
            case "8":
                view_model.enter(Digit(8))
                return True
            case "9":
                view_model.enter(Digit(9))
                return True

            # Handle operators
            case "plus" | "KP_Add":
                view_model.enter(Operator("+"))
                return True
            case "minus" | "KP_Subtract":
                view_model.enter(Operator("-"))
                return True
            case "asterisk" | "KP_Multiply":
                view_model.enter(Operator("*"))
                return True
            case "slash" | "KP_Divide":
                view_model.enter(Operator("/"))
                return True

            # Handle decimal point
            case "period" | "KP_Decimal":
                view_model.enter(Control.DECIMAL)
                return True

            # Handle equals/enter
            case "equal" | "Return" | "KP_Enter":
                view_model.enter(Control.EVAL)
                return True

            # Handle backspace
            case "BackSpace":
                view_model.enter(Control.BACKSPACE)
                return True

            # Handle clear (Escape or Delete)
            case "Escape" | "Delete":
                view_model.enter(Control.CLEAR)
                return True

            # Default case for unhandled keys
            case _:
                return False

    window = Adw.Window(
        title="Calculator",
        default_height=400,
        default_width=300,
        resizable=True,
        can_focus=True,
    )

    key_controller = Gtk.EventControllerKey(
        name="key-controller",
        propagation_phase=Gtk.PropagationPhase.CAPTURE,
    )
    key_controller.connect("key-pressed", handle_key_press)
    window.add_controller(key_controller)

    @apply(window.set_content)
    def _():
        toolbar_view = Adw.ToolbarView(top_bar_style=Adw.ToolbarStyle.FLAT)

        @apply(toolbar_view.add_top_bar)
        def _():
            return Adw.HeaderBar()

        @apply(toolbar_view.set_content)
        def _():
            return CalculatorView(view_model)

        return toolbar_view

    return window


if __name__ == "__main__":
    preview = Preview()

    @preview("ResultsDisplay")
    def _(_) -> Gtk.Widget:
        view_model = CalculatorViewModel()
        view_model._state.set(CalculatorState(current_expression="2+3*4", result="14", error=False))

        return Gtk.Overlay(
            width_request=300,
            child=ResultsDisplay(view_model),
        )

    @preview("ResultsDisplay with Error")
    def _(_) -> Gtk.Widget:
        view_model = CalculatorViewModel()
        view_model._state.set(CalculatorState(current_expression="2+3*", result="Error!", error=True))

        return Gtk.Overlay(
            width_request=300,
            child=ResultsDisplay(view_model),
        )

    @preview("Keypad")
    def _(_) -> Gtk.Widget:
        view_model = CalculatorViewModel()

        return Gtk.Overlay(
            width_request=300,
            height_request=300,
            child=Keypad(view_model),
        )

    @preview("CalculatorView")
    def _(_) -> Gtk.Widget:
        view_model = CalculatorViewModel()

        return Gtk.Overlay(
            width_request=300,
            height_request=400,
            child=CalculatorView(view_model),
        )

    @preview("CalculatorWindow")
    def _(_) -> Adw.Window:
        return CalculatorWindow()

    preview.run()
