"""Maze Pathfinding Visualizer: the Tkinter app.

The app is a row of screens, like a setup wizard followed by the race:

    1  Maze      pick a ready-made maze, make a random one, or draw your own
    2  Runners   tick the algorithms that race, give each its colour, choose the guess
    3  Speed     moves per tick, a countdown, big text for a projector
    4  Race      every chosen algorithm solves the same maze at the same time
    5  Results   who won, the awards, the full table and a chart

The model (grid.py), the algorithms (algorithms.py) and the lockstep race
(race.py) have no Tkinter in them; this file is only the interface.

Run with ``python app.py``.
"""
from __future__ import annotations

import math
import random
import tkinter as tk
import tkinter.font as tkfont
from datetime import datetime
from tkinter import colorchooser, ttk

from algorithms import ALGORITHMS, HEURISTICS, bfs, run
from grid import Grid, Node
from maze_gen import generate
from race import Race, Results, Runner
from templates import TEMPLATES

TICK_MS = 25             # one animation tick; the speed setting is moves per tick
STATS_EVERY = 4          # ticks between counter refreshes: ten a second is plenty
DEFAULT_TEMPLATE = "Maze with some loops"

COLOR_WALL = "#1f2933"
COLOR_OPEN = "#f5f5f0"
COLOR_GRIDLINE = "#e2e0d8"
COLOR_START = "#2e9e4f"
COLOR_GOAL = "#d64545"
COLOR_PATH = "#ffc400"
COLOR_BG = "#eeece6"
COLOR_CARD = "#ffffff"
COLOR_TEXT = "#1f2933"
COLOR_MUTED = "#5b6470"
COLOR_TROUGH = "#d6d3ca"
COLOR_ACCENT = "#1f6feb"

# The colours the runners start with; the Runners screen can change them.
ALGO_COLORS = {
    "BFS": "#1f6feb",
    "DFS": "#8250df",
    "Dijkstra": "#0d9488",
    "A*": "#e8590c",
    "Greedy": "#d6336c",
    "Hill Climbing": "#4b5563",
}

# The colour chips offered for every runner. Gold is left out: it is the path.
PALETTE = ("#1f6feb", "#8250df", "#0d9488", "#e8590c", "#d6336c", "#4b5563",
           "#16a34a", "#dc2626", "#0891b2", "#9333ea", "#b45309", "#111827")

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

STEPS = (("maze", "Maze"), ("runners", "Runners"), ("speed", "Speed"),
         ("race", "Race"), ("results", "Results"))

