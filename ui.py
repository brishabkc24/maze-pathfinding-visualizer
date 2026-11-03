"""The look of the app: a dark theme and the widgets drawn by hand.

Tk's stock buttons, check boxes and scales look like a dialog box from another
decade, so the app draws its own on canvases: rounded buttons, pill switches, a
segmented control, a slider, colour chips, cards with rounded corners and the
items of the sidebar. Every widget keeps the named font it was given and
re-measures itself in ``refit``, so Big text only has to rescale the fonts and
call :func:`refit_all`.
"""
from __future__ import annotations

import math
import tkinter as tk
import tkinter.font as tkfont
import weakref
from typing import Callable, Iterator, Sequence

# -- the palette -----------------------------------------------------------------------
BG = "#0e1117"            # the window
SIDEBAR = "#0a0d13"       # the navigation column on the left
CARD = "#151b25"          # cards and race panels
RAISED = "#1c2431"        # secondary buttons, hovered items
RAISED_HOVER = "#242e3d"
BORDER = "#232c3a"
BORDER_STRONG = "#303b4d"
TEXT = "#e9eef5"
MUTED = "#8d98aa"
FAINT = "#56617a"
ACCENT = "#f3f5f9"        # primary buttons, the selected choice, the active step
ACCENT_HOVER = "#ffffff"
ON_ACCENT = "#0b0e14"     # text on the accent
SELECTED = "#263040"      # the chosen row of a list
TRACK = "#2b3545"         # a switch that is off, the empty part of a slider


def parent_bg(widget: tk.Misc) -> str:
    """The background of ``widget``, so a canvas can blend into it."""
    try:
        return widget.cget("background") or BG
    except tk.TclError:
        return BG


def contrast_text(color: str) -> str:
    """White or near-black, whichever reads better on ``color``."""
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    return ON_ACCENT if 0.299 * r + 0.587 * g + 0.114 * b > 165 else "#ffffff"


