import gi
from reactivegtk import (
    MutableState,
    into,
    Preview,
    WidgetLifecycle,
)


gi.require_versions(
    {
        "Gtk": "4.0",
        "Adw": "1",
        "Pango": "1.0",
    }
)
from gi.repository import Gtk, Adw, Pango  # type: ignore # noqa: E402


class CalculatorViewModel:
    def __init__(self):
        self.current_expression = MutableState("")
        self.result = MutableState("0")
        self.has_error = MutableState(False)
        self.just_evaluated = MutableState(False)

    def append_digit(self, digit: str) -> None:
        if self.has_error.value:
            self.clear()

        # If we just evaluated, start fresh with new number
        if self.just_evaluated.value:
            self.current_expression.set(digit)
            self.just_evaluated.set(False)
            # Don't update result when starting new number
        else:
            self.current_expression.update(lambda expr: expr + digit)
            self._update_result()

    def append_operator(self, operator: str) -> None:
        if self.has_error.value:
            self.clear()

        # If we just evaluated, continue with the result
        if self.just_evaluated.value:
            self.just_evaluated.set(False)

        current = self.current_expression.value
        if current and current[-1] not in "+-*/":
            self.current_expression.update(lambda expr: expr + operator)
            self._update_result()

    def append_decimal(self) -> None:
        if self.has_error.value:
            self.clear()

        # If we just evaluated, start fresh with "0."
        if self.just_evaluated.value:
            self.current_expression.set("0.")
            self.just_evaluated.set(False)
            # Don't update result when starting new number
            return

        current = self.current_expression.value
        # Check if current number already has a decimal
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
            self._update_result()

    def clear(self) -> None:
        self.current_expression.set("")
        self.result.set("0")
        self.has_error.set(False)
        self.just_evaluated.set(False)

    def backspace(self) -> None:
        if self.has_error.value:
            self.clear()
            return

        # If we just evaluated, clear everything
        if self.just_evaluated.value:
            self.clear()
            return

        self.current_expression.update(lambda expr: expr[:-1] if expr else "")
        self._update_result()

    def calculate(self) -> None:
        try:
            expr = self.current_expression.value
            if expr:
                # Simple evaluation - in a real app you'd want a proper parser
                result = eval(expr)
                self.result.set(str(result))
                self.current_expression.set(str(result))
                self.has_error.set(False)
                self.just_evaluated.set(True)
        except Exception:
            self.result.set("Error!")
            self.has_error.set(True)
            self.just_evaluated.set(False)

    def _update_result(self) -> None:
        try:
            expr = self.current_expression.value
            if expr and not expr.endswith(tuple("+-*/")):
                # Only update result if expression contains operators
                if any(op in expr for op in "+-*/"):
                    result = eval(expr)
                    self.result.set(str(result))
                    self.has_error.set(False)
            elif not expr:
                self.result.set("0")
                self.has_error.set(False)
        except Exception:
            pass


def ResultsDisplay(view_model: CalculatorViewModel) -> Gtk.Widget:
    box = Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL,
        spacing=6,
        margin_start=12,
        margin_end=12,
        margin_top=12,
        margin_bottom=6,
    )

    @into(box.append)
    def _():
        expression_label = Gtk.Label(
            label="",
            halign=Gtk.Align.END,
            css_classes=["caption"],
            ellipsize=Pango.EllipsizeMode.END,
        )
        view_model.current_expression.map(lambda expr: expr or "0").bind(expression_label, "label")
        return expression_label

    @into(box.append)
    def _():
        result_label = Gtk.Label(
            label="0",
            halign=Gtk.Align.END,
            css_classes=["title-1"],
            ellipsize=Pango.EllipsizeMode.END,
        )
        view_model.result.bind(result_label, "label")

        # Change color on error
        def update_style(has_error: bool):
            if has_error:
                result_label.add_css_class("error")
            else:
                result_label.remove_css_class("error")

        view_model.has_error.watch(update_style)
        return result_label

    return box


def CalcButton(
    text: str, on_click, css_classes=None, width_request=None, icon_name=None
) -> Gtk.Button:
    if icon_name:
        button = Gtk.Button(
            icon_name=icon_name,
            hexpand=True,
            vexpand=True,
        )
    else:
        button = Gtk.Button(
            label=text,
            hexpand=True,
            vexpand=True,
        )

    if css_classes:
        for css_class in css_classes:
            button.add_css_class(css_class)

    if width_request:
        button.set_size_request(width_request, -1)

    lifecycle = WidgetLifecycle(button)

    @lifecycle.subscribe(button, "clicked")
    def _(_):
        on_click()

    return button


