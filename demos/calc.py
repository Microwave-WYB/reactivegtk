from typing import Sequence
import gi
from reactivegtk import (
    State,
    WidgetLifecycle,
    bind_sequence,
    into,
    Preview,
)


gi.require_versions(
    {
        "Gtk": "4.0",
        "Adw": "1",
    }
)
from gi.repository import Gtk, Adw  # type: ignore # noqa: E402


def ResultDisplay(results: State[Sequence[str]]) -> Gtk.Widget:
    listbox = Gtk.ListBox(
        selection_mode=Gtk.SelectionMode.NONE,
        css_classes=["boxed-list"],
    )

    @bind_sequence(listbox, results)
    def _(text: str):
        return Adw.ActionRow(title=text)

    return listbox


def LiveDisplay(text: State[str]) -> Gtk.Widget:
    box = Gtk.Frame(
        valign=Gtk.Align.CENTER,
        halign=Gtk.Align.CENTER,
        css_classes=["card"],
        width_request=300,
        height_request=100,
    )

    @into(box.set_child)
    def _():
        label = Gtk.Label(css_classes=["title-1"])
        text.bind(label, "label")

        return label

    return box


def InputGrid() -> Gtk.Widget:
    grid = Gtk.Grid(
        column_spacing=6,
        row_spacing=6,
        margin_top=12,
        margin_bottom=12,
        margin_start=12,
        margin_end=12,
    )

    return grid


def Calculator() -> Gtk.Widget:
    mainbox = Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL,
        spacing=6,
        valign=Gtk.Align.CENTER,
        halign=Gtk.Align.CENTER,
    )

    return mainbox


if __name__ == "__main__":
    preview = Preview()

    @preview("test")
    def PreviewResultDisplay(_) -> Gtk.Widget:
        """Preview for ResultDisplay."""
        return ResultDisplay(State(["1 + 1 = 2", "1 + 2 = 3"]))

    @preview
    def PreviewLiveDisplay(_) -> Gtk.Widget:
        """Preview for LiveDisplay."""
        return LiveDisplay(State("1 + 1"))

    preview.run()
