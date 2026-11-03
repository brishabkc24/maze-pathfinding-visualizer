"""Maze Pathfinding Visualizer: the Tkinter app.

The window is a sidebar of five steps and one screen showing at a time, like
a setup flow followed by the race:

    1  Maze      pick a ready-made maze, make a random one, or draw your own
    2  Runners   switch on the algorithms that race, give each its colour, choose the guess
    3  Speed     moves per tick, a countdown, big text for a projector
    4  Race      every chosen algorithm solves the same maze at the same time
    5  Results   who won, the awards, the full table and a chart

The model (grid.py), the algorithms (algorithms.py) and the lockstep race
(race.py) have no Tkinter in them; this file is only the interface, and the
theme and the hand-drawn widgets it is built from live in ui.py.

Run with ``python app.py``.
"""
from __future__ import annotations

import math
import random
import sys
import time
import tkinter as tk
import tkinter.font as tkfont
from datetime import datetime
from tkinter import colorchooser, ttk

import ui
from algorithms import ALGORITHMS, HEURISTICS, bfs, run
from grid import Grid, Node
from maze_gen import generate
from race import Race, Results, Runner
from templates import TEMPLATES

TICK_MS = 25             # one animation tick; the speed setting is moves per tick
STATS_EVERY = 4          # ticks between counter refreshes: ten a second is plenty
DEFAULT_TEMPLATE = "Maze with some loops"

# The maze itself: slate corridors between near-black walls, so the runners'
# colours are the brightest thing on the screen.
COLOR_WALL = "#070a10"
COLOR_OPEN = "#1c2433"
COLOR_GRIDLINE = "#263042"
COLOR_START = "#3ddc84"
COLOR_GOAL = "#ff5c5c"
COLOR_PATH = "#ffc400"

# The colours the runners start with; the Runners screen can change them.
ALGO_COLORS = {
    "BFS": "#3b82f6",
    "DFS": "#a855f7",
    "Dijkstra": "#14b8a6",
    "A*": "#f97316",
    "Greedy": "#ec4899",
    "Hill Climbing": "#94a3b8",
}

# The colour chips offered for every runner. Gold is left out: it is the path.
PALETTE = ("#3b82f6", "#a855f7", "#14b8a6", "#f97316", "#ec4899", "#94a3b8",
           "#22c55e", "#ef4444", "#06b6d4", "#84cc16", "#f43f5e", "#f1f5f9")

# One line under each runner's name, in plain words.
TAGLINES = {
    "BFS": "checks in rings around the start",
    "DFS": "follows one corridor to its end",
    "Dijkstra": "nearest to the start first",
    "A*": "distance so far + guess to the goal",
    "Greedy": "guess to the goal only",
    "Hill Climbing": "always steps closer, no memory",
}

QUICK_PICKS = (
    ("All six", tuple(ALGORITHMS)),
    ("BFS vs DFS", ("BFS", "DFS")),
    ("Dijkstra vs A*", ("Dijkstra", "A*")),
    ("A*, Greedy, Hill Climbing", ("A*", "Greedy", "Hill Climbing")),
)

SPEED_PRESETS = (
    ("Slow", 1, "One move per tick, so every decision can be talked through."),
    ("Normal", 4, "The default. Easy to follow, and a race is over in well under a minute."),
    ("Fast", 12, "Quick enough to run the same maze several times in a row."),
    ("Very fast", 40, "Almost instant. Use Step and Finish on the race screen for the details."),
)

# The sidebar: key, name, and the hint under the name.
STEPS = (("maze", "Maze", "Pick a course or draw one"),
         ("runners", "Runners", "Algorithms and colours"),
         ("speed", "Speed", "Moves per tick, countdown"),
         ("race", "Race", "Side by side, live"),
         ("results", "Results", "Who won, and why"))

HELP = (
    ("h", "How to use the Maze Pathfinding Visualizer\n"),
    ("", "The app is five screens, listed down the left side.\n"
         "1  Maze: pick one of the 26 ready-made mazes, make a random one with as many loops "
         "as you like, or start from a blank canvas. Draw on the preview: left-drag paints "
         "walls, right-drag erases them, and the green start and red goal dots can be dragged.\n"
         "2  Runners: switch on the algorithms that race, give each one its colour, and choose "
         "the guess to the goal that A*, Greedy and Hill Climbing use.\n"
         "3  Speed: how many moves every runner makes per tick, a countdown, and big text for "
         "a projector. Then press Start the race.\n"
         "4  Race: every runner solves the same maze at the same time, each in its own panel. "
         "Pause, Step one move at a time, Finish, change the speed, or race again.\n"
         "5  Results: who won, the awards, the full table with every time, and a chart of the "
         "cells each runner checked.\n"),
    ("h", "What the colours mean\n"),
    ("", "Green dot: the start.  Red dot: the goal.  Near-black cells: walls.\n"
         "A runner's full colour: cells it has found but not checked yet (its frontier).\n"
         "A dimmer shade of it: cells it has already checked (explored).\n"
         "Gold: the path it finally chose.\n"),
    ("h", "The algorithms\n"),
    ("BFS", "BFS, breadth-first search.  "),
    ("", "Uses a queue: first in, first out. Checks every cell one step away, then two steps "
         "away, and so on, like ripples on a pond. Always finds the shortest path, but checks "
         "a lot of cells.\n"),
    ("DFS", "DFS, depth-first search.  "),
    ("", "Uses a stack: last in, first out. Follows one corridor as far as it goes, then backs "
         "up and tries the next. Finds a path whenever there is one, but usually not the "
         "shortest.\n"),
    ("Dijkstra", "Dijkstra.  "),
    ("", "Uses a priority queue ordered by distance from the start. Finds the shortest path. "
         "In a maze where every step costs the same it checks the same cells as BFS.\n"),
    ("A*", "A*.  "),
    ("", "Priority queue ordered by distance from the start plus a guess of the distance to "
         "the goal (the guess chosen on the Runners screen). The guess never overestimates, so "
         "the path is still the shortest, and far fewer cells are checked.\n"),
    ("Greedy", "Greedy best-first.  "),
    ("", "Priority queue ordered by the guess to the goal only. Very quick, but the path can "
         "be longer, and a wall between it and the goal fools it for a while.\n"),
    ("Hill Climbing", "Hill climbing.  "),
    ("", "No queue at all. From the current cell, step to the neighbour closest to the goal; "
         "if no neighbour is closer, stop. It keeps no memory of other options, so one wall in "
         "the way leaves it stuck at a local minimum. That is why search needs a frontier. "
         "The cells it looks at are shown in its full colour, but it never returns to them.\n"),
    ("h", "The guess to the goal\n"),
    ("", "A*, Greedy and Hill Climbing need a guess of how far a cell is from the goal, and "
         "the Runners screen chooses it. Manhattan counts rows plus columns, which is the exact "
         "distance when no walls are in the way. Euclidean is the straight-line distance. "
         "Chebyshev is the larger of the rows and the columns. None of them ever overestimates, "
         "so A* finds the shortest path with any of them, but Manhattan is the closest guess on "
         "this grid, so A* checks the fewest cells with it. Try one maze with each guess: Greedy "
         "takes different routes, and with Chebyshev even the empty room stops Hill Climbing, "
         "because a step that shortens only the smaller of the two distances does not count as "
         "closer.\n"),
    ("h", "The results\n"),
    ("", "Every runner makes the same number of moves per tick, so the race is fair. A move is "
         "one look at one cell: finding a new cell (adding it to the frontier) or checking one "
         "(taking it off). An algorithm that finds four neighbours at once therefore spends "
         "more moves on a cell than Hill Climbing, which looks at a few and keeps none.\n"
         "The winner is the runner that reaches the goal in the fewest moves. Three more "
         "awards: the shortest path (compared with the BFS path), the fewest cells checked, and "
         "the quickest compute time, which is the time spent inside the algorithm itself "
         "without the drawing. Time taken runs from the start of the race to the runner's "
         "finish and depends on the speed. A runner that never reaches the goal did not "
         "finish: Hill Climbing when a wall is in its way, or everyone when the goal is "
         "sealed.\n"),
    ("h", "Keyboard\n"),
    ("", "On the race screen: Space starts or pauses, Right arrow steps one move, F finishes, "
         "Esc pauses.  F1 opens this window from anywhere.\n"),
)