def Keypad(view_model: CalculatorViewModel) -> Gtk.Widget:
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

    # Row 0: Clear and backspace
    grid.attach(CalcButton("C", view_model.clear, ["destructive-action"]), 0, 0, 3, 1)
    grid.attach(
        CalcButton("", view_model.backspace, ["flat"], icon_name="edit-clear-symbolic"), 3, 0, 1, 1
    )

    # Row 1: 7, 8, 9, /
    grid.attach(CalcButton("7", lambda: view_model.append_digit("7")), 0, 1, 1, 1)
    grid.attach(CalcButton("8", lambda: view_model.append_digit("8")), 1, 1, 1, 1)
    grid.attach(CalcButton("9", lambda: view_model.append_digit("9")), 2, 1, 1, 1)
    grid.attach(
        CalcButton("÷", lambda: view_model.append_operator("/"), ["suggested-action"]), 3, 1, 1, 1
    )

    # Row 2: 4, 5, 6, *
    grid.attach(CalcButton("4", lambda: view_model.append_digit("4")), 0, 2, 1, 1)
    grid.attach(CalcButton("5", lambda: view_model.append_digit("5")), 1, 2, 1, 1)
    grid.attach(CalcButton("6", lambda: view_model.append_digit("6")), 2, 2, 1, 1)
    grid.attach(
        CalcButton("×", lambda: view_model.append_operator("*"), ["suggested-action"]), 3, 2, 1, 1
    )

    # Row 3: 1, 2, 3, -
    grid.attach(CalcButton("1", lambda: view_model.append_digit("1")), 0, 3, 1, 1)
    grid.attach(CalcButton("2", lambda: view_model.append_digit("2")), 1, 3, 1, 1)
    grid.attach(CalcButton("3", lambda: view_model.append_digit("3")), 2, 3, 1, 1)
    grid.attach(
        CalcButton("−", lambda: view_model.append_operator("-"), ["suggested-action"]), 3, 3, 1, 1
    )

    # Row 4: 0, ., =, +
    grid.attach(CalcButton("0", lambda: view_model.append_digit("0")), 0, 4, 2, 1)
    grid.attach(CalcButton(".", view_model.append_decimal), 2, 4, 1, 1)
    grid.attach(
        CalcButton("+", lambda: view_model.append_operator("+"), ["suggested-action"]), 3, 4, 1, 1
    )

    # Row 5: Equals
    grid.attach(CalcButton("=", view_model.calculate, ["suggested-action"]), 0, 5, 4, 1)

    return grid


def CalculatorView(view_model: CalculatorViewModel) -> Gtk.Widget:
    box = Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL,
        spacing=0,
    )

    @into(box.append)
    def _():
        return ResultsDisplay(view_model)

    @into(box.append)
    def _():
        return Gtk.Separator()

    @into(box.append)
    def _():
        return Keypad(view_model)

    return box


def CalculatorWindow() -> Adw.Window:
    window = Adw.Window(title="Calculator")
    window.set_default_size(300, 400)
    window.set_resizable(False)

    toolbar_view = Adw.ToolbarView(top_bar_style=Adw.ToolbarStyle.FLAT)
    toolbar_view.add_top_bar(Adw.HeaderBar())

    view_model = CalculatorViewModel()
    toolbar_view.set_content(CalculatorView(view_model))

    window.set_content(toolbar_view)
    return window


if __name__ == "__main__":
    preview = Preview()

    @preview("ResultsDisplay")
    def _(_) -> Gtk.Widget:
        view_model = CalculatorViewModel()
        view_model.current_expression.set("2+3*4")
        view_model.result.set("14")

        overlay = Gtk.Overlay(width_request=300)
        overlay.set_child(ResultsDisplay(view_model))
        return overlay

    @preview("Keypad")
    def _(_) -> Gtk.Widget:
        view_model = CalculatorViewModel()

        overlay = Gtk.Overlay(width_request=300, height_request=300)
        overlay.set_child(Keypad(view_model))
        return overlay

    @preview("CalculatorView")
    def _(_) -> Gtk.Widget:
        view_model = CalculatorViewModel()

        overlay = Gtk.Overlay(width_request=300, height_request=400)
        overlay.set_child(CalculatorView(view_model))
        return overlay

    @preview("CalculatorWindow")
    def _(_) -> Adw.Window:
        return CalculatorWindow()

    preview.run()
