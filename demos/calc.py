import gi
from typing import Callable, Optional

from reactivegtk import MutableState, Preview, WidgetLifecycle
from reactivegtk.dsl import apply, do, build, unpack_apply

gi.require_versions(
    {
        "Gtk": "4.0",
        "Adw": "1",
        "Pango": "1.0",
        "Gdk": "4.0",
    }
)
from gi.repository import Adw, Gdk, Gtk, Pango  # type: ignore # noqa: E402


class CalculatorViewModel:
    def __init__(self):
        self.current_expression = MutableState("")
        self.result = MutableState("0")
        self.has_error = MutableState(False)
        self.just_evaluated = MutableState(False)

    def append_digit(self, digit: str) -> None:
        if self.has_error.value:
            self.clear()

        if self.just_evaluated.value:
            self.current_expression.set(digit)
            self.just_evaluated.set(False)
        else:
            self.current_expression.update(lambda expr: expr + digit)

    def append_operator(self, operator: str) -> None:
        if self.has_error.value:
            self.clear()

        if self.just_evaluated.value:
            self.just_evaluated.set(False)

        current = self.current_expression.value

        # Allow minus sign at the beginning for negative numbers
        if operator == "-" and not current:
            self.current_expression.update(lambda expr: expr + operator)
        elif current and current[-1] not in "+-*/":
            self.current_expression.update(lambda expr: expr + operator)

    def append_decimal(self) -> None:
        if self.has_error.value:
            self.clear()

        if self.just_evaluated.value:
            self.current_expression.set("0.")
            self.just_evaluated.set(False)
            return

        current = self.current_expression.value

        parts = (
            current.replace("+", "|")
            .replace("-", "|")
            .replace("*", "|")
            .replace("/", "|")
            .split("|")
        )
        if parts and "." not in parts[-1]:
            if not current or current[-1] in "+-*/":
                self.current_expression.update(lambda expr: expr + "0.")
            else:
                self.current_expression.update(lambda expr: expr + ".")

    def clear(self) -> None:
        self.current_expression.set("")
        self.result.set("0")
        self.has_error.set(False)
        self.just_evaluated.set(False)

    def backspace(self) -> None:
        if self.has_error.value:
            self.clear()
            return

        if self.just_evaluated.value:
            self.clear()
            return

        self.current_expression.update(lambda expr: expr[:-1] if expr else "")

    def calculate(self) -> None:
        try:
            expr = self.current_expression.value
            if expr:
                result = eval(expr)
                self.result.set(str(result))
                self.current_expression.set(str(result))
                self.has_error.set(False)
                self.just_evaluated.set(True)
        except Exception:
            self.result.set("Error!")
            self.has_error.set(True)
            self.just_evaluated.set(False)


def ResultsDisplay(view_model: CalculatorViewModel) -> Gtk.WindowHandle:
    return Gtk.WindowHandle(
        child=build(
            Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL,
                spacing=6,
                margin_start=12,
                margin_end=12,
                margin_top=12,
                margin_bottom=6,
            ),
            lambda box: apply(box.append).foreach(
                build(
                    Gtk.Label(
                        label="",
                        halign=Gtk.Align.END,
                        ellipsize=Pango.EllipsizeMode.END,
                    ),
                    lambda expression_label: view_model.current_expression.map(
                        lambda expr: expr or "0"
                    ).bind(expression_label, "label"),
                ),
                build(
                    Gtk.Label(
                        label="0",
                        halign=Gtk.Align.END,
                        css_classes=["title-1"],
                        ellipsize=Pango.EllipsizeMode.END,
                    ),
                    lambda result_label: do(
                        view_model.result.bind(result_label, "label"),
                        view_model.has_error.watch(
                            lambda has_error: (
                                result_label.add_css_class("error")
                                if has_error
                                else result_label.remove_css_class("error")
                            )
                        ),
                    ),
                ),
            ),
        ),
    )


def CalcButton(
    label_or_icon: str,
    on_click: Callable[[], None],
    css_classes: Optional[list[str]] = None,
    width_request: Optional[int] = None,
    icon: bool = False,
) -> Gtk.Button:
    return build(
        Gtk.Button(
            hexpand=True,
            vexpand=True,
            can_focus=False,
        ),
        lambda button: do(
            button.set_icon_name(label_or_icon) if icon else button.set_label(label_or_icon),
            lifecycle := WidgetLifecycle(button),
            *[button.add_css_class(css_class) for css_class in (css_classes or [])],
            button.set_size_request(width_request or -1, -1) if width_request else None,
            lifecycle.subscribe(button, "clicked")(lambda *_: on_click()),
        ),
    )