def rounded_points(x1: float, y1: float, x2: float, y2: float, r: float,
                   steps: int = 6) -> list[float]:
    """The outline of a rectangle with rounded corners, as polygon points."""
    r = max(0.0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
    points: list[float] = []
    for cx, cy, start in ((x2 - r, y1 + r, -90), (x2 - r, y2 - r, 0),
                          (x1 + r, y2 - r, 90), (x1 + r, y1 + r, 180)):
        for i in range(steps + 1):
            a = math.radians(start + 90 * i / steps)
            points += [cx + r * math.cos(a), cy + r * math.sin(a)]
    return points


def rounded(canvas: tk.Canvas, x1: float, y1: float, x2: float, y2: float, r: float,
            **kw) -> int:
    """Draw a rectangle with rounded corners and return its item id."""
    kw.setdefault("outline", "")
    return canvas.create_polygon(rounded_points(x1, y1, x2, y2, r), **kw)


def descendants(widget: tk.Misc) -> Iterator[tk.Misc]:
    """``widget`` and everything inside it."""
    yield widget
    for child in widget.winfo_children():
        yield from descendants(child)


def eyebrow(parent: tk.Misc, text: str, font: tkfont.Font) -> tk.Label:
    """A small capitalised caption above a group of controls."""
    return tk.Label(parent, text=text.upper(), font=font, bg=parent_bg(parent), fg=MUTED,
                    anchor="w")


# -- widgets that redraw themselves -----------------------------------------------------

_drawn: "weakref.WeakSet[tk.Canvas]" = weakref.WeakSet()


def refit_all() -> None:
    """Re-measure every drawn widget after the fonts changed size. Cards go last,
    so they measure children that already have their new size."""
    alive = []
    for widget in list(_drawn):
        try:
            if widget.winfo_exists():
                alive.append(widget)
        except tk.TclError:
            pass
    for widget in sorted(alive, key=lambda w: isinstance(w, Card)):
        widget.refit()


class Drawn(tk.Canvas):
    """A canvas that draws one control, follows a Tk variable, and blends into
    the background of its parent."""

    def __init__(self, master: tk.Misc, **kw):
        kw.setdefault("bg", parent_bg(master))
        super().__init__(master, highlightthickness=0, bd=0, **kw)
        self._traces: list[tuple[tk.Variable, str]] = []
        _drawn.add(self)
        self.bind("<Destroy>", self._untrace, add="+")

    def watch(self, variable: tk.Variable) -> None:
        """Redraw whenever ``variable`` changes, until this widget is destroyed."""
        name = variable.trace_add("write", lambda *_: self._safe_draw())
        self._traces.append((variable, name))

    def _untrace(self, event: tk.Event) -> None:
        if event.widget is not self:
            return
        for variable, name in self._traces:
            try:
                variable.trace_remove("write", name)
            except tk.TclError:
                pass
        self._traces = []

    def _safe_draw(self) -> None:
        try:
            if self.winfo_exists():
                self.draw()
        except tk.TclError:
            pass

    def size(self) -> tuple[int, int]:
        """The drawn size: the real one once mapped, the requested one before."""
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 1:
            w = int(float(self.cget("width")))
        if h <= 1:
            h = int(float(self.cget("height")))
        return w, h

    def refit(self) -> None:
        self.draw()

    def draw(self) -> None:
        pass


class Button(Drawn):
    """A rounded button. ``primary`` is the one action of a screen, ``secondary``
    the ordinary ones, ``ghost`` the quiet text-only links."""

    STYLES = {  # fill, hovered fill, text, outline
        "primary": (ACCENT, ACCENT_HOVER, ON_ACCENT, ""),
        "secondary": (RAISED, RAISED_HOVER, TEXT, BORDER_STRONG),
        "ghost": ("", RAISED, MUTED, ""),
    }

    def __init__(self, master: tk.Misc, text: str, command: Callable[[], None] | None = None,
                 kind: str = "secondary", font: tkfont.Font | None = None, padx: int = 16,
                 pady: int = 7, min_width: int = 0, radius: int = 8, **kw):
        super().__init__(master, cursor="hand2", **kw)
        self.text = text
        self.command = command
        self.kind = kind
        self.font = font or tkfont.nametofont("TkDefaultFont")
        self.padx, self.pady, self.min_width, self.radius = padx, pady, min_width, radius
        self.disabled = False
        self.hover = False
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
        self.bind("<Button-1>", self._click)
        self.bind("<Configure>", lambda _e: self.draw())
        self.refit()

    def refit(self) -> None:
        w = max(self.min_width, self.font.measure(self.text) + 2 * self.padx)
        h = self.font.metrics("linespace") + 2 * self.pady
        self.config(width=w, height=h)
        self.draw()

    def draw(self) -> None:
        w, h = self.size()
        fill, hover, fg, outline = self.STYLES[self.kind]
        if self.disabled:
            ghost = self.kind == "ghost"
            fill, fg, outline = ("" if ghost else RAISED), FAINT, ("" if ghost else BORDER)
        elif self.hover:
            fill = hover
            if self.kind == "ghost":
                fg = TEXT
        self.delete("all")
        if fill or outline:
            rounded(self, 1, 1, w - 1, h - 1, self.radius, fill=fill or parent_bg(self.master),
                    outline=outline)
        self.create_text(w / 2, h / 2, text=self.text, font=self.font, fill=fg)

    def _enter(self, _event) -> None:
        self.hover = True
        self.draw()

    def _leave(self, _event) -> None:
        self.hover = False
        self.draw()

    def _click(self, _event) -> None:
        if not self.disabled and self.command is not None:
            self.command()

    def set_text(self, text: str) -> None:
        if text != self.text:
            self.text = text
            self.refit()

    def set_state(self, state: str) -> None:
        self.disabled = state == "disabled"
        self.config(cursor="arrow" if self.disabled else "hand2")
        self.draw()


class Switch(Drawn):
    """A pill switch bound to a BooleanVar."""

    W, H = 42, 24

    def __init__(self, master: tk.Misc, variable: tk.BooleanVar,
                 command: Callable[[], None] | None = None, **kw):
        super().__init__(master, width=self.W, height=self.H, cursor="hand2", **kw)
        self.variable = variable
        self.command = command
        self.watch(variable)
        self.bind("<Button-1>", self.toggle)
        self.draw()

    def toggle(self, _event=None) -> None:
        self.variable.set(not self.variable.get())
        if self.command is not None:
            self.command()

    def draw(self) -> None:
        on = bool(self.variable.get())
        w, h = self.W, self.H
        r = h / 2
        self.delete("all")
        rounded(self, 1, 1, w - 1, h - 1, r, fill=ACCENT if on else TRACK)
        k = r - 4
        cx = w - r if on else r
        self.create_oval(cx - k, h / 2 - k, cx + k, h / 2 + k,
                         fill=ON_ACCENT if on else MUTED, outline="")


class SwitchRow(tk.Frame):
    """A switch with its label (and an optional second line) beside it; the
    whole row toggles."""

    def __init__(self, master: tk.Misc, text: str, variable: tk.BooleanVar,
                 command: Callable[[], None] | None = None, font: tkfont.Font | None = None,
                 sub: str | None = None, sub_font: tkfont.Font | None = None, **kw):
        bg = parent_bg(master)
        super().__init__(master, bg=bg, **kw)
        self.switch = Switch(self, variable, command)
        self.switch.pack(side="left", anchor="n", pady=(1, 0))
        words = tk.Frame(self, bg=bg)
        words.pack(side="left", padx=(12, 0), fill="x", expand=True)
        tk.Label(words, text=text, font=font, bg=bg, fg=TEXT, anchor="w").pack(fill="x")
        if sub:
            tk.Label(words, text=sub, font=sub_font, bg=bg, fg=MUTED, anchor="w",
                     justify="left").pack(fill="x")
        for widget in descendants(words):
            widget.bind("<Button-1>", self.switch.toggle)
            widget.configure(cursor="hand2")


class Segmented(Drawn):
    """A row of choices of which exactly one is selected."""

    PAD = 3

    def __init__(self, master: tk.Misc, options: Sequence[tuple[str, object]],
                 variable: tk.Variable, command: Callable[[], None] | None = None,
                 font: tkfont.Font | None = None, padx: int = 16, pady: int = 6, **kw):
        super().__init__(master, cursor="hand2", **kw)
        self.options = list(options)
        self.variable = variable
        self.command = command
        self.font = font or tkfont.nametofont("TkDefaultFont")
        self.padx, self.pady = padx, pady
        self.seg_w = 1
        self.watch(variable)
        self.bind("<Button-1>", self._click)
        self.refit()

    def refit(self) -> None:
        self.seg_w = max(self.font.measure(label) for label, _ in self.options) + 2 * self.padx
        w = self.seg_w * len(self.options) + 2 * self.PAD
        h = self.font.metrics("linespace") + 2 * self.pady + 2 * self.PAD
        self.config(width=w, height=h)
        self.draw()

    def draw(self) -> None:
        w, h = self.size()
        p = self.PAD
        self.delete("all")
        rounded(self, 1, 1, w - 1, h - 1, 9, fill=RAISED, outline=BORDER_STRONG)
        current = self.variable.get()
        for i, (label, value) in enumerate(self.options):
            x1 = p + i * self.seg_w
            x2 = x1 + self.seg_w
            chosen = value == current
            if chosen:
                rounded(self, x1 + 1, p + 1, x2 - 1, h - p - 1, 7, fill=ACCENT)
            self.create_text((x1 + x2) / 2, h / 2, text=label, font=self.font,
                             fill=ON_ACCENT if chosen else MUTED)

    def _click(self, event: tk.Event) -> None:
        i = int((event.x - self.PAD) // self.seg_w)
        if 0 <= i < len(self.options):
            _label, value = self.options[i]
            if value != self.variable.get():
                self.variable.set(value)
                if self.command is not None:
                    self.command()


class Slider(Drawn):
    """A horizontal slider for an IntVar. With no ``length`` it fills its row."""

    H = 26
    R = 8

    def __init__(self, master: tk.Misc, variable: tk.IntVar, lo: int, hi: int,
                 command: Callable[[int], None] | None = None, length: int | None = None, **kw):
        super().__init__(master, height=self.H, width=length or 200, cursor="hand2", **kw)
        self.variable, self.lo, self.hi, self.command = variable, lo, hi, command
        self.watch(variable)
        self.bind("<Configure>", lambda _e: self.draw())
        self.bind("<Button-1>", self._drag)
        self.bind("<B1-Motion>", self._drag)
        self.draw()

    def _drag(self, event: tk.Event) -> None:
        w, _h = self.size()
        pad = self.R + 1
        t = min(1.0, max(0.0, (event.x - pad) / max(1, w - 2 * pad)))
        value = round(self.lo + t * (self.hi - self.lo))
        if value != self.variable.get():
            self.variable.set(value)
            if self.command is not None:
                self.command(value)

    def draw(self) -> None:
        w, h = self.size()
        pad = self.R + 1
        y = h / 2
        span = max(1, self.hi - self.lo)
        t = min(1.0, max(0.0, (self.variable.get() - self.lo) / span))
        x = pad + t * (w - 2 * pad)
        self.delete("all")
        rounded(self, pad, y - 2, w - pad, y + 2, 2, fill=TRACK)
        if x > pad + 1:
            rounded(self, pad, y - 2, x, y + 2, 2, fill=ACCENT)
        self.create_oval(x - self.R, y - self.R, x + self.R, y + self.R, fill=ACCENT,
                         outline=parent_bg(self.master), width=2)


class ColorChips(Drawn):
    """A row of colour dots with a ring around the current one, and a last dot
    that opens the full colour dialog (and shows a colour chosen there)."""

    PITCH = 26
    R = 9

    def __init__(self, master: tk.Misc, palette: Sequence[str], current: str,
                 on_pick: Callable[[str], None], on_more: Callable[[], None],
                 font: tkfont.Font | None = None, **kw):
        super().__init__(master, cursor="hand2", **kw)
        self.palette = tuple(palette)
        self.current = current
        self.on_pick, self.on_more = on_pick, on_more
        self.font = font or tkfont.nametofont("TkDefaultFont")
        self.bind("<Button-1>", self._click)
        self.refit()

    def refit(self) -> None:
        self.config(width=self.PITCH * (len(self.palette) + 1), height=2 * self.R + 8)
        self.draw()

    def draw(self) -> None:
        _w, h = self.size()
        cy, r = h / 2, self.R
        self.delete("all")
        for i, color in enumerate(self.palette):
            cx = self.PITCH * i + self.PITCH / 2
            if color == self.current:
                self.create_oval(cx - r - 3, cy - r - 3, cx + r + 3, cy + r + 3,
                                 outline=TEXT, width=2)
            self.create_oval(cx - r, cy - r, cx + r, cy + r, fill=color, outline="")
        cx = self.PITCH * len(self.palette) + self.PITCH / 2
        if self.current not in self.palette:
            self.create_oval(cx - r - 3, cy - r - 3, cx + r + 3, cy + r + 3, outline=TEXT, width=2)
            self.create_oval(cx - r, cy - r, cx + r, cy + r, fill=self.current, outline="")
        else:
            self.create_oval(cx - r, cy - r, cx + r, cy + r, outline=BORDER_STRONG, dash=(3, 2))
            self.create_text(cx, cy, text="+", font=self.font, fill=MUTED)

    def set_current(self, color: str) -> None:
        self.current = color
        self.draw()

    def _click(self, event: tk.Event) -> None:
        i = int(event.x // self.PITCH)
        if 0 <= i < len(self.palette):
            self.on_pick(self.palette[i])
        elif i == len(self.palette):
            self.on_more()


class Tag(Drawn):
    """A name in a coloured pill: a runner's jersey."""

    def __init__(self, master: tk.Misc, text: str, color: str, font: tkfont.Font,
                 padx: int = 10, pady: int = 3, **kw):
        super().__init__(master, **kw)
        self.text, self.color, self.font = text, color, font
        self.padx, self.pady = padx, pady
        self.refit()

    def refit(self) -> None:
        self.config(width=self.font.measure(self.text) + 2 * self.padx,
                    height=self.font.metrics("linespace") + 2 * self.pady)
        self.draw()

    def draw(self) -> None:
        w, h = self.size()
        self.delete("all")
        rounded(self, 1, 1, w - 1, h - 1, h / 2, fill=self.color)
        self.create_text(w / 2, h / 2, text=self.text, font=self.font,
                         fill=contrast_text(self.color))

    def set_color(self, color: str) -> None:
        self.color = color
        self.draw()


class Card(tk.Canvas):
    """A panel with rounded corners. Put widgets in ``card.body`` (a Frame with
    the card's colour), then call :meth:`fit` so the card takes their size.
    A card that is packed to fill its space grows with it instead."""

    INSET = 4

    def __init__(self, master: tk.Misc, fill: str = CARD, outline: str = BORDER,
                 radius: int = 12, padx: int = 16, pady: int = 14, **kw):
        kw.setdefault("bg", parent_bg(master))
        super().__init__(master, highlightthickness=0, bd=0, width=10, height=10, **kw)
        self.fill, self.radius = fill, radius
        self.shape = self.create_polygon(0, 0, 0, 0, fill=fill, outline=outline)
        self.body = tk.Frame(self, bg=fill, padx=padx, pady=pady)
        self.window = self.create_window(self.INSET, self.INSET, window=self.body, anchor="nw")
        self.bind("<Configure>", lambda e: self._redraw(e.width, e.height))
        _drawn.add(self)

    def fit(self, width: bool = True) -> None:
        """Request the size of the content (only the height if ``width`` is False)."""
        self.body.update_idletasks()
        h = self.body.winfo_reqheight() + 2 * self.INSET
        if width:
            w = self.body.winfo_reqwidth() + 2 * self.INSET
            self.config(width=w, height=h)
        else:
            w = self.winfo_width() if self.winfo_width() > 1 else 10
            self.config(height=h)
        self._redraw(w, h)

    def refit(self) -> None:
        self.fit()

    def _redraw(self, w: int, h: int) -> None:
        self.coords(self.shape, *rounded_points(1, 1, w - 1, h - 1, self.radius))
        self.itemconfig(self.window, width=max(1, w - 2 * self.INSET),
                        height=max(1, h - 2 * self.INSET))

    def set_outline(self, color: str, width: int = 1) -> None:
        self.itemconfig(self.shape, outline=color, width=width)


class StatTile(Card):
    """A card with one number and a caption under it."""

    def __init__(self, master: tk.Misc, caption: str, value_font: tkfont.Font,
                 caption_font: tkfont.Font, **kw):
        super().__init__(master, padx=18, pady=10, **kw)
        self.value = tk.Label(self.body, text="", font=value_font, bg=self.fill, fg=TEXT,
                              anchor="w")
        self.value.pack(fill="x")
        self.caption = tk.Label(self.body, text=caption, font=caption_font, bg=self.fill,
                                fg=MUTED, anchor="w")
        self.caption.pack(fill="x")
        self.fit()

    def set(self, value: str, caption: str | None = None) -> None:
        self.value.config(text=value)
        if caption is not None:
            self.caption.config(text=caption)
        self.fit()


class NavItem(Drawn):
    """One step in the sidebar: a numbered badge, the name and a hint.
    States: ``active`` (the screen showing), ``normal`` and ``disabled``."""

    def __init__(self, master: tk.Misc, number: int, label: str, hint: str,
                 command: Callable[[], None], font: tkfont.Font, hint_font: tkfont.Font,
                 badge_font: tkfont.Font, **kw):
        super().__init__(master, cursor="hand2", **kw)
        self.number, self.label, self.hint, self.command = number, label, hint, command
        self.font, self.hint_font, self.badge_font = font, hint_font, badge_font
        self.state = "normal"
        self.hover = False
        self.compact = False
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
        self.bind("<Button-1>", self._click)
        self.bind("<Configure>", lambda _e: self.draw())
        self.refit()

    def refit(self) -> None:
        h = self.font.metrics("linespace") + self.hint_font.metrics("linespace") + 22
        self.config(height=h)
        self.draw()

    def set_compact(self, compact: bool) -> None:
        """Badge only, for the narrow rail the sidebar becomes during a race."""
        self.compact = compact
        self.draw()

    def draw(self) -> None:
        w, h = self.size()
        active = self.state == "active"
        disabled = self.state == "disabled"
        edge = 8 if self.compact else 10
        self.delete("all")
        if active:
            rounded(self, edge, 3, w - edge, h - 3, 10, fill=CARD)
            self.create_rectangle(0, h / 2 - 12, 3, h / 2 + 12, fill=ACCENT, outline="")
        elif self.hover and not disabled:
            rounded(self, edge, 3, w - edge, h - 3, 10, fill=RAISED)
        bx, by, r = (w / 2 if self.compact else 34), h / 2, 13
        if active:
            self.create_oval(bx - r, by - r, bx + r, by + r, fill=ACCENT, outline="")
            number_fg = ON_ACCENT
        else:
            self.create_oval(bx - r, by - r, bx + r, by + r,
                             outline=BORDER if disabled else BORDER_STRONG, width=1.5)
            number_fg = FAINT if disabled else MUTED
        self.create_text(bx, by, text=str(self.number), font=self.badge_font, fill=number_fg)
        if self.compact:
            return
        label_fg = TEXT if active else (FAINT if disabled else "#c5cdd9")
        self.create_text(60, by - 8, text=self.label, font=self.font, fill=label_fg, anchor="w")
        self.create_text(60, by + 9, text=self.hint, font=self.hint_font,
                         fill=FAINT if disabled else MUTED, anchor="w")

    def set_state(self, state: str) -> None:
        self.state = state
        self.config(cursor="arrow" if state == "disabled" else "hand2")
        self.draw()

    def _enter(self, _event) -> None:
        self.hover = True
        self.draw()

    def _leave(self, _event) -> None:
        self.hover = False
        self.draw()

    def _click(self, _event) -> None:
        if self.state != "disabled":
            self.command()


class BrandMark(Drawn):
    """The app's mark: a path through a little maze, start to goal."""

    def __init__(self, master: tk.Misc, size: int = 40, **kw):
        super().__init__(master, width=size, height=size, **kw)
        self.px = size
        self.draw()

    def draw(self) -> None:
        s = self.px
        u = s / 40
        self.delete("all")
        rounded(self, 0, 0, s, s, 10 * u, fill=ACCENT)
        path = [10, 30, 10, 14, 22, 14, 22, 26, 30, 26, 30, 10]
        self.create_line(*(p * u for p in path), fill=ON_ACCENT, width=3 * u,
                         joinstyle="round", capstyle="round")
        self.create_oval(7 * u, 27 * u, 13 * u, 33 * u, fill="#3ddc84", outline="")
        self.create_oval(27 * u, 7 * u, 33 * u, 13 * u, fill="#ff5c5c", outline="")