def blend(color: str, other: str, t: float) -> str:
    """Mix ``color`` towards ``other`` by ``t`` (0 keeps color, 1 gives other)."""
    a = [int(color[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(other[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def frontier_shade(color: str) -> str:
    """Cells a runner has found but not checked yet: its full colour."""
    return color


def explored_shade(color: str) -> str:
    """Cells a runner has checked: its colour sunk towards the corridor floor."""
    return blend(color, COLOR_OPEN, 0.6)


def fmt_clock(moment: datetime | None) -> str:
    if moment is None:
        return ""
    return moment.strftime("%H:%M:%S.") + f"{moment.microsecond // 1000:03d}"


def plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


class Fonts:
    """Named fonts shared by every widget, so Big text can rescale them all at once.
    Headings and numbers use a display face, the rest the system text face."""

    SIZES = {"body": 10, "bold": 10, "small": 9, "label": 9, "eyebrow": 8, "nav": 11,
             "chip": 10, "title": 13, "h1": 20, "display": 26, "brand": 15, "number": 22,
             "big": 18, "huge": 64}

    def __init__(self) -> None:
        families = set(tkfont.families())

        def pick(*names: str) -> str:
            return next((n for n in names if n in families), "Helvetica")

        display = pick("Bahnschrift", "Segoe UI Variable Display", "Segoe UI", "Helvetica")
        text = pick("Segoe UI", "Helvetica")
        s = self.SIZES
        self.body = tkfont.Font(family=text, size=s["body"])
        self.bold = tkfont.Font(family=text, size=s["bold"], weight="bold")
        self.small = tkfont.Font(family=text, size=s["small"])
        self.label = tkfont.Font(family=text, size=s["label"], weight="bold")
        self.eyebrow = tkfont.Font(family=text, size=s["eyebrow"], weight="bold")
        self.nav = tkfont.Font(family=text, size=s["nav"], weight="bold")
        self.chip = tkfont.Font(family=text, size=s["chip"], weight="bold")
        self.title = tkfont.Font(family=display, size=s["title"], weight="bold")
        self.h1 = tkfont.Font(family=display, size=s["h1"], weight="bold")
        self.display = tkfont.Font(family=display, size=s["display"], weight="bold")
        self.brand = tkfont.Font(family=display, size=s["brand"], weight="bold")
        self.number = tkfont.Font(family=display, size=s["number"], weight="bold")
        self.big = tkfont.Font(family=display, size=s["big"], weight="bold")
        self.huge = tkfont.Font(family=display, size=s["huge"], weight="bold")

    def scale(self, factor: float) -> None:
        for name, size in self.SIZES.items():
            getattr(self, name).configure(size=round(size * factor))


class GridCanvas(tk.Canvas):
    """Draws one :class:`Grid`.

    Every cell rectangle is created once, here in ``__init__``. Afterwards
    cells are only recolored with ``itemconfig`` and the start and goal dots
    are moved with ``coords``; nothing is deleted and redrawn. That is what
    keeps a Tkinter canvas smooth while thousands of cells are animated.
    """

    def __init__(self, master: tk.Misc, model: Grid, cell: int, **kwargs):
        super().__init__(master, width=model.cols * cell, height=model.rows * cell,
                         highlightthickness=0, bg=COLOR_OPEN, **kwargs)
        self.model = model
        self.cell = cell
        outline = COLOR_GRIDLINE if cell >= 8 else ""
        self.rects = [
            [self.create_rectangle(c * cell, r * cell, (c + 1) * cell, (r + 1) * cell,
                                   fill=COLOR_OPEN, outline=outline)
             for c in range(model.cols)]
            for r in range(model.rows)
        ]
        self._dot_pad = max(1, cell // 5)
        self.start_dot = self.create_oval(0, 0, 0, 0, fill=COLOR_START, outline="")
        self.goal_dot = self.create_oval(0, 0, 0, 0, fill=COLOR_GOAL, outline="")
        self.redraw()

    def node_at(self, x: int, y: int) -> Node | None:
        """The cell under canvas pixel ``(x, y)``, or None outside the grid."""
        r, c = y // self.cell, x // self.cell
        return (r, c) if self.model.in_bounds(r, c) else None

    def paint_cell(self, node: Node, color: str | None = None) -> None:
        """Recolor one cell; by default from the model (wall or open)."""
        r, c = node
        if color is None:
            color = COLOR_WALL if self.model.is_wall(r, c) else COLOR_OPEN
        self.itemconfig(self.rects[r][c], fill=color)

    def place_dots(self) -> None:
        self._place(self.start_dot, self.model.start)
        self._place(self.goal_dot, self.model.goal)

    def _place(self, item: int, node: Node) -> None:
        r, c = node
        pad, size = self._dot_pad, self.cell
        self.coords(item, c * size + pad, r * size + pad,
                    (c + 1) * size - pad, (r + 1) * size - pad)

    def redraw(self) -> None:
        """Repaint every cell from the model. For bulk changes only."""
        for r in range(self.model.rows):
            for c in range(self.model.cols):
                self.paint_cell((r, c))
        self.place_dots()


class Panel(ui.Card):
    """One runner's view on the race screen: its name in a coloured pill, a
    one-line description, live counters in plain words, and the maze canvas."""

    PADX, PADY = 8, 6

    def __init__(self, master: tk.Misc, model: Grid, name: str, color: str,
                 cell: int, fonts: Fonts, compact: bool = False):
        super().__init__(master, padx=self.PADX, pady=self.PADY)
        self.name = name
        self.color = color
        self.compact = compact
        self.explored_color = explored_shade(color)
        self.frontier_color = frontier_shade(color)

        body = self.body
        head = tk.Frame(body, bg=ui.CARD)
        head.pack(fill="x")
        ui.Tag(head, name, color, fonts.chip).pack(side="left")
        if compact:
            # Narrow panel: counters share the name line and the tagline is left out.
            self.stats = tk.Label(head, text="ready", bg=ui.CARD, fg=ui.MUTED,
                                  font=fonts.small, anchor="e")
            self.stats.pack(side="right", fill="x", expand=True)
        else:
            tk.Label(head, text=TAGLINES[name], bg=ui.CARD, fg=ui.MUTED,
                     font=fonts.small, anchor="w").pack(side="left", padx=(8, 0))
            self.stats = tk.Label(body, text="ready", bg=ui.CARD, fg=ui.TEXT,
                                  font=fonts.body, anchor="w")
            self.stats.pack(fill="x", pady=(4, 6))

        self.canvas = GridCanvas(body, model, cell)
        self.canvas.pack(pady=(6, 0) if compact else 0)
        self.fit()

    def apply(self, event: tuple) -> None:
        kind, payload = event
        if kind == "discover":
            self.canvas.paint_cell(payload, self.frontier_color)
        elif kind == "visit":
            self.canvas.paint_cell(payload, self.explored_color)
        elif kind == "done" and payload:
            for node in payload:
                self.canvas.paint_cell(node, COLOR_PATH)

    def render(self, runner: Runner) -> None:
        """Paint a runner's whole state at once."""
        for node in runner.frontier:
            self.canvas.paint_cell(node, self.frontier_color)
        for node in runner.explored:
            self.canvas.paint_cell(node, self.explored_color)
        if runner.path:
            for node in runner.path:
                self.canvas.paint_cell(node, COLOR_PATH)

    def show_stats(self, runner: Runner, race: Race) -> None:
        n = len(runner.explored)
        seconds = f"{runner.elapsed():.1f} s"
        sep = " · " if self.compact else "   ·   "
        if not runner.done:
            parts = [f"{n} checked", f"{len(runner.frontier)} waiting", seconds]
        elif runner.found:
            extra = runner.path_length - (race.optimal_length or runner.path_length)
            if self.compact:
                verdict = "shortest ✓" if extra == 0 else f"+{extra} steps"
                parts = [f"{runner.path_length} steps", f"{n} cells", verdict, seconds]
            else:
                verdict = ("shortest path ✓" if extra == 0
                           else f"{extra} steps longer than shortest")
                parts = [f"path {runner.path_length} steps", f"checked {n} cells",
                         verdict, seconds]
        else:
            stuck = runner.name == "Hill Climbing" and race.optimal_length is not None
            if self.compact:
                why = "stuck at a wall" if stuck else "no path"
                parts = [why, f"{n} cells", seconds]
            else:
                why = "stuck: a wall is in the way" if stuck else "no path exists"
                parts = [why, f"checked {n} cells", seconds]
        self.stats.config(text=sep.join(parts))


class Sidebar(tk.Frame):
    """The column on the left: the mark, the five steps in two groups, and the
    help link. The current step is highlighted, the others can be clicked, and
    Results is greyed out until a race has finished. While the race screen
    shows, the sidebar folds into a narrow rail of badges so the panels get
    the width."""

    WIDTH = 220
    RAIL = 64

    def __init__(self, master: tk.Misc, app: App):
        super().__init__(master, bg=ui.SIDEBAR, width=self.WIDTH)
        self.pack_propagate(False)
        f = app.fonts
        self.compact = False
        self.brand = tk.Frame(self, bg=ui.SIDEBAR)
        self.brand.pack(fill="x", padx=18, pady=(22, 14))
        ui.BrandMark(self.brand, 40).pack(anchor="w")
        self.words = tk.Frame(self.brand, bg=ui.SIDEBAR)
        self.words.pack(fill="x", pady=(12, 0))
        tk.Label(self.words, text="Maze Pathfinding", font=f.brand, bg=ui.SIDEBAR, fg=ui.TEXT,
                 anchor="w").pack(fill="x")
        tk.Label(self.words, text="Visualizer", font=f.brand, bg=ui.SIDEBAR, fg=ui.MUTED,
                 anchor="w").pack(fill="x")

        self.items: dict[str, ui.NavItem] = {}
        self.eyebrows: list[tuple[tk.Label, str]] = []
        for title, steps in (("Set up", STEPS[:3]), ("Run", STEPS[3:])):
            label = ui.eyebrow(self, title, f.eyebrow)
            label.pack(fill="x", padx=22, pady=(14, 4))
            self.eyebrows.append((label, title))
            for key, name, hint in steps:
                number = [s[0] for s in STEPS].index(key) + 1
                item = ui.NavItem(self, number, name, hint, lambda k=key: app.show(k),
                                  f.nav, f.small, f.chip)
                item.pack(fill="x")
                self.items[key] = item

        foot = tk.Frame(self, bg=ui.SIDEBAR)
        foot.pack(side="bottom", fill="x", padx=14, pady=16)
        self.help_button = ui.Button(foot, "How it works", app.show_help, kind="ghost",
                                     font=f.body)
        self.help_button.pack(side="left")
        self.key_label = tk.Label(foot, text="F1", font=f.small, bg=ui.SIDEBAR, fg=ui.FAINT)
        self.key_label.pack(side="left", padx=(4, 0))

    def set_compact(self, compact: bool) -> None:
        if compact == self.compact:
            return
        self.compact = compact
        self.config(width=self.RAIL if compact else self.WIDTH)
        self.brand.pack_configure(padx=12 if compact else 18)
        if compact:
            self.words.pack_forget()
            self.key_label.pack_forget()
        else:
            self.words.pack(fill="x", pady=(12, 0))
            self.key_label.pack(side="left", padx=(4, 0))
        for label, title in self.eyebrows:
            label.config(text="" if compact else title.upper())
        self.help_button.set_text("?" if compact else "How it works")
        for item in self.items.values():
            item.set_compact(compact)

    def set_current(self, current: str, finished: bool) -> None:
        for key, item in self.items.items():
            if key == current:
                item.set_state("active")
            elif key == "results" and not finished:
                item.set_state("disabled")
            else:
                item.set_state("normal")


class Screen(tk.Frame):
    """One screen of the app. ``refresh`` runs every time it is shown and
    ``relayout`` when the window changes size while it is showing."""

    def __init__(self, master: tk.Misc, app: App):
        super().__init__(master, bg=ui.BG)
        self.app = app
        self.fonts = app.fonts

    def refresh(self) -> None:
        pass

    def relayout(self) -> None:
        pass

    def heading(self, parent: tk.Misc, text: str, sub: str | None = None,
                wrap: int = 900) -> tk.Frame:
        block = tk.Frame(parent, bg=ui.BG)
        block.pack(fill="x")
        tk.Label(block, text=text, font=self.fonts.display, bg=ui.BG, fg=ui.TEXT,
                 anchor="w").pack(fill="x")
        if sub:
            tk.Label(block, text=sub, font=self.fonts.body, bg=ui.BG, fg=ui.MUTED,
                     anchor="w", justify="left", wraplength=wrap).pack(fill="x", pady=(4, 0))
        return block

    def eyebrow(self, parent: tk.Misc, text: str, pady=(18, 6)) -> tk.Label:
        label = ui.eyebrow(parent, text, self.fonts.eyebrow)
        label.pack(fill="x", pady=pady)
        return label

    def button(self, parent: tk.Misc, text: str, command, kind: str = "secondary",
               **kw) -> ui.Button:
        font = self.fonts.bold if kind == "primary" else self.fonts.body
        return ui.Button(parent, text, command, kind=kind, font=font, **kw)

    def nav(self, back: tuple | None = None, forward: tuple | None = None,
            extra: tuple = ()) -> tk.Frame:
        """The bar along the bottom: a quiet Back on the left, the one primary
        action on the right, and any further links beside it."""
        bar = tk.Frame(self, bg=ui.BG)
        bar.pack(side="bottom", fill="x", pady=(12, 0))
        tk.Frame(bar, bg=ui.BORDER, height=1).pack(fill="x", pady=(0, 10))
        row = tk.Frame(bar, bg=ui.BG)
        row.pack(fill="x")
        if back:
            self.button(row, back[0], back[1], kind="ghost").pack(side="left")
        if forward:
            self.button(row, forward[0], forward[1], kind="primary", padx=22,
                        pady=9).pack(side="right")
        for label, command in extra:
            self.button(row, label, command, kind="ghost").pack(side="right", padx=(0, 4))
        return row


class MazeScreen(Screen):
    """Step 1: the list of mazes on the left, an editable preview on the right."""

    def __init__(self, master: tk.Misc, app: App):
        super().__init__(master, app)
        self.nav(forward=("Next: choose the runners  →", lambda: app.show("runners")))
        body = tk.Frame(self, bg=ui.BG)
        body.pack(fill="both", expand=True)

        left = tk.Frame(body, bg=ui.BG, width=300)
        left.pack(side="left", fill="y", padx=(0, 26))
        left.pack_propagate(False)
        self.heading(left, "Choose a maze", "26 ready-made mazes, each built to make a point.",
                     wrap=280)
        list_card = ui.Card(left, padx=6, pady=6)
        list_card.pack(fill="both", expand=True, pady=(14, 0))
        self.listbox = tk.Listbox(list_card.body, font=self.fonts.body, activestyle="none",
                                  exportselection=False, relief="flat", bd=0,
                                  highlightthickness=0, bg=ui.CARD, fg=ui.TEXT,
                                  selectbackground=ui.SELECTED, selectforeground=ui.TEXT,
                                  takefocus=0)
        scroll = ttk.Scrollbar(list_card.body, command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scroll.set)
        self.listbox.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        for i, t in enumerate(TEMPLATES):
            self.listbox.insert("end", f"  {i + 1}.  {t.name}")
        self.listbox.bind("<<ListboxSelect>>", self.on_pick)

        self.eyebrow(left, "Or make your own")
        self.button(left, "Make a random maze", self.make_random).pack(fill="x")
        tk.Label(left, text="Loops in the random maze", font=self.fonts.small, bg=ui.BG,
                 fg=ui.MUTED, anchor="w").pack(fill="x", pady=(10, 0))
        self.braid = tk.IntVar(value=15)
        ui.Slider(left, self.braid, 0, 60).pack(fill="x")
        ends = tk.Frame(left, bg=ui.BG)
        ends.pack(fill="x")
        tk.Label(ends, text="none", bg=ui.BG, fg=ui.FAINT, font=self.fonts.small).pack(side="left")
        tk.Label(ends, text="many", bg=ui.BG, fg=ui.FAINT, font=self.fonts.small).pack(side="right")
        self.button(left, "Start from a blank canvas", self.blank).pack(fill="x", pady=(12, 0))
        self.button(left, "Clear the walls of this maze", self.clear_walls,
                    kind="ghost").pack(fill="x", pady=(6, 0))

        right = tk.Frame(body, bg=ui.BG)
        right.pack(side="left", fill="both", expand=True)
        self.name_label = tk.Label(right, font=self.fonts.h1, bg=ui.BG, fg=ui.TEXT, anchor="w")
        self.name_label.pack(fill="x")
        self.note_label = tk.Label(right, font=self.fonts.body, bg=ui.BG, fg=ui.MUTED,
                                   anchor="w", justify="left", wraplength=900)
        self.note_label.pack(fill="x", pady=(4, 12))
        self.preview_card = ui.Card(right, padx=10, pady=10)
        self.preview_card.pack(fill="both", expand=True)
        self.holder = self.preview_card.body
        facts = tk.Frame(right, bg=ui.BG)
        facts.pack(fill="x", pady=(12, 0))
        self.tiles = [ui.StatTile(facts, caption, self.fonts.number, self.fonts.small)
                      for caption in ("cells", "walls", "shortest path")]
        for tile in self.tiles:
            tile.pack(side="left", padx=(0, 10))
        tk.Label(facts, text="Draw on the maze: left-drag paints walls, right-drag erases "
                             "them, and the green start and red goal dots can be dragged.",
                 font=self.fonts.small, bg=ui.BG, fg=ui.MUTED, anchor="w",
                 justify="left", wraplength=420).pack(side="left", padx=(14, 0))
        self.canvas: GridCanvas | None = None
        self.drag: str | None = None
        self._facts_id: str | None = None
        self._size = (0, 0)

    # -- showing ----------------------------------------------------------------------

    def refresh(self) -> None:
        self.name_label.config(text=self.app.maze_name)
        self.note_label.config(text=self.app.maze_note)
        self.build_preview()                 # lays the window out, so the list knows its height
        self.listbox.selection_clear(0, "end")
        self.listbox.yview_moveto(0)
        index = self.app.template_index
        if index is not None:
            self.listbox.selection_set(index)
            self.listbox.see(index)
        self.update_facts()

    def build_preview(self) -> None:
        root = self.app.root
        root.update_idletasks()
        card = self.preview_card
        w = card.winfo_width() - 2 * ui.Card.INSET - 20
        h = card.winfo_height() - 2 * ui.Card.INSET - 20
        if w < 100 or h < 100:                      # not laid out yet: estimate
            w, h = root.winfo_width() - Sidebar.WIDTH - 400, root.winfo_height() - 370
        grid = self.app.grid
        cell = max(4, min(22, w // grid.cols, h // grid.rows))
        for child in self.holder.winfo_children():
            child.destroy()
        self.canvas = GridCanvas(self.holder, grid, cell)
        self.canvas.pack(expand=True)
        canvas = self.canvas
        canvas.bind("<Button-1>", self.on_left_press)
        canvas.bind("<B1-Motion>", self.on_left_drag)
        canvas.bind("<Button-3>", self.on_right)
        canvas.bind("<B3-Motion>", self.on_right)
        canvas.bind("<ButtonRelease-1>", self.on_release)
        canvas.bind("<ButtonRelease-3>", self.on_release)
        self._size = (root.winfo_width(), root.winfo_height())

    def relayout(self) -> None:
        root = self.app.root
        if (root.winfo_width(), root.winfo_height()) != self._size:
            self.build_preview()

    def update_facts(self) -> None:
        self._facts_id = None
        grid = self.app.grid
        path, _ = run(bfs, grid)
        cells, walls, shortest = self.tiles
        cells.set(f"{grid.cols} × {grid.rows}")
        walls.set(str(grid.wall_count))
        if path:
            shortest.set(f"{len(path) - 1} steps", "shortest path")
        else:
            shortest.set("none", "no path to the goal")

    def _facts_soon(self) -> None:
        if self._facts_id is not None:
            self.app.root.after_cancel(self._facts_id)
        self._facts_id = self.app.root.after(150, self.update_facts)

    # -- choosing ---------------------------------------------------------------------

    def on_pick(self, _event=None) -> None:
        selection = self.listbox.curselection()
        if not selection:
            return
        index = selection[0]
        template = TEMPLATES[index]
        self.app.set_maze(template.build(), f"{index + 1}.  {template.name}",
                          template.note, index)

    def make_random(self) -> None:
        seed = random.randrange(1, 1_000_000)
        loops = self.braid.get()
        grid = generate(seed=seed, braid_fraction=loops / 100)
        self.app.set_maze(grid, f"Random maze {seed}",
                          f"A random maze with {loops}% of its inner walls removed. With no "
                          "loops every algorithm finds the same path; with loops the "
                          "shortcuts separate them.", None)

    def blank(self) -> None:
        self.app.set_maze(Grid(), "Blank canvas",
                          "Draw your own maze: left-drag paints walls, right-drag erases "
                          "them, and the start and goal dots can be dragged anywhere.", None)

    def clear_walls(self) -> None:
        self.app.grid.clear_walls()
        self.app.discard_race()
        if self.canvas is not None:
            self.canvas.redraw()
        self.update_facts()

    # -- drawing on the preview ------------------------------------------------------

    def on_left_press(self, event: tk.Event) -> None:
        node = self.canvas.node_at(event.x, event.y)
        if node is None:
            return
        grid = self.app.grid
        if node == grid.start:
            self.drag = "start"
        elif node == grid.goal:
            self.drag = "goal"
        else:
            self.drag = "wall"
            self.paint(node, wall=True)

    def on_left_drag(self, event: tk.Event) -> None:
        node = self.canvas.node_at(event.x, event.y)
        if node is None:
            return
        if self.drag in ("start", "goal"):
            self.move_endpoint(self.drag, node)
        elif self.drag == "wall":
            self.paint(node, wall=True)

    def on_right(self, event: tk.Event) -> None:
        node = self.canvas.node_at(event.x, event.y)
        if node is not None:
            self.drag = "erase"
            self.paint(node, wall=False)

    def on_release(self, _event: tk.Event) -> None:
        self.drag = None

    def paint(self, node: Node, wall: bool) -> None:
        r, c = node
        grid = self.app.grid
        changed = grid.set_wall(r, c) if wall else grid.clear_wall(r, c)
        if changed:
            self.canvas.paint_cell(node)
            self.app.discard_race()
            self._facts_soon()

    def move_endpoint(self, which: str, node: Node) -> None:
        grid = self.app.grid
        move = grid.move_start if which == "start" else grid.move_goal
        if move(*node):
            self.canvas.paint_cell(node)
            self.canvas.place_dots()
            self.app.discard_race()
            self._facts_soon()


class RunnersScreen(Screen):
    """Step 2: one card per algorithm with its switch and colour, the quick
    picks, and the guess to the goal."""

    def __init__(self, master: tk.Misc, app: App):
        super().__init__(master, app)
        self.nav(back=("←  Back: the maze", lambda: app.show("maze")),
                 forward=("Next: set the speed  →", lambda: app.show("speed")))
        self.heading(self, "Choose the runners",
                     "Switch on the algorithms that race, and give each one its colour.")

        cards = tk.Frame(self, bg=ui.BG)
        cards.pack(fill="x", pady=(14, 0))
        for col in range(3):
            cards.columnconfigure(col, weight=1, uniform="card")
        self.tags: dict[str, ui.Tag] = {}
        self.chips: dict[str, ui.ColorChips] = {}
        self.previews: dict[str, dict[str, tk.Label]] = {}
        for i, name in enumerate(ALGORITHMS):
            card = ui.Card(cards)
            card.grid(row=i // 3, column=i % 3, sticky="nsew", padx=6, pady=6)
            body = card.body
            head = tk.Frame(body, bg=ui.CARD)
            head.pack(fill="x")
            tag = ui.Tag(head, name, app.colors[name], self.fonts.chip)
            tag.pack(side="left")
            self.tags[name] = tag
            ui.Switch(head, app.selected[name], command=self.on_toggle).pack(side="right")
            tk.Label(body, text=TAGLINES[name][0].upper() + TAGLINES[name][1:] + ".",
                     bg=ui.CARD, fg=ui.MUTED, font=self.fonts.small, anchor="w",
                     wraplength=320).pack(fill="x", pady=(10, 0))
            ui.eyebrow(body, "Colour", self.fonts.eyebrow).pack(fill="x", pady=(14, 4))
            chips = ui.ColorChips(body, PALETTE, app.colors[name],
                                  on_pick=lambda c, n=name: self.set_color(n, c),
                                  on_more=lambda n=name: self.choose_color(n),
                                  font=self.fonts.bold)
            chips.pack(anchor="w")
            self.chips[name] = chips
            preview = tk.Frame(body, bg=ui.CARD)
            preview.pack(fill="x", pady=(12, 0))
            swatches: dict[str, tk.Label] = {}
            for key, caption in (("frontier", "found"), ("explored", "checked"),
                                 ("path", "path")):
                swatch = tk.Label(preview, width=3, bg=COLOR_PATH if key == "path" else ui.CARD)
                swatch.pack(side="left")
                tk.Label(preview, text=caption, bg=ui.CARD, fg=ui.MUTED,
                         font=self.fonts.small).pack(side="left", padx=(6, 14))
                swatches[key] = swatch
            self.previews[name] = swatches
            card.fit()

        below = tk.Frame(self, bg=ui.BG)
        below.pack(fill="x", pady=(16, 0))
        tk.Label(below, text="Quick picks", bg=ui.BG, fg=ui.TEXT,
                 font=self.fonts.bold).pack(side="left", padx=(0, 10))
        for label, names in QUICK_PICKS:
            self.button(below, label, lambda n=names: self.pick(n)).pack(side="left", padx=3)
        self.button(below, "Default colours", self.default_colors,
                    kind="ghost").pack(side="right")

        guess = tk.Frame(self, bg=ui.BG)
        guess.pack(fill="x", pady=(16, 0))
        tk.Label(guess, text="Guess to the goal", bg=ui.BG, fg=ui.TEXT,
                 font=self.fonts.bold).pack(side="left")
        ui.Segmented(guess, [(h, h) for h in HEURISTICS], app.heuristic,
                     command=self.on_heuristic, font=self.fonts.body).pack(side="left",
                                                                           padx=(12, 14))
        tk.Label(guess, text="used by A*, Greedy and Hill Climbing. Manhattan is the exact "
                             "distance when no wall is in the way, Euclidean the straight line, "
                             "Chebyshev the larger of rows and columns.",
                 bg=ui.BG, fg=ui.MUTED, font=self.fonts.small, anchor="w",
                 justify="left", wraplength=620).pack(side="left")

        self.summary = tk.Label(self, bg=ui.BG, fg=ui.TEXT, font=self.fonts.bold,
                                anchor="w", justify="left")
        self.summary.pack(fill="x", pady=(16, 0))

    def refresh(self) -> None:
        for name in ALGORITHMS:
            self.update_colors(name)
        self.update_summary()

    def update_colors(self, name: str) -> None:
        color = self.app.colors[name]
        self.tags[name].set_color(color)
        self.chips[name].set_current(color)
        self.previews[name]["frontier"].config(bg=frontier_shade(color))
        self.previews[name]["explored"].config(bg=explored_shade(color))

    def set_color(self, name: str, color: str) -> None:
        self.app.colors[name] = color
        self.update_colors(name)
        self.app.discard_race()
        self.update_summary()

    def choose_color(self, name: str) -> None:
        _rgb, chosen = colorchooser.askcolor(color=self.app.colors[name],
                                             title=f"Colour for {name}", parent=self.app.root)
        if chosen:
            self.set_color(name, chosen)

    def default_colors(self) -> None:
        for name, color in ALGO_COLORS.items():
            self.app.colors[name] = color
            self.update_colors(name)
        self.app.discard_race()
        self.update_summary()

    def pick(self, names: tuple[str, ...]) -> None:
        for name, var in self.app.selected.items():
            var.set(name in names)
        self.on_toggle()

    def on_toggle(self) -> None:
        self.app.discard_race()
        self.update_summary()

    def on_heuristic(self, _event=None) -> None:
        self.app.discard_race()
        self.update_summary()
        self.app.root.focus_set()

    def update_summary(self) -> None:
        names = self.app.chosen()
        if not names:
            text = "Switch on at least one runner."
        else:
            text = (f"{plural(len(names), 'runner')} in the race: {', '.join(names)}.   "
                    f"Guess to the goal: {self.app.heuristic.get()}.")
            by_color: dict[str, list[str]] = {}
            for name in names:
                by_color.setdefault(self.app.colors[name], []).append(name)
            shared = [group for group in by_color.values() if len(group) > 1]
            if shared:
                text += "   Note: " + "; ".join(" and ".join(g) for g in shared) + \
                        " have the same colour."
        self.summary.config(text=text)


class SpeedScreen(Screen):
    """Step 3: four speed presets as cards, a fine slider, the countdown and Big text."""

    def __init__(self, master: tk.Misc, app: App):
        super().__init__(master, app)
        self.nav(back=("←  Back: the runners", lambda: app.show("runners")),
                 forward=("Start the race  ▶", app.start_race))
        self.heading(self, "Set the speed",
                     "Every runner makes the same number of moves per tick, and a move is one "
                     "look at one cell. Pick how many.")
        self.preset = tk.IntVar(value=app.speed.get())
        cards = tk.Frame(self, bg=ui.BG)
        cards.pack(fill="x", pady=(14, 0))
        for col in range(len(SPEED_PRESETS)):
            cards.columnconfigure(col, weight=1, uniform="speed")
        self.cards: dict[int, tuple[ui.Card, tk.Canvas]] = {}
        for i, (label, value, desc) in enumerate(SPEED_PRESETS):
            card = ui.Card(cards, padx=18, pady=16)
            card.grid(row=0, column=i, sticky="nsew", padx=6, pady=6)
            body = card.body
            head = tk.Frame(body, bg=ui.CARD)
            head.pack(fill="x")
            tk.Label(head, text=label, bg=ui.CARD, fg=ui.TEXT, font=self.fonts.title,
                     anchor="w").pack(side="left")
            dot = tk.Canvas(head, width=20, height=20, bg=ui.CARD, highlightthickness=0)
            dot.pack(side="right")
            tk.Label(body, text=str(value), bg=ui.CARD, fg=ui.TEXT, font=self.fonts.number,
                     anchor="w").pack(fill="x", pady=(8, 0))
            tk.Label(body, text=f"{plural(value, 'move')} per tick   ·   "
                                f"about {value * 1000 // TICK_MS} a second",
                     bg=ui.CARD, fg=ui.MUTED, font=self.fonts.small, anchor="w").pack(fill="x")
            tk.Label(body, text=desc, bg=ui.CARD, fg=ui.MUTED, font=self.fonts.small,
                     anchor="w", justify="left", wraplength=250).pack(fill="x", pady=(10, 0))
            card.fit()
            for widget in ui.descendants(card):
                widget.bind("<Button-1>", lambda _e, v=value: self.choose(v))
                widget.configure(cursor="hand2")
            self.cards[value] = (card, dot)

        fine = tk.Frame(self, bg=ui.BG)
        fine.pack(fill="x", pady=(20, 0))
        self.eyebrow(fine, "Fine tune", pady=(0, 6))
        row = tk.Frame(fine, bg=ui.BG)
        row.pack(fill="x")
        ui.Slider(row, app.speed, 1, 60, command=self.on_scale, length=520).pack(side="left")
        self.readout = tk.Label(row, bg=ui.BG, fg=ui.TEXT, font=self.fonts.body, anchor="w")
        self.readout.pack(side="left", padx=(16, 0))

        options = tk.Frame(self, bg=ui.BG)
        options.pack(fill="x", pady=(22, 0))
        self.eyebrow(options, "Before the race", pady=(0, 8))
        ui.SwitchRow(options, "Count down from 3 before the runners set off", app.countdown,
                     font=self.fonts.body).pack(fill="x")
        ui.SwitchRow(options, "Big text, for a projector", app.big_text,
                     command=app.toggle_big_text, font=self.fonts.body,
                     sub="Every label and number grows by a third.",
                     sub_font=self.fonts.small).pack(fill="x", pady=(10, 0))
        tk.Label(self, text="The speed can also be changed while the race runs, with the "
                            "slider on the race screen.",
                 bg=ui.BG, fg=ui.FAINT, font=self.fonts.small,
                 anchor="w").pack(fill="x", pady=(22, 0))

    def refresh(self) -> None:
        self.sync()

    def choose(self, value: int) -> None:
        self.app.speed.set(value)
        self.sync()

    def on_scale(self, _value=None) -> None:
        self.sync()

    def sync(self) -> None:
        value = self.app.speed.get()
        self.preset.set(value if value in self.cards else 0)
        for preset, (card, dot) in self.cards.items():
            chosen = preset == value
            card.set_outline(ui.ACCENT if chosen else ui.BORDER, 2 if chosen else 1)
            dot.delete("all")
            dot.create_oval(2, 2, 18, 18, outline=ui.ACCENT if chosen else ui.BORDER_STRONG,
                            width=1.5)
            if chosen:
                dot.create_oval(6, 6, 14, 14, fill=ui.ACCENT, outline="")
        self.readout.config(text=f"{plural(value, 'move')} per tick, "
                                 f"about {value * 1000 // TICK_MS} moves a second.")


class RaceScreen(Screen):
    """Step 4: one panel per runner, the controls, and a banner that names the
    winner when the race is over."""

    def __init__(self, master: tk.Misc, app: App):
        super().__init__(master, app)
        top = tk.Frame(self, bg=ui.BG)
        top.pack(fill="x")
        self.title_label = tk.Label(top, font=self.fonts.title, bg=ui.BG, fg=ui.TEXT,
                                    anchor="w")
        self.title_label.pack(side="left")
        controls = tk.Frame(top, bg=ui.BG)
        controls.pack(side="right")
        self.run_button = self.button(controls, "❙❙  Pause", app.toggle_run, kind="primary",
                                      min_width=130)
        self.run_button.pack(side="left", padx=3)
        self.button(controls, "Step", app.step_once).pack(side="left", padx=3)
        self.button(controls, "Finish", app.finish_now).pack(side="left", padx=3)
        self.button(controls, "Race again", app.race_again).pack(side="left", padx=3)
        self.button(controls, "Set up again", lambda: app.show("maze"),
                    kind="ghost").pack(side="left", padx=(3, 18))
        tk.Label(controls, text="Speed", bg=ui.BG, fg=ui.MUTED,
                 font=self.fonts.body).pack(side="left")
        ui.Slider(controls, app.speed, 1, 60, length=170).pack(side="left", padx=(8, 0))

        bottom = tk.Frame(self, bg=ui.BG)
        bottom.pack(side="bottom", fill="x", pady=(8, 0))
        self.banner = tk.Label(bottom, textvariable=app.status_var, font=self.fonts.bold,
                               bg=ui.BG, fg=ui.TEXT, anchor="w")
        self.banner.pack(side="left", fill="x", expand=True)
        self.results_button = self.button(bottom, "See the results  →",
                                          lambda: app.show("results"), kind="primary",
                                          padx=22, pady=9)
        legend = tk.Frame(self, bg=ui.BG)
        legend.pack(side="bottom", fill="x", pady=(10, 0))
        for text, color in (("Start", COLOR_START), ("Goal", COLOR_GOAL),
                            ("Wall", COLOR_WALL), ("Final path", COLOR_PATH)):
            swatch = tk.Canvas(legend, width=12, height=12, bg=ui.BG, highlightthickness=0)
            swatch.create_oval(1, 1, 11, 11, fill=color,
                               outline=ui.BORDER_STRONG if color == COLOR_WALL else "")
            swatch.pack(side="left", padx=(0, 6))
            tk.Label(legend, text=text, bg=ui.BG, fg=ui.MUTED,
                     font=self.fonts.small).pack(side="left", padx=(0, 16))
        tk.Label(legend, text="A runner's full colour: found, not checked yet.   "
                              "Dimmer: checked.",
                 bg=ui.BG, fg=ui.FAINT, font=self.fonts.small).pack(side="left")

        self.panel_area = tk.Frame(self, bg=ui.BG)
        self.panel_area.pack(fill="both", expand=True, pady=(10, 0))
        self.panel_grid = tk.Frame(self.panel_area, bg=ui.BG)   # centred in the area
        self.panel_grid.pack(expand=True)
        self.panels: list[Panel] = []
        self.panel_by_name: dict[str, Panel] = {}
        self._size = (0, 0)
        self._overlay: tk.Label | None = None
        self._count_id: str | None = None

    # -- building --------------------------------------------------------------------

    def refresh(self) -> None:
        race = self.app.race
        if race is None:
            return
        self.title_label.config(
            text=f"{self.app.maze_name}   ·   {plural(len(race.runners), 'runner')}   ·   "
                 f"{self.app.heuristic.get()} guess")
        self.build_panels()
        self.show_finished(race.finished)

    def layout(self, count: int) -> tuple[int, int, bool]:
        """Columns of panels, the cell size that fits them in the panel area, and
        whether the panels are too narrow for the full two-line header."""
        root = self.app.root
        root.update_idletasks()
        w, h = self.panel_area.winfo_width(), self.panel_area.winfo_height()
        if w < 200 or h < 150:                       # not laid out yet: estimate
            w, h = root.winfo_width() - Sidebar.RAIL - 50, root.winfo_height() - 230
        line = self.fonts.body.metrics("linespace")
        tag = self.fonts.chip.metrics("linespace") + 6          # the name pill
        pad_w = 2 * ui.Card.INSET + 2 * Panel.PADX + 8          # card edges and grid padding
        pad_h = 2 * ui.Card.INSET + 2 * Panel.PADY + 8
        grid = self.app.grid
        best = None
        for columns in (1, 2, 3):
            rows = max(1, math.ceil(count / columns))

            def fits(header: int) -> int:
                return min(18, (w - columns * pad_w) // (columns * grid.cols),
                           (h - rows * (header + pad_h)) // (rows * grid.rows))

            cell = fits(tag + line + 10)             # name + tagline, counters below
            compact = cell < 11
            if compact:
                cell = fits(tag + 6)                 # name and counters on one line
            # Biggest cells win; then the fewest empty slots; then the wider layout.
            key = (cell, count - rows * columns, columns)
            if best is None or key > best[0]:
                best = (key, columns, max(4, cell), compact)
        return best[1], best[2], best[3]

    def build_panels(self) -> None:
        self.cancel_countdown()
        for widget in self.panel_grid.winfo_children():
            widget.destroy()
        self.panels = []
        self.panel_by_name = {}
        race = self.app.race
        if race is None:
            return
        columns, cell, compact = self.layout(len(race.runners))
        for i, runner in enumerate(race.runners):
            panel = Panel(self.panel_grid, self.app.grid, runner.name, runner.color, cell,
                          self.fonts, compact)
            panel.grid(row=i // columns, column=i % columns, padx=4, pady=4, sticky="n")
            panel.render(runner)
            self.panels.append(panel)
            self.panel_by_name[runner.name] = panel
        root = self.app.root
        self._size = (root.winfo_width(), root.winfo_height())
        self.refresh_stats()

    def relayout(self) -> None:
        root = self.app.root
        if self.app.race is not None and (root.winfo_width(), root.winfo_height()) != self._size:
            self.build_panels()

    # -- during the race -----------------------------------------------------------------

    def apply(self, runner: Runner, event: tuple) -> None:
        self.panel_by_name[runner.name].apply(event)

    def render_all(self) -> None:
        for runner in self.app.race.runners:
            self.panel_by_name[runner.name].render(runner)

    def refresh_stats(self) -> None:
        race = self.app.race
        if race is None:
            return
        for runner in race.runners:
            self.panel_by_name[runner.name].show_stats(runner, race)

    def show_finished(self, finished: bool) -> None:
        if finished:
            self.results_button.pack(side="right")
        else:
            self.results_button.pack_forget()

    # -- the countdown ------------------------------------------------------------------

    def countdown(self, then) -> None:
        """Show 3, 2, 1, Go! over the panels, then call ``then``."""
        self.cancel_countdown()
        self._overlay = tk.Label(self.panel_area, text="3", font=self.fonts.huge,
                                 bg=ui.BG, fg=ui.TEXT, padx=40, pady=10)
        self._overlay.place(relx=0.5, rely=0.5, anchor="center")
        self._count_step(["2", "1", "Go!"], then)

    def _count_step(self, rest: list[str], then) -> None:
        def advance() -> None:
            self._count_id = None
            if not rest:
                self.cancel_countdown()
                then()
                return
            if self._overlay is not None:
                self._overlay.config(text=rest[0])
            self._count_step(rest[1:], then)
        self._count_id = self.app.root.after(700, advance)

    def cancel_countdown(self) -> None:
        if self._count_id is not None:
            self.app.root.after_cancel(self._count_id)
            self._count_id = None
        if self._overlay is not None:
            self._overlay.destroy()
            self._overlay = None


class ResultsScreen(Screen):
    """Step 5: the winner, the awards, the full table and a chart."""

    COLUMNS = (   # id, heading, width, anchor; the headings are shown in capitals
        ("place", "Place", 60, "center"),
        ("algorithm", "Runner", 120, "w"),
        ("result", "Result", 170, "w"),
        ("moves", "Moves", 85, "e"),
        ("explored", "Cells checked", 115, "e"),
        ("path", "Path length", 100, "e"),
        ("optimal", "Shortest?", 95, "center"),
        ("started", "Started at", 105, "center"),
        ("finished", "Finished at", 105, "center"),
        ("race_time", "Time taken", 100, "e"),
        ("cpu", "Compute", 95, "e"),
    )
    AWARDS = ("Shortest path", "Fewest cells checked", "Quickest to compute", "Did not finish")

    def __init__(self, master: tk.Misc, app: App):
        super().__init__(master, app)
        self.nav(back=("←  Back to the race", lambda: app.show("race")),
                 forward=("Race again  ↻", app.race_again),
                 extra=(("Change the speed", lambda: app.show("speed")),
                        ("Change the runners", lambda: app.show("runners")),
                        ("Change the maze", lambda: app.show("maze"))))

        head = tk.Frame(self, bg=ui.BG)
        head.pack(fill="x")
        tk.Label(head, text="Race results", font=self.fonts.display, bg=ui.BG,
                 fg=ui.TEXT, anchor="w").pack(side="left")
        self.subtitle = tk.Label(head, font=self.fonts.body, bg=ui.BG, fg=ui.MUTED, anchor="e")
        self.subtitle.pack(side="right", anchor="s", pady=(0, 6))

        # One row of cards: the winner, two columns wide, then the four awards.
        top = tk.Frame(self, bg=ui.BG)
        top.pack(fill="x", pady=(12, 0))
        for col in range(6):
            top.columnconfigure(col, weight=1, uniform="top")
        self.winner_card = ui.Card(top, padx=20, pady=12)
        self.winner_card.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=(0, 6))
        body = self.winner_card.body
        head = tk.Frame(body, bg=ui.CARD)
        head.pack(fill="x")
        left = tk.Frame(head, bg=ui.CARD)
        left.pack(side="left", fill="x", expand=True)
        ui.eyebrow(left, "Winner", self.fonts.eyebrow).pack(anchor="w")
        self.winner = tk.Label(left, font=self.fonts.h1, bg=ui.CARD, fg=ui.TEXT, anchor="w")
        self.winner.pack(fill="x")
        right = tk.Frame(head, bg=ui.CARD)
        right.pack(side="right", anchor="n", padx=(16, 0))
        self.winner_moves = tk.Label(right, font=self.fonts.number, bg=ui.CARD, fg=ui.TEXT,
                                     anchor="e")
        self.winner_moves.pack(fill="x")
        self.winner_moves_caption = tk.Label(right, text="moves to the goal",
                                             font=self.fonts.small, bg=ui.CARD, fg=ui.MUTED,
                                             anchor="e")
        self.winner_moves_caption.pack(fill="x")
        self.winner_sub = tk.Label(body, font=self.fonts.body, fg=ui.MUTED, bg=ui.CARD,
                                   anchor="w", justify="left", wraplength=340)
        self.winner_sub.pack(fill="x", pady=(6, 0))

        self.awards: list[tuple[ui.Card, tk.Label, tk.Label]] = []
        for i, title in enumerate(self.AWARDS):
            card = ui.Card(top, padx=16, pady=10)
            card.grid(row=0, column=2 + i, sticky="nsew",
                      padx=(6, 0) if i == len(self.AWARDS) - 1 else 6)
            ui.eyebrow(card.body, title, self.fonts.eyebrow).pack(fill="x")
            who = tk.Label(card.body, bg=ui.CARD, fg=ui.TEXT, font=self.fonts.title,
                           anchor="w", justify="left", wraplength=170)
            who.pack(fill="x", pady=(2, 0))
            detail = tk.Label(card.body, bg=ui.CARD, fg=ui.MUTED, font=self.fonts.body,
                              anchor="w", justify="left", wraplength=170)
            detail.pack(fill="x")
            self.awards.append((card, who, detail))

        self.table_card = ui.Card(self, padx=2, pady=2)
        self.table_card.pack(fill="x", pady=(12, 0))
        ids = [c[0] for c in self.COLUMNS]
        self.board = ttk.Treeview(self.table_card.body, columns=ids, show="headings",
                                  height=len(ALGORITHMS), selectmode="none")
        for cid, heading, width, anchor in self.COLUMNS:
            self.board.heading(cid, text=heading.upper())
            self.board.column(cid, width=width, anchor=anchor, stretch=(cid == "result"))
        self.board.pack(fill="both", expand=True)

        self.eyebrow(self, "Cells checked, in finishing order", pady=(12, 2))
        self.chart = tk.Canvas(self, bg=ui.BG, highlightthickness=0, height=120)
        self.chart.pack(fill="x")

    def refresh(self) -> None:
        app = self.app
        race = app.race
        if race is None or not race.finished:
            return
        res = race.results()
        self.subtitle.config(
            text=f"{app.maze_name}   ·   {app.heuristic.get()} guess   ·   "
                 f"speed {app.speed.get()}   ·   started {fmt_clock(race.started_at)}")
        self.fit_text_to_cards()
        self.show_winner(res, race)
        self.show_awards(res, race)
        self.fill_table(res, race)
        self.draw_chart(res)

    def fit_text_to_cards(self) -> None:
        """Wrap the card texts to the width the cards actually have, which depends
        on the window and on the font size."""
        self.app.root.update_idletasks()
        inset = 2 * ui.Card.INSET
        width = self.winner_card.winfo_width() - inset - 40
        self.winner_sub.config(wraplength=max(160, width))
        for card, who, detail in self.awards:
            width = card.winfo_width() - inset - 32
            who.config(wraplength=max(80, width))
            detail.config(wraplength=max(80, width))

    def show_winner(self, res: Results, race: Race) -> None:
        if not res.winners:
            self.winner.config(text="No winner", fg=ui.TEXT)
            self.winner_sub.config(text="Nobody reached the goal.")
            self.winner_moves.config(text="–")
            self.winner_card.fit(width=False)
            return
        names = " and ".join(r.name for r in res.winners)
        first = res.winners[0]
        self.winner.config(text=names, fg=first.color if len(res.winners) == 1 else ui.TEXT)
        extra = first.path_length - (race.optimal_length or first.path_length)
        path = (f"Path of {first.path_length} steps, the shortest there is." if extra == 0
                else f"Path of {first.path_length} steps, {extra} longer than the shortest.")
        heat = "  A dead heat." if len(res.winners) > 1 else ""
        self.winner_sub.config(text=f"First to reach the goal.  {path}{heat}")
        self.winner_moves.config(text=str(res.winner_moves))
        self.winner_card.fit(width=False)

    def show_awards(self, res: Results, race: Race) -> None:
        (shortest, fewest, quickest, dnf) = self.awards
        if res.shortest:
            shortest[1].config(text=", ".join(r.name for r in res.shortest))
            shortest[2].config(text=f"{plural(race.optimal_length, 'step')} from start to goal")
        else:
            shortest[1].config(text="Nobody")
            shortest[2].config(text="")
        if res.fewest_checked is not None:
            fewest[1].config(text=res.fewest_checked.name)
            fewest[2].config(text=f"{plural(len(res.fewest_checked.explored), 'cell')} checked")
        else:
            fewest[1].config(text="Nobody")
            fewest[2].config(text="")
        if res.quickest_compute is not None:
            quickest[1].config(text=res.quickest_compute.name)
            quickest[2].config(text=f"{res.quickest_compute.compute_seconds * 1000:.2f} ms "
                                    "inside the algorithm")
        else:
            quickest[1].config(text="Nobody")
            quickest[2].config(text="")
        if res.did_not_finish:
            dnf[1].config(text=", ".join(r.name for r in res.did_not_finish))
            dnf[2].config(text="stuck at a local minimum" if race.optimal_length is not None
                          else "no path exists: the goal is sealed off")
        else:
            dnf[1].config(text="Everyone finished")
            dnf[2].config(text="")
        for card, _who, _detail in self.awards:
            card.fit(width=False)

    def fill_table(self, res: Results, race: Race) -> None:
        board = self.board
        board.delete(*board.get_children())
        board.configure(height=max(2, len(res.order)))
        board.tag_configure("stripe", background=ui.RAISED)
        for place, runner in enumerate(res.order, 1):
            board.tag_configure(runner.name, foreground=runner.color)
            tags = (runner.name, "stripe") if place % 2 == 0 else (runner.name,)
            board.insert("", "end", iid=runner.name, tags=tags,
                         values=self.row(place, runner, race))
        self.table_card.fit(width=False)

    @staticmethod
    def row(place: int, runner: Runner, race: Race) -> tuple:
        if runner.found:
            result = "reached the goal"
        elif runner.name == "Hill Climbing" and race.optimal_length is not None:
            result = "stuck at a local minimum"
        else:
            result = "no path exists"
        optimal = race.is_optimal(runner)
        if optimal is None:
            shortest = ""
        elif optimal:
            shortest = "yes"
        else:
            shortest = f"no, {runner.path_length - race.optimal_length} longer"
        return (
            str(place) if runner.found else "–",
            runner.name,
            result,
            runner.steps if runner.found else "",
            len(runner.explored),
            "" if runner.path_length is None else runner.path_length,
            shortest,
            fmt_clock(runner.started_at),
            fmt_clock(runner.finished_at),
            f"{runner.elapsed():.2f} s",
            f"{runner.compute_seconds * 1000:.2f} ms",
        )

    def draw_chart(self, res: Results) -> None:
        c = self.chart
        c.delete("all")
        c.update_idletasks()
        width = c.winfo_width()
        if width < 300:
            width = self.app.root.winfo_width() - Sidebar.WIDTH - 50
        runners = res.order
        row_h = self.fonts.body.metrics("linespace") + 10
        c.config(height=row_h * len(runners) + 4)
        most = max((len(r.explored) for r in runners), default=1) or 1
        left, right = 150, 320
        scale = (width - left - right) / most
        for i, runner in enumerate(runners):
            y = 2 + i * row_h
            c.create_text(left - 14, y + row_h / 2, text=runner.name, anchor="e",
                          font=self.fonts.bold, fill=runner.color)
            n = len(runner.explored)
            x1 = left + max(6, n * scale)
            ui.rounded(c, left, y + 4, x1, y + row_h - 4, 5, fill=runner.color)
            label = f"{plural(n, 'cell')} checked" + (
                f"   ·   path {runner.path_length} steps" if runner.found
                else "   ·   did not finish")
            c.create_text(x1 + 12, y + row_h / 2, text=label, anchor="w",
                          font=self.fonts.body, fill=ui.MUTED)


class App:
    """The window: the sidebar on the left and one screen showing at a time."""

    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("Maze Pathfinding Visualizer")
        root.configure(bg=ui.BG)
        root.minsize(1100, 680)
        self.fonts = Fonts()
        self.style = ttk.Style(root)
        self._apply_style()
        try:
            root.state("zoomed")      # fill the screen first, so the screens can be sized to it
        except tk.TclError:
            pass
        root.update_idletasks()
        if sys.platform == "win32":
            self._keep_awake()

        # The settings the setup screens edit.
        index = [t.name for t in TEMPLATES].index(DEFAULT_TEMPLATE)
        template = TEMPLATES[index]
        self.grid = template.build()
        self.maze_name = f"{index + 1}.  {template.name}"
        self.maze_note = template.note
        self.template_index: int | None = index
        self.selected = {name: tk.BooleanVar(value=True) for name in ALGORITHMS}
        self.colors = dict(ALGO_COLORS)
        self.heuristic = tk.StringVar(value="Manhattan")
        self.speed = tk.IntVar(value=4)
        self.countdown = tk.BooleanVar(value=True)
        self.big_text = tk.BooleanVar(value=False)

        # The race in progress, if any.
        self.race: Race | None = None
        self.running = False
        self.after_id: str | None = None
        self._ticks = 0
        self.status_var = tk.StringVar(value="")
        self.help_window: tk.Toplevel | None = None
        self._relayout_id: str | None = None
        self.current = ""

        self.sidebar = Sidebar(root, self)
        self.sidebar.pack(side="left", fill="y")
        tk.Frame(root, bg=ui.BORDER, width=1).pack(side="left", fill="y")
        container = tk.Frame(root, bg=ui.BG, padx=24, pady=20)
        container.pack(side="left", fill="both", expand=True)
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)
        self.screens: dict[str, Screen] = {
            "maze": MazeScreen(container, self),
            "runners": RunnersScreen(container, self),
            "speed": SpeedScreen(container, self),
            "race": RaceScreen(container, self),
            "results": ResultsScreen(container, self),
        }
        for screen in self.screens.values():
            screen.grid(row=0, column=0, sticky="nsew")
        self.show("maze")

        root.bind("<space>", lambda _e: self.on_race_screen(self.toggle_run))
        root.bind("<Right>", lambda _e: self.on_race_screen(self.step_once))
        root.bind("<Key-f>", lambda _e: self.on_race_screen(self.finish_now))
        root.bind("<Escape>", lambda _e: self.on_race_screen(self.pause))
        root.bind("<F1>", lambda _e: self.show_help())
        root.bind("<Configure>", self._on_configure)

    # -- looks -------------------------------------------------------------------------

    def _apply_style(self) -> None:
        """The few ttk widgets left (the table and the scrollbars) in the theme's colours."""
        s, f = self.style, self.fonts
        s.theme_use("clam")
        s.configure(".", background=ui.BG, foreground=ui.TEXT, font=f.body,
                    bordercolor=ui.BORDER, lightcolor=ui.BG, darkcolor=ui.BG,
                    troughcolor=ui.CARD, focuscolor=ui.BG)
        self.rowheight = f.body.metrics("linespace") + 8
        s.configure("Treeview", background=ui.CARD, fieldbackground=ui.CARD,
                    foreground=ui.TEXT, font=f.body, rowheight=self.rowheight,
                    borderwidth=0, relief="flat")
        s.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
        s.map("Treeview", background=[("selected", ui.SELECTED)],
              foreground=[("selected", ui.TEXT)])
        s.configure("Treeview.Heading", background=ui.RAISED, foreground=ui.MUTED,
                    font=f.label, relief="flat", borderwidth=0, padding=(8, 7))
        s.map("Treeview.Heading", background=[("active", ui.RAISED)],
              relief=[("pressed", "flat")])
        s.configure("Vertical.TScrollbar", background=ui.BORDER_STRONG, troughcolor=ui.CARD,
                    bordercolor=ui.CARD, arrowcolor=ui.MUTED, lightcolor=ui.BORDER_STRONG,
                    darkcolor=ui.BORDER_STRONG, arrowsize=12, relief="flat", gripcount=0)
        s.map("Vertical.TScrollbar", background=[("active", ui.FAINT), ("pressed", ui.FAINT)])

    def _keep_awake(self) -> None:
        """Windows only. Tk's event loop can oversleep after another program asks
        the window to paint itself (PrintWindow, which some screenshot tools use):
        its timers then stay silent until the next window message arrives, and a
        race in progress would freeze until the mouse moved. A helper thread posts
        a no-op message to the window twice a second, so a message always comes."""
        import ctypes
        import threading

        user32 = ctypes.windll.user32
        user32.GetAncestor.restype = ctypes.c_void_p
        user32.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
        user32.IsWindow.argtypes = [ctypes.c_void_p]
        user32.PostMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p,
                                        ctypes.c_void_p]
        hwnd = user32.GetAncestor(self.root.winfo_id(), 2)      # GA_ROOT: the frame window
        if not hwnd:
            return

        def nudge() -> None:
            while user32.IsWindow(hwnd):
                time.sleep(0.5)
                user32.PostMessageW(hwnd, 0, None, None)        # WM_NULL

        threading.Thread(target=nudge, name="tk-keep-awake", daemon=True).start()

    def toggle_big_text(self) -> None:
        self.fonts.scale(1.35 if self.big_text.get() else 1.0)
        ui.refit_all()
        self._apply_style()
        self.screens[self.current].refresh()

    # -- moving between screens ---------------------------------------------------------

    def chosen(self) -> list[str]:
        """The runners switched on on the Runners screen, in the fixed order."""
        return [name for name in ALGORITHMS if self.selected[name].get()]

    def show(self, name: str) -> None:
        if name == "race" and self.race is None:
            self.start_race()
            return
        if name == "results" and (self.race is None or not self.race.finished):
            return
        if self.current == "race" and name != "race" and self.running:
            self.pause()
        self.current = name
        self.sidebar.set_compact(name == "race")     # before the screen measures itself
        self.screens[name].refresh()
        self.screens[name].tkraise()
        self.sidebar.set_current(name, self.race is not None and self.race.finished)
        self.root.focus_set()

    def set_maze(self, grid: Grid, name: str, note: str, index: int | None) -> None:
        self.grid = grid
        self.maze_name = name
        self.maze_note = note
        self.template_index = index
        self.discard_race()
        if self.current == "maze":
            self.screens["maze"].refresh()

    def discard_race(self) -> None:
        """Forget the race: a setting changed, so it would no longer be fair."""
        self.pause()
        self.race = None
        self.status_var.set("")
        self.screens["race"].cancel_countdown()
        if self.current:
            self.sidebar.set_current(self.current, False)

    def on_race_screen(self, action) -> None:
        if self.current == "race" and self.race is not None:
            action()

    # -- running the race ----------------------------------------------------------------

    def start_race(self) -> None:
        """Build a race from the settings and go to the race screen."""
        names = self.chosen()
        if not names:
            self.show("runners")
            return
        self.discard_race()
        self.race = Race(self.grid, [(name, self.colors[name]) for name in names],
                         HEURISTICS[self.heuristic.get()])
        race_screen = self.screens["race"]
        race_screen.run_button.set_state("normal")
        race_screen.run_button.set_text("▶  Start")
        self.current = "race"
        self.sidebar.set_compact(True)
        race_screen.refresh()
        race_screen.tkraise()
        self.sidebar.set_current("race", False)
        self.root.focus_set()
        if self.countdown.get():
            self.status_var.set("Get ready…")
            race_screen.countdown(then=self.start)
        else:
            self.start()

    def race_again(self) -> None:
        self.start_race()

    def toggle_run(self) -> None:
        if self.running:
            self.pause()
        else:
            self.start()

    def start(self) -> None:
        race = self.race
        if race is None or race.finished or self.running:
            return
        self.screens["race"].cancel_countdown()
        if race.started_at is None:
            race.start()          # the clock starts when the runners set off
            self._ticks = 0
        race.resume()             # and runs again after a pause
        self.running = True
        self.screens["race"].run_button.set_text("❙❙  Pause")
        self.status_var.set("Racing.   Space pauses, Right arrow steps, F finishes.")
        self._schedule()

    def pause(self) -> None:
        self.running = False
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        race = self.race
        if race is None:
            return
        race.pause()              # paused time is not time taken
        self.refresh_stats()      # and the frozen numbers are shown exactly
        if not race.finished and race.started_at:
            self.screens["race"].run_button.set_text("▶  Resume")
            self.status_var.set("Paused.   Right arrow steps one move at a time.")

    def _schedule(self) -> None:
        self.after_id = self.root.after(TICK_MS, self.tick)

    def tick(self) -> None:
        self.after_id = None
        if not self.running or self.race is None:
            return
        self._advance(self.speed.get())
        self._ticks += 1
        if self.race.finished:
            self._finish()
            return
        if self._ticks % STATS_EVERY == 0:
            # Rewriting every counter 40 times a second is wasted work on a slow
            # classroom laptop; a few times a second reads the same to the eye.
            self.refresh_stats()
        self._schedule()

    def _advance(self, k: int) -> None:
        """Move every runner ``k`` events and paint them."""
        assert self.race is not None
        race_screen = self.screens["race"]
        for runner, event in self.race.step(k):
            race_screen.apply(runner, event)

    def step_once(self) -> None:
        if self.running:
            self.pause()
        race = self.race
        if race is None or race.finished:
            return
        self.screens["race"].cancel_countdown()
        if race.started_at is None:
            race.start()
            race.pause()          # stepping by hand costs no race time
        self._advance(1)
        if race.finished:
            self._finish()
        else:
            self.refresh_stats()  # a step by hand shows its numbers at once
            self.screens["race"].run_button.set_text("▶  Resume")

    def finish_now(self) -> None:
        race = self.race
        if race is None or race.finished:
            return
        self.pause()
        self.screens["race"].cancel_countdown()
        race.run_to_completion()
        self.screens["race"].render_all()
        self._finish()

    def _finish(self) -> None:
        self.running = False
        race = self.race
        assert race is not None
        race_screen = self.screens["race"]
        race_screen.run_button.set_text("Finished")
        race_screen.run_button.set_state("disabled")
        self.refresh_stats()      # always once, with the final numbers
        res = race.results()
        if res.winners:
            names = " and ".join(r.name for r in res.winners)
            self.status_var.set(f"Finished.   Winner: {names}, first to the goal after "
                                f"{plural(res.winner_moves, 'move')}.")
        else:
            self.status_var.set("Finished.   Nobody reached the goal.")
        race_screen.show_finished(True)
        self.sidebar.set_current(self.current, True)

    def refresh_stats(self) -> None:
        self.screens["race"].refresh_stats()

    # -- the window ------------------------------------------------------------------------

    def _on_configure(self, event: tk.Event) -> None:
        if event.widget is not self.root:
            return
        if self._relayout_id is not None:
            self.root.after_cancel(self._relayout_id)
        self._relayout_id = self.root.after(200, self._relayout)

    def _relayout(self) -> None:
        self._relayout_id = None
        if self.current:
            self.screens[self.current].relayout()

    # -- help ------------------------------------------------------------------------------

    def show_help(self) -> None:
        if self.help_window is not None and self.help_window.winfo_exists():
            self.help_window.lift()
            return
        win = tk.Toplevel(self.root)
        win.title("How it works")
        win.configure(bg=ui.BG)
        self.help_window = win
        frame = tk.Frame(win, bg=ui.BG, padx=14, pady=14)
        frame.pack(fill="both", expand=True)
        text = tk.Text(frame, wrap="word", width=90, height=34, font=self.fonts.body,
                       bg=ui.CARD, fg=ui.TEXT, relief="flat", bd=0, highlightthickness=0,
                       padx=24, pady=18, spacing2=2, spacing3=8, insertbackground=ui.TEXT,
                       selectbackground=ui.SELECTED, selectforeground=ui.TEXT)
        scroll = ttk.Scrollbar(frame, command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        text.tag_configure("h", font=self.fonts.title, spacing1=14, spacing3=4)
        for name, color in ALGO_COLORS.items():
            text.tag_configure(name, foreground=color, font=self.fonts.bold)
        for tag, chunk in HELP:
            text.insert("end", chunk, (tag,) if tag else ())
        text.configure(state="disabled")
        ui.Button(win, "Close", win.destroy, font=self.fonts.body).pack(pady=(0, 14))


def main() -> None:
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