def Keypad(view_model: CalculatorViewModel) -> Gtk.Grid:
    return build(
        Gtk.Grid(
            row_spacing=6,
            column_spacing=6,
            margin_top=12,
            margin_start=12,
            margin_end=12,
            margin_bottom=12,
            hexpand=True,
            vexpand=True,
        ),
        lambda grid: unpack_apply(grid.attach).foreach(
            # Row 0: Clear and backspace
            (CalcButton("C", view_model.clear, ["destructive-action"]), 0, 0, 3, 1),
            (
                CalcButton("edit-clear-symbolic", view_model.backspace, ["flat"], icon=True),
                3,
                0,
                1,
                1,
            ),
            # Row 1: 7, 8, 9, /
            (CalcButton("7", lambda: view_model.append_digit("7")), 0, 1, 1, 1),
            (CalcButton("8", lambda: view_model.append_digit("8")), 1, 1, 1, 1),
            (CalcButton("9", lambda: view_model.append_digit("9")), 2, 1, 1, 1),
            (
                CalcButton("÷", lambda: view_model.append_operator("/"), ["suggested-action"]),
                3,
                1,
                1,
                1,
            ),
            # Row 2: 4, 5, 6, *
            (CalcButton("4", lambda: view_model.append_digit("4")), 0, 2, 1, 1),
            (CalcButton("5", lambda: view_model.append_digit("5")), 1, 2, 1, 1),
            (CalcButton("6", lambda: view_model.append_digit("6")), 2, 2, 1, 1),
            (
                CalcButton("×", lambda: view_model.append_operator("*"), ["suggested-action"]),
                3,
                2,
                1,
                1,
            ),
            # Row 3: 1, 2, 3, -
            (CalcButton("1", lambda: view_model.append_digit("1")), 0, 3, 1, 1),
            (CalcButton("2", lambda: view_model.append_digit("2")), 1, 3, 1, 1),
            (CalcButton("3", lambda: view_model.append_digit("3")), 2, 3, 1, 1),
            (
                CalcButton("−", lambda: view_model.append_operator("-"), ["suggested-action"]),
                3,
                3,
                1,
                1,
            ),
            # Row 4: 0, ., +
            (CalcButton("0", lambda: view_model.append_digit("0")), 0, 4, 2, 1),
            (CalcButton(".", view_model.append_decimal), 2, 4, 1, 1),
            (
                CalcButton("+", lambda: view_model.append_operator("+"), ["suggested-action"]),
                3,
                4,
                1,
                1,
            ),
            # Row 5: Equals
            (CalcButton("=", view_model.calculate, ["suggested-action"]), 0, 5, 4, 1),
        ),
    )


def CalculatorView(view_model: CalculatorViewModel) -> Gtk.Box:
    return build(
        Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=0,
        ),
        lambda box: apply(box.append).foreach(
            ResultsDisplay(view_model),
            Gtk.Separator(),
            Keypad(view_model),
        ),
    )


def CalculatorWindow() -> Adw.Window:
    view_model = CalculatorViewModel()

    def handle_key_press(controller, keyval, keycode, state) -> bool:
        key_name = Gdk.keyval_name(keyval)

        match key_name:
            # Handle digit keys
            case "0" | "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9":
                view_model.append_digit(key_name)
                return True

            # Handle operators
            case "plus" | "KP_Add":
                view_model.append_operator("+")
                return True
            case "minus" | "KP_Subtract":
                view_model.append_operator("-")
                return True
            case "asterisk" | "KP_Multiply":
                view_model.append_operator("*")
                return True
            case "slash" | "KP_Divide":
                view_model.append_operator("/")
                return True

            # Handle decimal point
            case "period" | "KP_Decimal":
                view_model.append_decimal()
                return True

            # Handle equals/enter
            case "equal" | "Return" | "KP_Enter":
                view_model.calculate()
                return True

            # Handle backspace
            case "BackSpace":
                view_model.backspace()
                return True

            # Handle clear (Escape or Delete)
            case "Escape" | "Delete":
                view_model.clear()
                return True

            # Default case for unhandled keys
            case _:
                return False

    return build(
        Adw.Window(
            title="Calculator",
            default_height=400,
            default_width=300,
            resizable=True,
            can_focus=True,
        ),
        lambda window: do(
            lifecycle := WidgetLifecycle(window),
            window.add_controller(
                do(
                    key_controller := Gtk.EventControllerKey(
                        name="key-controller",
                        propagation_phase=Gtk.PropagationPhase.CAPTURE,
                    ),
                    lifecycle.subscribe(key_controller, "key-pressed")(handle_key_press),
                    ret=key_controller,
                )
            ),
            window.set_content(
                build(
                    Adw.ToolbarView(top_bar_style=Adw.ToolbarStyle.FLAT),
                    lambda toolbar_view: do(
                        toolbar_view.add_top_bar(Adw.HeaderBar()),
                        toolbar_view.set_content(CalculatorView(view_model)),
                    ),
                ),
            ),
        ),
    )


if __name__ == "__main__":
    preview = Preview()

    @preview("ResultsDisplay")
    def _(_) -> Gtk.Widget:
        view_model = CalculatorViewModel()
        view_model.current_expression.set("2+3*4")
        view_model.result.set("14")

        return Gtk.Overlay(
            width_request=300,
            child=ResultsDisplay(view_model),
        )

    @preview("ResultsDisplay with Error")
    def _(_) -> Gtk.Widget:
        view_model = CalculatorViewModel()
        view_model.current_expression.set("2+3*")
        view_model.result.set("Error!")
        view_model.has_error.set(True)

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