HELP = (
    ("h", "How to use the Maze Pathfinding Visualizer\n"),
    ("", "The app is five screens, listed in the bar at the top.\n"
         "1  Maze: pick one of the 26 ready-made mazes, make a random one with as many loops "
         "as you like, or start from a blank canvas. Draw on the preview: left-drag paints "
         "walls, right-drag erases them, and the green start and red goal dots can be dragged.\n"
         "2  Runners: tick the algorithms that race, give each one its colour, and choose the "
         "guess to the goal that A*, Greedy and Hill Climbing use.\n"
         "3  Speed: how many moves every runner makes per tick, a countdown, and big text for "
         "a projector. Then press Start the race.\n"
         "4  Race: every runner solves the same maze at the same time, each in its own panel. "
         "Pause, Step one move at a time, Finish, change the speed, or race again.\n"
         "5  Results: who won, the awards, the full table with every time, and a chart of the "
         "cells each runner checked.\n"),
    ("h", "What the colours mean\n"),
    ("", "Green dot: the start.  Red dot: the goal.  Dark cells: walls.\n"
         "Strong shade of a runner's colour: cells it has found but not checked yet (its "
         "frontier).\n"
         "Light shade: cells it has already checked (explored).\n"
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
         "The cells it looks at are shown in the frontier colour, but it never returns to them.\n"),
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


def fmt_clock(moment: datetime | None) -> str:
    if moment is None:
        return ""
    return moment.strftime("%H:%M:%S.") + f"{moment.microsecond // 1000:03d}"


def plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


class Fonts:
    """Named fonts shared by every widget, so Big text can rescale them all at once."""

    SIZES = {"body": 10, "bold": 10, "small": 9, "title": 12, "chip": 11, "big": 18, "huge": 54}

    def __init__(self) -> None:
        self.body = tkfont.Font(family="Segoe UI", size=10)
        self.bold = tkfont.Font(family="Segoe UI", size=10, weight="bold")
        self.small = tkfont.Font(family="Segoe UI", size=9)
        self.title = tkfont.Font(family="Segoe UI", size=12, weight="bold")
        self.chip = tkfont.Font(family="Segoe UI", size=11, weight="bold")
        self.big = tkfont.Font(family="Segoe UI", size=18, weight="bold")
        self.huge = tkfont.Font(family="Segoe UI", size=54, weight="bold")

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


class Panel(ttk.Frame):
    """One runner's view on the race screen: a coloured name, a one-line
    description, live counters in plain words, and the maze canvas."""

    def __init__(self, master: tk.Misc, model: Grid, name: str, color: str,
                 cell: int, fonts: Fonts, compact: bool = False):
        super().__init__(master)
        self.name = name
        self.color = color
        self.compact = compact
        self.explored_color = blend(color, "#ffffff", 0.68)
        self.frontier_color = blend(color, "#ffffff", 0.22)

        head = tk.Frame(self, bg=COLOR_BG)
        head.pack(fill="x")
        tk.Label(head, text=name, fg="white", bg=color, font=fonts.chip,
                 padx=10, pady=1).pack(side="left")
        if compact:
            # Narrow panel: counters share the name line and the tagline is left out.
            self.stats = tk.Label(head, text="ready", bg=COLOR_BG, fg=COLOR_TEXT,
                                  font=fonts.small, anchor="e")
            self.stats.pack(side="right", fill="x", expand=True)
        else:
            tk.Label(head, text=TAGLINES[name], bg=COLOR_BG, fg=COLOR_MUTED,
                     font=fonts.small, anchor="w").pack(side="left", padx=(8, 0))
            self.stats = tk.Label(self, text="ready", bg=COLOR_BG, fg=COLOR_TEXT,
                                  font=fonts.body, anchor="w")
            self.stats.pack(fill="x", pady=(1, 2))

        self.canvas = GridCanvas(self, model, cell)
        self.canvas.pack(pady=(2, 0) if compact else 0)

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


class StepBar(tk.Frame):
    """The numbered steps across the top. The current one is highlighted, the
    others can be clicked, and Results is greyed out until a race has finished."""

    def __init__(self, master: tk.Misc, app: App):
        super().__init__(master, bg=COLOR_BG)
        self.items: dict[str, tuple[tk.Label, tk.Label]] = {}
        for i, (key, label) in enumerate(STEPS):
            cell = tk.Frame(self, bg=COLOR_BG, cursor="hand2")
            cell.pack(side="left")
            num = tk.Label(cell, text=str(i + 1), width=2, font=app.fonts.chip,
                           bg=COLOR_TROUGH, fg=COLOR_TEXT)
            num.pack(side="left")
            txt = tk.Label(cell, text=label, font=app.fonts.bold, bg=COLOR_BG,
                           fg=COLOR_MUTED, padx=6)
            txt.pack(side="left")
            for widget in (cell, num, txt):
                widget.bind("<Button-1>", lambda _e, k=key: app.show(k))
            if i < len(STEPS) - 1:
                tk.Label(self, text="›", font=app.fonts.title, bg=COLOR_BG,
                         fg=COLOR_MUTED, padx=8).pack(side="left")
            self.items[key] = (num, txt)

    def set_current(self, current: str, finished: bool) -> None:
        for key, (num, txt) in self.items.items():
            if key == current:
                num.config(bg=COLOR_ACCENT, fg="white")
                txt.config(fg=COLOR_TEXT)
            elif key == "results" and not finished:
                num.config(bg=COLOR_BG, fg=COLOR_TROUGH)
                txt.config(fg=COLOR_TROUGH)
            else:
                num.config(bg=COLOR_TROUGH, fg=COLOR_TEXT)
                txt.config(fg=COLOR_MUTED)


class Screen(ttk.Frame):
    """One screen of the app. ``refresh`` runs every time it is shown and
    ``relayout`` when the window changes size while it is showing."""

    def __init__(self, master: tk.Misc, app: App):
        super().__init__(master)
        self.app = app
        self.fonts = app.fonts

    def refresh(self) -> None:
        pass

    def relayout(self) -> None:
        pass

    def heading(self, parent: tk.Misc, text: str, sub: str | None = None,
                wrap: int = 960) -> None:
        tk.Label(parent, text=text, font=self.fonts.title, bg=COLOR_BG, fg=COLOR_TEXT,
                 anchor="w").pack(fill="x")
        if sub:
            tk.Label(parent, text=sub, font=self.fonts.body, bg=COLOR_BG, fg=COLOR_MUTED,
                     anchor="w", justify="left", wraplength=wrap).pack(fill="x", pady=(2, 0))

    def card(self, parent: tk.Misc, **kwargs) -> tk.Frame:
        return tk.Frame(parent, bg=COLOR_CARD, highlightbackground=COLOR_TROUGH,
                        highlightthickness=1, **kwargs)

    def nav(self, back: tuple | None = None, forward: tuple | None = None,
            accent: bool = False) -> ttk.Frame:
        """The bar of Back / Next buttons along the bottom of a screen."""
        bar = ttk.Frame(self)
        bar.pack(side="bottom", fill="x", pady=(10, 0))
        if back:
            ttk.Button(bar, text=back[0], command=back[1], takefocus=False).pack(side="left")
        if forward:
            ttk.Button(bar, text=forward[0], command=forward[1], takefocus=False,
                       style="Accent.TButton" if accent else "TButton").pack(side="right")
        return bar


class MazeScreen(Screen):
    """Step 1: the list of mazes on the left, an editable preview on the right."""

    def __init__(self, master: tk.Misc, app: App):
        super().__init__(master, app)
        self.nav(forward=("Next: choose the runners  ›", lambda: app.show("runners")))
        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)

        left = ttk.Frame(body, width=290)
        left.pack(side="left", fill="y", padx=(0, 18))
        left.pack_propagate(False)
        self.heading(left, "Choose a maze", "26 ready-made mazes, each built to make a point.",
                     wrap=270)
        lst = ttk.Frame(left)
        lst.pack(fill="both", expand=True, pady=(6, 0))
        self.listbox = tk.Listbox(lst, font=self.fonts.body, activestyle="none",
                                  exportselection=False, relief="flat", highlightthickness=1,
                                  highlightbackground=COLOR_TROUGH, bg=COLOR_CARD,
                                  fg=COLOR_TEXT, selectbackground=COLOR_ACCENT,
                                  selectforeground="white", takefocus=0)
        scroll = ttk.Scrollbar(lst, command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scroll.set)
        self.listbox.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        for i, t in enumerate(TEMPLATES):
            self.listbox.insert("end", f"{i + 1}.  {t.name}")
        self.listbox.bind("<<ListboxSelect>>", self.on_pick)

        tk.Label(left, text="Or make your own", font=self.fonts.bold, bg=COLOR_BG,
                 fg=COLOR_TEXT, anchor="w").pack(fill="x", pady=(12, 2))
        ttk.Button(left, text="Make a random maze", command=self.make_random,
                   takefocus=False).pack(fill="x")
        self.braid = tk.IntVar(value=15)
        app.slider(left, "Loops in the random maze", self.braid, 0, 60, "none", "many")
        ttk.Button(left, text="Start from a blank canvas", command=self.blank,
                   takefocus=False).pack(fill="x", pady=(10, 0))
        ttk.Button(left, text="Clear the walls of this maze", command=self.clear_walls,
                   takefocus=False).pack(fill="x", pady=(4, 0))

        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True)
        self.name_label = tk.Label(right, font=self.fonts.title, bg=COLOR_BG, fg=COLOR_TEXT,
                                   anchor="w")
        self.name_label.pack(fill="x")
        self.note_label = tk.Label(right, font=self.fonts.body, bg=COLOR_BG, fg=COLOR_MUTED,
                                   anchor="w", justify="left", wraplength=960)
        self.note_label.pack(fill="x", pady=(2, 6))
        self.holder = ttk.Frame(right)
        self.holder.pack(fill="both", expand=True)
        self.facts = tk.Label(right, font=self.fonts.bold, bg=COLOR_BG, fg=COLOR_TEXT,
                              anchor="w")
        self.facts.pack(fill="x", pady=(6, 0))
        tk.Label(right, text="Draw on the maze: left-drag paints walls, right-drag erases "
                             "them, and the green start and red goal dots can be dragged.",
                 font=self.fonts.small, bg=COLOR_BG, fg=COLOR_MUTED, anchor="w",
                 justify="left", wraplength=960).pack(fill="x")
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
        w, h = self.holder.winfo_width(), self.holder.winfo_height()
        if w < 100 or h < 100:                      # not laid out yet: estimate
            w, h = root.winfo_width() - 380, root.winfo_height() - 300
        grid = self.app.grid
        cell = max(4, min(22, (w - 10) // grid.cols, (h - 10) // grid.rows))
        for child in self.holder.winfo_children():
            child.destroy()
        self.canvas = GridCanvas(self.holder, grid, cell)
        self.canvas.pack(anchor="nw")
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
        reach = (f"shortest path {len(path) - 1} steps" if path
                 else "no path from the start to the goal")
        self.facts.config(text=f"{grid.cols} × {grid.rows} cells   ·   "
                               f"{plural(grid.wall_count, 'wall')}   ·   {reach}")

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
        self.nav(back=("‹  Back: the maze", lambda: app.show("maze")),
                 forward=("Next: set the speed  ›", lambda: app.show("speed")))
        self.heading(self, "Choose the runners",
                     "Tick the algorithms that race, and give each one its colour.")

        cards = ttk.Frame(self)
        cards.pack(fill="x", pady=(8, 0))
        for col in range(3):
            cards.columnconfigure(col, weight=1, uniform="card")
        self.headers: dict[str, tk.Label] = {}
        self.previews: dict[str, dict[str, tk.Label]] = {}
        for i, name in enumerate(ALGORITHMS):
            card = self.card(cards)
            card.grid(row=i // 3, column=i % 3, sticky="nsew", padx=5, pady=5)
            head = tk.Label(card, text=name, bg=app.colors[name], fg="white",
                            font=self.fonts.chip, anchor="w", padx=12, pady=4)
            head.pack(fill="x")
            self.headers[name] = head
            body = tk.Frame(card, bg=COLOR_CARD, padx=12, pady=8)
            body.pack(fill="x")
            tk.Checkbutton(body, text="Runs in this race", variable=app.selected[name],
                           command=self.on_toggle, bg=COLOR_CARD, activebackground=COLOR_CARD,
                           font=self.fonts.bold, anchor="w", takefocus=0).pack(fill="x")
            tk.Label(body, text=TAGLINES[name][0].upper() + TAGLINES[name][1:] + ".",
                     bg=COLOR_CARD, fg=COLOR_MUTED, font=self.fonts.small,
                     anchor="w").pack(fill="x")
            tk.Label(body, text="Colour", bg=COLOR_CARD, fg=COLOR_TEXT, font=self.fonts.small,
                     anchor="w").pack(fill="x", pady=(8, 2))
            chips = tk.Frame(body, bg=COLOR_CARD)
            chips.pack(fill="x")
            for color in PALETTE:
                chip = tk.Label(chips, bg=color, width=2, cursor="hand2")
                chip.pack(side="left", padx=(0, 3))
                chip.bind("<Button-1>", lambda _e, n=name, c=color: self.set_color(n, c))
            tk.Button(chips, text="more…", command=lambda n=name: self.choose_color(n),
                      font=self.fonts.small, relief="flat", bg=COLOR_CARD, fg=COLOR_ACCENT,
                      activebackground=COLOR_CARD, cursor="hand2", takefocus=0,
                      padx=4, pady=0).pack(side="left", padx=(6, 0))
            preview = tk.Frame(body, bg=COLOR_CARD)
            preview.pack(fill="x", pady=(8, 0))
            swatches: dict[str, tk.Label] = {}
            for key, caption in (("frontier", "found"), ("explored", "checked"), ("path", "path")):
                swatch = tk.Label(preview, width=3, bg=COLOR_PATH if key == "path" else COLOR_CARD)
                swatch.pack(side="left")
                tk.Label(preview, text=caption, bg=COLOR_CARD, fg=COLOR_MUTED,
                         font=self.fonts.small).pack(side="left", padx=(4, 12))
                swatches[key] = swatch
            self.previews[name] = swatches

        below = ttk.Frame(self)
        below.pack(fill="x", pady=(10, 0))
        tk.Label(below, text="Quick picks", bg=COLOR_BG, fg=COLOR_TEXT,
                 font=self.fonts.bold).pack(side="left", padx=(0, 8))
        for label, names in QUICK_PICKS:
            ttk.Button(below, text=label, command=lambda n=names: self.pick(n),
                       takefocus=False).pack(side="left", padx=2)
        ttk.Button(below, text="Default colours", command=self.default_colors,
                   takefocus=False).pack(side="right")

        guess = ttk.Frame(self)
        guess.pack(fill="x", pady=(12, 0))
        tk.Label(guess, text="Guess to the goal", bg=COLOR_BG, fg=COLOR_TEXT,
                 font=self.fonts.bold).pack(side="left")
        self.heuristic_box = ttk.Combobox(guess, state="readonly", font=self.fonts.body,
                                          takefocus=False, width=11, values=list(HEURISTICS),
                                          textvariable=app.heuristic)
        self.heuristic_box.pack(side="left", padx=(8, 10))
        self.heuristic_box.bind("<<ComboboxSelected>>", self.on_heuristic)
        tk.Label(guess, text="used by A*, Greedy and Hill Climbing. Manhattan is the exact "
                             "distance when no wall is in the way, Euclidean the straight line, "
                             "Chebyshev the larger of rows and columns.",
                 bg=COLOR_BG, fg=COLOR_MUTED, font=self.fonts.small, anchor="w",
                 justify="left").pack(side="left")

        self.summary = tk.Label(self, bg=COLOR_BG, fg=COLOR_TEXT, font=self.fonts.bold,
                                anchor="w", justify="left")
        self.summary.pack(fill="x", pady=(12, 0))

    def refresh(self) -> None:
        for name in ALGORITHMS:
            self.update_colors(name)
        self.update_summary()

    def update_colors(self, name: str) -> None:
        color = self.app.colors[name]
        self.headers[name].config(bg=color)
        self.previews[name]["frontier"].config(bg=blend(color, "#ffffff", 0.22))
        self.previews[name]["explored"].config(bg=blend(color, "#ffffff", 0.68))

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
            text = "Tick at least one runner."
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
    """Step 3: four speed presets, a fine slider, the countdown and Big text."""

    def __init__(self, master: tk.Misc, app: App):
        super().__init__(master, app)
        self.nav(back=("‹  Back: the runners", lambda: app.show("runners")),
                 forward=("Start the race  ▶", app.start_race), accent=True)
        self.heading(self, "Set the speed",
                     "Every runner makes the same number of moves per tick, and a move is one "
                     "look at one cell. Pick how many.")
        self.preset = tk.IntVar(value=app.speed.get())
        cards = ttk.Frame(self)
        cards.pack(fill="x", pady=(8, 0))
        for col in range(len(SPEED_PRESETS)):
            cards.columnconfigure(col, weight=1, uniform="speed")
        for i, (label, value, desc) in enumerate(SPEED_PRESETS):
            card = self.card(cards, padx=12, pady=10)
            card.grid(row=0, column=i, sticky="nsew", padx=5, pady=5)
            tk.Radiobutton(card, text=label, variable=self.preset, value=value,
                           command=lambda v=value: self.choose(v), bg=COLOR_CARD,
                           activebackground=COLOR_CARD, font=self.fonts.title, anchor="w",
                           takefocus=0).pack(fill="x")
            tk.Label(card, text=f"{plural(value, 'move')} per tick   ·   "
                                f"about {value * 1000 // TICK_MS} a second",
                     bg=COLOR_CARD, fg=COLOR_TEXT, font=self.fonts.body,
                     anchor="w").pack(fill="x")
            tk.Label(card, text=desc, bg=COLOR_CARD, fg=COLOR_MUTED, font=self.fonts.small,
                     anchor="w", justify="left", wraplength=280).pack(fill="x", pady=(4, 0))

        fine = ttk.Frame(self)
        fine.pack(fill="x", pady=(16, 0))
        tk.Label(fine, text="Fine tune", bg=COLOR_BG, fg=COLOR_TEXT,
                 font=self.fonts.bold, anchor="w").pack(fill="x")
        tk.Scale(fine, from_=1, to=60, orient="horizontal", variable=app.speed,
                 showvalue=False, command=self.on_scale, bg=COLOR_BG, highlightthickness=0,
                 takefocus=0, troughcolor=COLOR_TROUGH, sliderlength=18, bd=1,
                 length=520).pack(anchor="w")
        self.readout = tk.Label(fine, bg=COLOR_BG, fg=COLOR_TEXT, font=self.fonts.body,
                                anchor="w")
        self.readout.pack(fill="x")

        options = ttk.Frame(self)
        options.pack(fill="x", pady=(18, 0))
        tk.Label(options, text="Before the race", bg=COLOR_BG, fg=COLOR_TEXT,
                 font=self.fonts.bold, anchor="w").pack(fill="x")
        ttk.Checkbutton(options, text="Count down from 3 before the runners set off",
                        variable=app.countdown, takefocus=False).pack(anchor="w", pady=(4, 0))
        ttk.Checkbutton(options, text="Big text, for a projector", variable=app.big_text,
                        command=app.toggle_big_text, takefocus=False).pack(anchor="w",
                                                                           pady=(4, 0))
        tk.Label(self, text="The speed can also be changed while the race runs, with the "
                            "slider on the race screen.",
                 bg=COLOR_BG, fg=COLOR_MUTED, font=self.fonts.small,
                 anchor="w").pack(fill="x", pady=(18, 0))

    def refresh(self) -> None:
        self.sync()

    def choose(self, value: int) -> None:
        self.app.speed.set(value)
        self.sync()

    def on_scale(self, _value=None) -> None:
        self.sync()

    def sync(self) -> None:
        value = self.app.speed.get()
        self.preset.set(value if value in {p[1] for p in SPEED_PRESETS} else 0)
        self.readout.config(text=f"{plural(value, 'move')} per tick, "
                                 f"about {value * 1000 // TICK_MS} moves a second.")


class RaceScreen(Screen):
    """Step 4: one panel per runner, the controls, and a banner that names the
    winner when the race is over."""

    def __init__(self, master: tk.Misc, app: App):
        super().__init__(master, app)
        top = ttk.Frame(self)
        top.pack(fill="x")
        self.title_label = tk.Label(top, font=self.fonts.title, bg=COLOR_BG, fg=COLOR_TEXT,
                                    anchor="w")
        self.title_label.pack(side="left")
        controls = ttk.Frame(top)
        controls.pack(side="right")
        self.run_button = ttk.Button(controls, text="❙❙  Pause", style="Accent.TButton",
                                     command=app.toggle_run, takefocus=False, width=11)
        self.run_button.pack(side="left", padx=2)
        ttk.Button(controls, text="Step", command=app.step_once,
                   takefocus=False).pack(side="left", padx=2)
        ttk.Button(controls, text="Finish", command=app.finish_now,
                   takefocus=False).pack(side="left", padx=2)
        ttk.Button(controls, text="Race again", command=app.race_again,
                   takefocus=False).pack(side="left", padx=2)
        ttk.Button(controls, text="Set up again", command=lambda: app.show("maze"),
                   takefocus=False).pack(side="left", padx=(2, 16))
        tk.Label(controls, text="Speed", bg=COLOR_BG, fg=COLOR_TEXT,
                 font=self.fonts.body).pack(side="left")
        tk.Scale(controls, from_=1, to=60, orient="horizontal", variable=app.speed,
                 showvalue=False, bg=COLOR_BG, highlightthickness=0, takefocus=0,
                 troughcolor=COLOR_TROUGH, sliderlength=16, bd=1,
                 length=150).pack(side="left", padx=(6, 0))

        bottom = ttk.Frame(self)
        bottom.pack(side="bottom", fill="x", pady=(6, 0))
        self.banner = tk.Label(bottom, textvariable=app.status_var, font=self.fonts.bold,
                               bg=COLOR_BG, fg=COLOR_TEXT, anchor="w")
        self.banner.pack(side="left", fill="x", expand=True)
        self.results_button = ttk.Button(bottom, text="See the results  ›",
                                         style="Accent.TButton", takefocus=False,
                                         command=lambda: app.show("results"))
        legend = ttk.Frame(self)
        legend.pack(side="bottom", fill="x", pady=(6, 0))
        for text, color in (("Start", COLOR_START), ("Goal", COLOR_GOAL),
                            ("Wall", COLOR_WALL), ("Final path", COLOR_PATH)):
            tk.Label(legend, bg=color, width=2).pack(side="left", padx=(0, 4))
            tk.Label(legend, text=text, bg=COLOR_BG, fg=COLOR_TEXT,
                     font=self.fonts.small).pack(side="left", padx=(0, 16))
        tk.Label(legend, text="Strong shade of a runner's colour: found, not checked yet.   "
                              "Light shade: checked.",
                 bg=COLOR_BG, fg=COLOR_MUTED, font=self.fonts.small).pack(side="left")

        self.panel_area = ttk.Frame(self)
        self.panel_area.pack(fill="both", expand=True, pady=(8, 0))
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
            w, h = root.winfo_width() - 40, root.winfo_height() - 230
        line = self.fonts.body.metrics("linespace")
        chip = self.fonts.chip.metrics("linespace")
        grid = self.app.grid
        best = None
        for columns in (1, 2, 3):
            rows = max(1, math.ceil(count / columns))

            def fits(header: int) -> int:
                return min(18, (w - columns * 12) // (columns * grid.cols),
                           (h - rows * (header + 12)) // (rows * grid.rows))

            cell = fits(chip + line + 14)            # name + tagline, counters below
            compact = cell < 11
            if compact:
                cell = fits(chip + 12)               # name and counters on one line
            # Biggest cells win; then the fewest empty slots; then the wider layout.
            key = (cell, count - rows * columns, columns)
            if best is None or key > best[0]:
                best = (key, columns, max(4, cell), compact)
        return best[1], best[2], best[3]

    def build_panels(self) -> None:
        self.cancel_countdown()
        for widget in self.panel_area.winfo_children():
            widget.destroy()
        self.panels = []
        self.panel_by_name = {}
        race = self.app.race
        if race is None:
            return
        columns, cell, compact = self.layout(len(race.runners))
        for col in range(3):
            self.panel_area.columnconfigure(col, weight=1 if col < columns else 0)
        for i, runner in enumerate(race.runners):
            panel = Panel(self.panel_area, self.app.grid, runner.name, runner.color, cell,
                          self.fonts, compact)
            panel.grid(row=i // columns, column=i % columns, padx=5, pady=5, sticky="n")
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
                                 bg=COLOR_BG, fg=COLOR_TEXT, padx=40, pady=10)
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

    COLUMNS = (
        ("place", "Place", 60, "center"),
        ("algorithm", "Runner", 120, "w"),
        ("result", "Result", 170, "w"),
        ("moves", "Moves to finish", 110, "e"),
        ("explored", "Cells checked", 100, "e"),
        ("path", "Path length", 90, "e"),
        ("optimal", "Shortest path?", 110, "center"),
        ("started", "Started at", 100, "center"),
        ("finished", "Finished at", 100, "center"),
        ("race_time", "Time taken", 90, "e"),
        ("cpu", "Compute time", 100, "e"),
    )
    AWARDS = ("Shortest path", "Fewest cells checked", "Quickest to compute", "Did not finish")

    def __init__(self, master: tk.Misc, app: App):
        super().__init__(master, app)
        bar = ttk.Frame(self)
        bar.pack(side="bottom", fill="x", pady=(10, 0))
        ttk.Button(bar, text="‹  Back to the race", command=lambda: app.show("race"),
                   takefocus=False).pack(side="left")
        ttk.Button(bar, text="Race again  ↻", style="Accent.TButton", command=app.race_again,
                   takefocus=False).pack(side="right", padx=(8, 0))
        for label, screen in (("Change the speed", "speed"), ("Change the runners", "runners"),
                              ("Change the maze", "maze")):
            ttk.Button(bar, text=label, command=lambda s=screen: app.show(s),
                       takefocus=False).pack(side="right", padx=2)

        head = ttk.Frame(self)
        head.pack(fill="x")
        tk.Label(head, text="Race results", font=self.fonts.title, bg=COLOR_BG,
                 fg=COLOR_TEXT, anchor="w").pack(side="left")
        self.subtitle = tk.Label(head, font=self.fonts.body, bg=COLOR_BG, fg=COLOR_MUTED,
                                 anchor="e")
        self.subtitle.pack(side="right")

        self.winner = tk.Label(self, font=self.fonts.big, fg="white", bg=COLOR_TEXT,
                               anchor="w", padx=16, pady=8)
        self.winner.pack(fill="x", pady=(8, 0))
        self.winner_sub = tk.Label(self, font=self.fonts.body, fg=COLOR_TEXT, bg=COLOR_CARD,
                                   anchor="w", padx=16, pady=6)
        self.winner_sub.pack(fill="x")

        awards = ttk.Frame(self)
        awards.pack(fill="x", pady=(10, 0))
        self.awards: list[tuple[tk.Label, tk.Label]] = []
        for i, title in enumerate(self.AWARDS):
            awards.columnconfigure(i, weight=1, uniform="award")
            card = self.card(awards, padx=12, pady=8)
            card.grid(row=0, column=i, sticky="nsew", padx=5)
            tk.Label(card, text=title, bg=COLOR_CARD, fg=COLOR_MUTED, font=self.fonts.small,
                     anchor="w").pack(fill="x")
            who = tk.Label(card, bg=COLOR_CARD, fg=COLOR_TEXT, font=self.fonts.title,
                           anchor="w", justify="left", wraplength=320)
            who.pack(fill="x")
            detail = tk.Label(card, bg=COLOR_CARD, fg=COLOR_TEXT, font=self.fonts.body,
                              anchor="w", justify="left", wraplength=320)
            detail.pack(fill="x")
            self.awards.append((who, detail))

        ids = [c[0] for c in self.COLUMNS]
        self.board = ttk.Treeview(self, columns=ids, show="headings",
                                  height=len(ALGORITHMS), selectmode="none")
        for cid, heading, width, anchor in self.COLUMNS:
            self.board.heading(cid, text=heading)
            self.board.column(cid, width=width, anchor=anchor, stretch=(cid == "result"))
        self.board.pack(fill="x", pady=(12, 0))

        tk.Label(self, text="Cells checked, in finishing order", bg=COLOR_BG, fg=COLOR_TEXT,
                 font=self.fonts.bold, anchor="w").pack(fill="x", pady=(12, 2))
        self.chart = tk.Canvas(self, bg=COLOR_BG, highlightthickness=0, height=120)
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
        self.show_winner(res, race)
        self.show_awards(res, race)
        self.fill_table(res, race)
        self.draw_chart(res)

    def show_winner(self, res: Results, race: Race) -> None:
        if not res.winners:
            self.winner.config(text="No winner", bg=COLOR_TEXT)
            self.winner_sub.config(text="Nobody reached the goal.")
            return
        names = " and ".join(r.name for r in res.winners)
        first = res.winners[0]
        self.winner.config(text=f"Winner: {names}",
                           bg=first.color if len(res.winners) == 1 else COLOR_TEXT)
        extra = first.path_length - (race.optimal_length or first.path_length)
        path = (f"a path of {first.path_length} steps, the shortest there is." if extra == 0
                else f"a path of {first.path_length} steps, {extra} longer than the shortest.")
        heat = "  A dead heat." if len(res.winners) > 1 else ""
        self.winner_sub.config(
            text=f"First to reach the goal, after {plural(res.winner_moves, 'move')}, "
                 f"with {path}{heat}")

    def show_awards(self, res: Results, race: Race) -> None:
        (shortest, fewest, quickest, dnf) = self.awards
        if res.shortest:
            shortest[0].config(text=", ".join(r.name for r in res.shortest))
            shortest[1].config(text=f"{plural(race.optimal_length, 'step')} from start to goal")
        else:
            shortest[0].config(text="Nobody")
            shortest[1].config(text="")
        if res.fewest_checked is not None:
            fewest[0].config(text=res.fewest_checked.name)
            fewest[1].config(text=f"{plural(len(res.fewest_checked.explored), 'cell')} checked")
        else:
            fewest[0].config(text="Nobody")
            fewest[1].config(text="")
        if res.quickest_compute is not None:
            quickest[0].config(text=res.quickest_compute.name)
            quickest[1].config(text=f"{res.quickest_compute.compute_seconds * 1000:.2f} ms "
                                    "inside the algorithm")
        else:
            quickest[0].config(text="Nobody")
            quickest[1].config(text="")
        if res.did_not_finish:
            dnf[0].config(text=", ".join(r.name for r in res.did_not_finish))
            dnf[1].config(text="stuck at a local minimum" if race.optimal_length is not None
                          else "no path exists: the goal is sealed off")
        else:
            dnf[0].config(text="Everyone finished")
            dnf[1].config(text="")

    def fill_table(self, res: Results, race: Race) -> None:
        board = self.board
        board.delete(*board.get_children())
        board.configure(height=max(2, len(res.order)))
        for place, runner in enumerate(res.order, 1):
            board.tag_configure(runner.name, foreground=runner.color)
            board.insert("", "end", iid=runner.name, tags=(runner.name,),
                         values=self.row(place, runner, race))

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
            width = self.app.root.winfo_width() - 60
        runners = res.order
        row_h = self.fonts.body.metrics("linespace") + 12
        c.config(height=row_h * len(runners) + 4)
        most = max((len(r.explored) for r in runners), default=1) or 1
        left, right = 140, 300
        scale = (width - left - right) / most
        for i, runner in enumerate(runners):
            y = 2 + i * row_h
            c.create_text(left - 12, y + row_h / 2, text=runner.name, anchor="e",
                          font=self.fonts.bold, fill=runner.color)
            n = len(runner.explored)
            x1 = left + n * scale
            c.create_rectangle(left, y + 4, x1, y + row_h - 4, fill=runner.color, outline="")
            label = f"{plural(n, 'cell')} checked" + (
                f"   ·   path {runner.path_length} steps" if runner.found
                else "   ·   did not finish")
            c.create_text(x1 + 10, y + row_h / 2, text=label, anchor="w",
                          font=self.fonts.body, fill=COLOR_TEXT)


class App:
    """The window: a step bar across the top and one screen showing at a time."""

    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("Maze Pathfinding Visualizer")
        root.configure(bg=COLOR_BG)
        root.minsize(960, 620)
        self.fonts = Fonts()
        self.style = ttk.Style(root)
        root.option_add("*TCombobox*Listbox.font", self.fonts.body)
        self._apply_style()
        try:
            root.state("zoomed")      # fill the screen first, so the screens can be sized to it
        except tk.TclError:
            pass
        root.update_idletasks()

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

        header = tk.Frame(root, bg=COLOR_BG)
        header.pack(fill="x", padx=16, pady=(10, 0))
        tk.Label(header, text="Maze Pathfinding Visualizer", font=self.fonts.title,
                 bg=COLOR_BG, fg=COLOR_TEXT).pack(side="left")
        self.stepbar = StepBar(header, self)
        self.stepbar.pack(side="left", padx=(36, 0))
        ttk.Button(header, text="How it works  (F1)", command=self.show_help,
                   takefocus=False).pack(side="right")

        container = ttk.Frame(root, padding=(16, 10, 16, 12))
        container.pack(fill="both", expand=True)
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
        s, f = self.style, self.fonts
        s.configure("TFrame", background=COLOR_BG)
        s.configure("TLabel", background=COLOR_BG, foreground=COLOR_TEXT, font=f.body)
        s.configure("TCheckbutton", background=COLOR_BG, font=f.body)
        s.configure("TButton", font=f.body)
        s.configure("Accent.TButton", font=f.bold)
        s.configure("TCombobox", font=f.body)
        self.rowheight = f.body.metrics("linespace") + 6
        s.configure("Treeview", font=f.body, rowheight=self.rowheight)
        s.configure("Treeview.Heading", font=f.bold)

    def toggle_big_text(self) -> None:
        self.fonts.scale(1.35 if self.big_text.get() else 1.0)
        self._apply_style()
        self.screens[self.current].refresh()

    def slider(self, parent: tk.Misc, title: str, var: tk.IntVar, lo: int, hi: int,
               left: str, right: str) -> None:
        tk.Label(parent, text=title, bg=COLOR_BG, fg=COLOR_TEXT, font=self.fonts.body,
                 anchor="w").pack(fill="x", pady=(8, 0))
        tk.Scale(parent, from_=lo, to=hi, orient="horizontal", variable=var,
                 showvalue=False, bg=COLOR_BG, highlightthickness=0, takefocus=0,
                 troughcolor=COLOR_TROUGH, sliderlength=18, bd=1).pack(fill="x")
        ends = tk.Frame(parent, bg=COLOR_BG)
        ends.pack(fill="x")
        tk.Label(ends, text=left, bg=COLOR_BG, fg=COLOR_MUTED,
                 font=self.fonts.small).pack(side="left")
        tk.Label(ends, text=right, bg=COLOR_BG, fg=COLOR_MUTED,
                 font=self.fonts.small).pack(side="right")

    # -- moving between screens ---------------------------------------------------------

    def chosen(self) -> list[str]:
        """The runners ticked on the Runners screen, in the fixed order."""
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
        self.screens[name].refresh()
        self.screens[name].tkraise()
        self.stepbar.set_current(name, self.race is not None and self.race.finished)
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
            self.stepbar.set_current(self.current, False)

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
        race_screen.run_button.state(["!disabled"])
        race_screen.run_button.config(text="▶  Start")
        self.current = "race"
        race_screen.refresh()
        race_screen.tkraise()
        self.stepbar.set_current("race", False)
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
        self.screens["race"].run_button.config(text="❙❙  Pause")
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
            self.screens["race"].run_button.config(text="▶  Resume")
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
            self.screens["race"].run_button.config(text="▶  Resume")

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
        race_screen.run_button.config(text="Finished")
        race_screen.run_button.state(["disabled"])
        self.refresh_stats()      # always once, with the final numbers
        res = race.results()
        if res.winners:
            names = " and ".join(r.name for r in res.winners)
            self.status_var.set(f"Finished.   Winner: {names}, first to the goal after "
                                f"{plural(res.winner_moves, 'move')}.")
        else:
            self.status_var.set("Finished.   Nobody reached the goal.")
        race_screen.show_finished(True)
        self.stepbar.set_current(self.current, True)

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
        win.configure(bg=COLOR_BG)
        self.help_window = win
        frame = ttk.Frame(win, padding=10)
        frame.pack(fill="both", expand=True)
        text = tk.Text(frame, wrap="word", width=90, height=34, font=self.fonts.body,
                       bg="white", fg=COLOR_TEXT, relief="flat", padx=20, pady=14,
                       spacing2=2, spacing3=8)
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
        ttk.Button(win, text="Close", command=win.destroy).pack(pady=(0, 10))


def main() -> None:
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
