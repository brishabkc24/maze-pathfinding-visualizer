"""Maze Pathfinding Visualizer: the Tkinter app.

Three steps: choose a maze, choose the algorithms, press Start. Every chosen
algorithm solves the same maze at the same time, each in its own panel and
colour, and the scoreboard records what each one did and when. It is meant
for showing search algorithms to a class, so everything is labelled in plain
words and a "How it works" window explains the rest.

Run with ``python app.py``.
"""
from __future__ import annotations

import math
import random
import tkinter as tk
import tkinter.font as tkfont
from datetime import datetime
from tkinter import ttk

from algorithms import ALGORITHMS, HEURISTICS
from grid import Grid, Node
from maze_gen import generate
from race import Race, Runner
from templates import TEMPLATES

TICK_MS = 25             # one animation tick; the speed slider sets events per tick
STATS_EVERY = 4          # ticks between scoreboard refreshes: ten a second is plenty
SIDEBAR_WIDTH = 284
DEFAULT_TEMPLATE = "Maze with some loops"

COLOR_WALL = "#1f2933"
COLOR_OPEN = "#f5f5f0"
COLOR_GRIDLINE = "#e2e0d8"
COLOR_START = "#2e9e4f"
COLOR_GOAL = "#d64545"
COLOR_PATH = "#ffc400"
COLOR_BG = "#eeece6"
COLOR_TEXT = "#1f2933"
COLOR_MUTED = "#5b6470"
COLOR_TROUGH = "#d6d3ca"

ALGO_COLORS = {
    "BFS": "#1f6feb",
    "DFS": "#8250df",
    "Dijkstra": "#0d9488",
    "A*": "#e8590c",
    "Greedy": "#d6336c",
    "Hill Climbing": "#4b5563",
}

# One line under each panel name, in plain words.
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

HELP = (
    ("h", "How to use the Maze Pathfinding Visualizer\n"),
    ("", "1. Choose a maze from the list, or press Make a random maze.\n"
         "2. Tick the algorithms you want to compare. The quick picks set up common comparisons.\n"
         "3. Press Start. Every algorithm makes the same number of moves per tick, so the "
         "comparison is fair. A move is one look at one cell: finding a new cell (adding it to "
         "the frontier) or checking one (taking it off). An algorithm that finds four "
         "neighbours at once therefore spends more moves on a cell than Hill Climbing, which "
         "looks at a few and keeps none. Step moves everyone one move; Finish jumps to the "
         "end; Reset clears the panels so you can run again.\n"
         "Before a race you can draw your own walls: left-drag paints, right-drag erases, and "
         "the green and red dots can be dragged to new cells.\n"),
    ("h", "What the colours mean\n"),
    ("", "Green dot: the start.  Red dot: the goal.  Dark cells: walls.\n"
         "Strong colour: cells the algorithm has found but not checked yet (its frontier).\n"
         "Light colour: cells it has already checked (explored).\n"
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
         "the goal (the guess chosen in step 2). The guess never overestimates, so the path "
         "is still the shortest, and far fewer cells are checked.\n"),
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
         "the box in step 2 chooses it. Manhattan counts rows plus columns, which is the exact "
         "distance when no walls are in the way. Euclidean is the straight-line distance. "
         "Chebyshev is the larger of the rows and the columns. None of them ever overestimates, "
         "so A* finds the shortest path with any of them, but Manhattan is the closest guess on "
         "this grid, so A* checks the fewest cells with it. Try one maze with each guess: Greedy "
         "takes different routes, and with Chebyshev even the empty room stops Hill Climbing, "
         "because a step that shortens only the smaller of the two distances does not count as "
         "closer.\n"),
    ("h", "The scoreboard\n"),
    ("", "Cells checked: how many cells the algorithm expanded.  Path length: steps from start "
         "to goal.  Shortest path?: compared with the BFS path.  Started at and Finished at: "
         "clock times.  Time taken: from pressing Start to finishing, which depends on the "
         "speed slider.  Compute time: time spent inside the algorithm itself, without the "
         "drawing.\n"),
    ("h", "Keyboard\n"),
    ("", "Space: start or pause.  Right arrow: one step.  F: finish now.  Esc: reset.  "
         "F1: this window.\n"),
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


class Fonts:
    """Named fonts shared by every widget, so Big text can rescale them all at once."""

    SIZES = {"body": 10, "bold": 10, "small": 9, "title": 12, "chip": 11}

    def __init__(self) -> None:
        self.body = tkfont.Font(family="Segoe UI", size=10)
        self.bold = tkfont.Font(family="Segoe UI", size=10, weight="bold")
        self.small = tkfont.Font(family="Segoe UI", size=9)
        self.title = tkfont.Font(family="Segoe UI", size=12, weight="bold")
        self.chip = tkfont.Font(family="Segoe UI", size=11, weight="bold")

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
    """One algorithm's view: a coloured name, a one-line description, live
    counters in plain words, and the maze canvas."""

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
        """Paint a runner's whole state at once (after an instant finish)."""
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

    def reset(self) -> None:
        self.canvas.redraw()
        self.stats.config(text="ready")


class App:
    """The window: a three-step sidebar, one panel per racing algorithm, and
    the scoreboard."""

    COLUMNS = (
        ("algorithm", "Algorithm", 120, "w"),
        ("result", "Result", 180, "w"),
        ("explored", "Cells checked", 100, "e"),
        ("path", "Path length", 90, "e"),
        ("optimal", "Shortest path?", 110, "center"),
        ("started", "Started at", 100, "center"),
        ("finished", "Finished at", 100, "center"),
        ("race_time", "Time taken", 90, "e"),
        ("cpu", "Compute time", 100, "e"),
    )

    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("Maze Pathfinding Visualizer")
        root.configure(bg=COLOR_BG)
        self.fonts = Fonts()
        self.style = ttk.Style(root)
        root.option_add("*TCombobox*Listbox.font", self.fonts.body)
        self._apply_style()
        try:
            root.state("zoomed")      # fill the screen first, so the panels can be sized to it
        except tk.TclError:
            pass
        root.update_idletasks()

        self.grid = next(t for t in TEMPLATES if t.name == DEFAULT_TEMPLATE).build()
        self.race: Race | None = None
        self.running = False
        self.after_id: str | None = None
        self.panels: list[Panel] = []
        self.panel_by_name: dict[str, Panel] = {}
        self.drag: str | None = None
        self.help_window: tk.Toplevel | None = None
        self._laid_out_size = (0, 0)      # window size the panels were last built for
        self._relayout_id: str | None = None
        self._ticks = 0

        self.note_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready. Choose a maze and press Start.")
        self.summary_var = tk.StringVar(value="")
        self.selected = {name: tk.BooleanVar(value=True) for name in ALGORITHMS}
        self.speed = tk.IntVar(value=4)
        self.braid = tk.IntVar(value=15)
        self.big_text = tk.BooleanVar(value=False)
        self.heuristic = tk.StringVar(value="Manhattan")

        outer = ttk.Frame(root, padding=10)
        outer.pack(fill="both", expand=True)
        self.sidebar = ttk.Frame(outer, width=SIDEBAR_WIDTH)
        self.sidebar.pack(side="left", fill="y", padx=(0, 12))
        self.sidebar.pack_propagate(False)
        right = ttk.Frame(outer)
        right.pack(side="left", fill="both", expand=True)
        self.panel_area = ttk.Frame(right)
        self.panel_area.pack(fill="both", expand=True)

        self._build_sidebar()
        self._build_scoreboard(right)
        self.picker.current([t.name for t in TEMPLATES].index(DEFAULT_TEMPLATE))
        self.load_template()

        root.bind("<space>", lambda _e: self.toggle_run())
        root.bind("<Right>", lambda _e: self.step_once())
        root.bind("<Key-f>", lambda _e: self.finish_now())
        root.bind("<Escape>", lambda _e: self.reset())
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
        self.rebuild_panels()

    # -- building the window ---------------------------------------------------------

    def _heading(self, text: str) -> ttk.Frame:
        tk.Label(self.sidebar, text=text, font=self.fonts.title, bg=COLOR_BG,
                 fg=COLOR_TEXT, anchor="w").pack(fill="x", pady=(10, 3))
        box = ttk.Frame(self.sidebar)
        box.pack(fill="x")
        return box

    def _slider(self, parent: tk.Misc, title: str, var: tk.IntVar, lo: int, hi: int,
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

    def _build_sidebar(self) -> None:
        maze = self._heading("1   Choose a maze")
        # No widget keeps keyboard focus, so Space, the arrows, F and Esc always
        # mean the race shortcuts and never a focused button or slider.
        self.picker = ttk.Combobox(maze, state="readonly", font=self.fonts.body, takefocus=False,
                                   values=[f"{i + 1}.  {t.name}" for i, t in enumerate(TEMPLATES)])
        self.picker.pack(fill="x")
        self.picker.bind("<<ComboboxSelected>>", self.load_template)
        tk.Label(maze, textvariable=self.note_var, wraplength=SIDEBAR_WIDTH - 12,
                 justify="left", anchor="nw", bg=COLOR_BG, fg=COLOR_MUTED,
                 font=self.fonts.small, height=3).pack(fill="x", pady=(4, 2))
        ttk.Button(maze, text="Make a random maze", command=self.generate_random,
                   takefocus=False).pack(fill="x")
        self._slider(maze, "Loops in the random maze", self.braid, 0, 60, "none", "many")

        algos = self._heading("2   Choose the algorithms")
        for name in ALGORITHMS:
            row = ttk.Frame(algos)
            row.pack(fill="x", pady=1)
            tk.Label(row, bg=ALGO_COLORS[name], width=2).pack(side="left", padx=(2, 8))
            ttk.Checkbutton(row, text=name, variable=self.selected[name],
                            command=self.on_selection_change, takefocus=False).pack(side="left")
        picks = ttk.Frame(algos)
        picks.pack(fill="x", pady=(6, 0))
        picks.columnconfigure((0, 1), weight=1)
        for i, (label, names) in enumerate(QUICK_PICKS):
            ttk.Button(picks, text=label, command=lambda n=names: self.pick(n),
                       takefocus=False).grid(row=i // 2, column=i % 2, sticky="ew", padx=1, pady=1)
        guess = ttk.Frame(algos)
        guess.pack(fill="x", pady=(8, 0))
        tk.Label(guess, text="Guess to the goal", bg=COLOR_BG, fg=COLOR_TEXT,
                 font=self.fonts.body).pack(side="left")
        self.heuristic_box = ttk.Combobox(guess, state="readonly", font=self.fonts.body,
                                          takefocus=False, width=11, values=list(HEURISTICS),
                                          textvariable=self.heuristic)
        self.heuristic_box.pack(side="right")
        self.heuristic_box.bind("<<ComboboxSelected>>", self.on_heuristic_change)
        tk.Label(algos, text="used by A*, Greedy and Hill Climbing", bg=COLOR_BG,
                 fg=COLOR_MUTED, font=self.fonts.small, anchor="w").pack(fill="x")

        race = self._heading("3   Run the race")
        buttons = ttk.Frame(race)
        buttons.pack(fill="x")
        buttons.columnconfigure((0, 1), weight=1)
        self.run_button = ttk.Button(buttons, text="▶  Start", style="Accent.TButton",
                                     command=self.toggle_run, takefocus=False)
        self.run_button.grid(row=0, column=0, sticky="ew", padx=1, pady=1)
        ttk.Button(buttons, text="Reset", command=self.reset, takefocus=False).grid(
            row=0, column=1, sticky="ew", padx=1, pady=1)
        ttk.Button(buttons, text="Step", command=self.step_once, takefocus=False).grid(
            row=1, column=0, sticky="ew", padx=1, pady=1)
        ttk.Button(buttons, text="Finish", command=self.finish_now, takefocus=False).grid(
            row=1, column=1, sticky="ew", padx=1, pady=1)
        self._slider(race, "Speed", self.speed, 1, 60, "slow", "fast")

        bottom = ttk.Frame(self.sidebar)
        bottom.pack(side="bottom", fill="x")
        tk.Label(bottom, textvariable=self.status_var, wraplength=SIDEBAR_WIDTH - 12,
                 justify="left", anchor="sw", bg=COLOR_BG, fg=COLOR_TEXT,
                 font=self.fonts.body, height=2).pack(side="bottom", fill="x", pady=(6, 0))
        tools = ttk.Frame(bottom)
        tools.pack(side="bottom", fill="x", pady=(8, 0))
        ttk.Button(tools, text="How it works", command=self.show_help,
                   takefocus=False).pack(side="left")
        ttk.Checkbutton(tools, text="Big text", variable=self.big_text,
                        command=self.toggle_big_text, takefocus=False).pack(side="right")
        tk.Label(bottom, text="Draw your own maze before a race: left-drag paints walls, "
                              "right-drag erases, drag the green and red dots.",
                 wraplength=SIDEBAR_WIDTH - 12, justify="left", anchor="nw", bg=COLOR_BG,
                 fg=COLOR_MUTED, font=self.fonts.small).pack(side="bottom", fill="x")

    def _build_scoreboard(self, parent: ttk.Frame) -> None:
        tk.Label(parent, text="Scoreboard", font=self.fonts.title, bg=COLOR_BG,
                 fg=COLOR_TEXT, anchor="w").pack(fill="x", pady=(8, 2))
        ids = [c[0] for c in self.COLUMNS]
        self.board = ttk.Treeview(parent, columns=ids, show="headings",
                                  height=len(ALGORITHMS), selectmode="none")
        for cid, heading, width, anchor in self.COLUMNS:
            self.board.heading(cid, text=heading)
            self.board.column(cid, width=width, anchor=anchor, stretch=(cid == "result"))
        for name, color in ALGO_COLORS.items():
            self.board.tag_configure(name, foreground=color)
        self.board.pack(fill="x")
        tk.Label(parent, textvariable=self.summary_var, bg=COLOR_BG, fg=COLOR_TEXT,
                 font=self.fonts.bold, anchor="w").pack(fill="x", pady=(6, 0))

        legend = ttk.Frame(parent)
        legend.pack(fill="x", pady=(6, 0))
        sample = ALGO_COLORS["BFS"]
        items = (
            ("Start", COLOR_START), ("Goal", COLOR_GOAL), ("Wall", COLOR_WALL),
            ("Found, not checked yet", blend(sample, "#ffffff", 0.22)),
            ("Checked", blend(sample, "#ffffff", 0.68)),
            ("Final path", COLOR_PATH),
        )
        for text, color in items:
            tk.Label(legend, bg=color, width=2).pack(side="left", padx=(0, 4))
            tk.Label(legend, text=text, bg=COLOR_BG, fg=COLOR_TEXT,
                     font=self.fonts.small).pack(side="left", padx=(0, 16))

    # -- panels -----------------------------------------------------------------------

    def _layout(self, count: int) -> tuple[int, int, bool]:
        """Columns of panels, the cell size that fits them in this window, and
        whether the panels are too narrow for the full two-line header."""
        columns = 1 if count <= 1 else 2 if count <= 4 else 3
        rows = max(1, math.ceil(count / columns))
        line = self.fonts.body.metrics("linespace")
        chip = self.fonts.chip.metrics("linespace")
        board = 40 + self.rowheight * (max(2, count) + 1) + 2 * line + 36
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        if width < 400 or height < 300:           # not mapped yet: guess from the screen
            width = self.root.winfo_screenwidth() - 16
            height = self.root.winfo_screenheight() - 110
        avail_w = width - SIDEBAR_WIDTH - 50 - columns * 10

        def fits(header: int) -> int:
            avail_h = height - 28 - board - rows * (header + 10)
            return min(18, avail_w // (columns * self.grid.cols),
                       avail_h // (rows * self.grid.rows))

        cell = fits(chip + line + 14)             # name + tagline, counters below
        compact = cell < 11
        if compact:
            cell = fits(chip + 12)                # name and counters on one line
        return columns, max(4, cell), compact

    def rebuild_panels(self) -> None:
        """Create the panels for the ticked algorithms from scratch, sized for
        the window as it is now. A race in progress is painted back into them."""
        for widget in self.panel_area.winfo_children():
            widget.destroy()
        self.panels = []
        self.panel_by_name = {}
        names = [name for name in ALGORITHMS if self.selected[name].get()]
        if not names:
            tk.Label(self.panel_area, text="Tick at least one algorithm in step 2.",
                     bg=COLOR_BG, fg=COLOR_MUTED, font=self.fonts.title).pack(pady=60)
        columns, cell, compact = self._layout(len(names))
        for col in range(3):
            self.panel_area.columnconfigure(col, weight=1 if col < columns else 0)
        for i, name in enumerate(names):
            panel = Panel(self.panel_area, self.grid, name, ALGO_COLORS[name], cell,
                          self.fonts, compact)
            panel.grid(row=i // columns, column=i % columns, padx=5, pady=5, sticky="n")
            self._bind_editing(panel.canvas)
            self.panels.append(panel)
            self.panel_by_name[name] = panel
        self._laid_out_size = (self.root.winfo_width(), self.root.winfo_height())
        race = self.race
        if race is not None and [r.name for r in race.runners] == names:
            for runner in race.runners:
                self.panel_by_name[runner.name].render(runner)
            self.refresh_stats()
        else:
            self._reset_scoreboard(names)

    def _on_configure(self, event: tk.Event) -> None:
        """Re-size the panels when the window itself changes size."""
        if event.widget is not self.root:
            return
        if (event.width, event.height) == self._laid_out_size:
            return
        if self._relayout_id is not None:
            self.root.after_cancel(self._relayout_id)
        self._relayout_id = self.root.after(200, self._relayout)

    def _relayout(self) -> None:
        self._relayout_id = None
        if (self.root.winfo_width(), self.root.winfo_height()) != self._laid_out_size:
            self.rebuild_panels()

    def _reset_scoreboard(self, names: list[str]) -> None:
        self.board.delete(*self.board.get_children())
        self.board.configure(height=max(2, len(names)))
        for name in names:
            self.board.insert("", "end", iid=name, tags=(name,),
                              values=(name, "ready", "", "", "", "", "", "", ""))
        self.summary_var.set("")

    def _new_grid(self) -> None:
        self.pause()
        self.race = None
        self.rebuild_panels()
        self.set_status("Maze loaded. Press Start, or draw on the maze first.")

    # -- maze choice --------------------------------------------------------------------

    def load_template(self, _event=None) -> None:
        index = self.picker.current()
        if index < 0:
            return
        template = TEMPLATES[index]
        self.grid = template.build()
        self.note_var.set(template.note)
        self._new_grid()
        self.root.focus_set()

    def generate_random(self) -> None:
        seed = random.randrange(1, 1_000_000)
        loops = self.braid.get()
        self.grid = generate(seed=seed, braid_fraction=loops / 100)
        self.picker.set("Random maze")
        self.note_var.set(f"Random maze number {seed} with {loops}% of its inner walls removed. "
                          "With no loops every algorithm finds the same path; "
                          "with loops the shortcuts separate them.")
        self._new_grid()

    def pick(self, names: tuple[str, ...]) -> None:
        for name, var in self.selected.items():
            var.set(name in names)
        self.on_selection_change()

    def on_selection_change(self) -> None:
        self.pause()
        self.race = None
        self.rebuild_panels()
        count = len(self.panels)
        self.set_status(f"{count} algorithm{'s' if count != 1 else ''} in the race. Press Start.")

    def on_heuristic_change(self, _event=None) -> None:
        """A new guess means a new race: the informed algorithms would behave differently."""
        self.reset()
        self.set_status(f"{self.heuristic.get()} guess for A*, Greedy and Hill Climbing. "
                        "Press Start.")
        self.root.focus_set()

    # -- editing the shared maze -------------------------------------------------------

    def _bind_editing(self, canvas: GridCanvas) -> None:
        canvas.bind("<Button-1>", lambda e, c=canvas: self.on_left_press(e, c))
        canvas.bind("<B1-Motion>", lambda e, c=canvas: self.on_left_drag(e, c))
        canvas.bind("<Button-3>", lambda e, c=canvas: self.on_right(e, c))
        canvas.bind("<B3-Motion>", lambda e, c=canvas: self.on_right(e, c))
        canvas.bind("<ButtonRelease-1>", self.on_release)
        canvas.bind("<ButtonRelease-3>", self.on_release)

    def _editable(self) -> bool:
        if self.race is not None:
            self.set_status("Press Reset before drawing on the maze.")
            return False
        return True

    def on_left_press(self, event: tk.Event, canvas: GridCanvas) -> None:
        node = canvas.node_at(event.x, event.y)
        if node is None or not self._editable():
            return
        if node == self.grid.start:
            self.drag = "start"
        elif node == self.grid.goal:
            self.drag = "goal"
        else:
            self.drag = "wall"
            self.paint(node, wall=True)

    def on_left_drag(self, event: tk.Event, canvas: GridCanvas) -> None:
        node = canvas.node_at(event.x, event.y)
        if node is None or self.race is not None:
            return
        if self.drag in ("start", "goal"):
            self.move_endpoint(self.drag, node)
        elif self.drag == "wall":
            self.paint(node, wall=True)

    def on_right(self, event: tk.Event, canvas: GridCanvas) -> None:
        node = canvas.node_at(event.x, event.y)
        if node is not None and self._editable():
            self.drag = "erase"
            self.paint(node, wall=False)

    def on_release(self, _event: tk.Event) -> None:
        self.drag = None

    def paint(self, node: Node, wall: bool) -> None:
        r, c = node
        changed = self.grid.set_wall(r, c) if wall else self.grid.clear_wall(r, c)
        if changed:
            for panel in self.panels:
                panel.canvas.paint_cell(node)

    def move_endpoint(self, which: str, node: Node) -> None:
        move = self.grid.move_start if which == "start" else self.grid.move_goal
        if move(*node):
            for panel in self.panels:
                panel.canvas.paint_cell(node)
                panel.canvas.place_dots()

    # -- running the race ----------------------------------------------------------------

    def _ensure_race(self) -> Race | None:
        if self.race is None:
            if not self.panels:
                self.set_status("Tick at least one algorithm in step 2.")
                return None
            self.race = Race(self.grid, [(p.name, p.color) for p in self.panels],
                             HEURISTICS[self.heuristic.get()])
        return self.race

    def toggle_run(self) -> None:
        if self.running:
            self.pause()
        else:
            self.start()

    def start(self) -> None:
        race = self._ensure_race()
        if race is None or race.finished:
            return
        if race.started_at is None:
            race.start()          # the clock starts when Start is pressed
            self._ticks = 0
        race.resume()             # and runs again after a pause
        self.running = True
        self.run_button.config(text="❙❙  Pause")
        self.set_status("Racing. Space pauses, Right arrow steps.")
        self._schedule()

    def pause(self) -> None:
        self.running = False
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        if self.race is not None:
            self.race.pause()     # paused time is not time taken
            self.refresh_stats()  # and the frozen numbers are shown exactly
        if self.race is not None and not self.race.finished and self.race.started_at:
            self.run_button.config(text="▶  Resume")
            self.set_status("Paused. Right arrow steps one move at a time.")
        else:
            self.run_button.config(text="▶  Start")

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
            # Rewriting the scoreboard rows and panel counters 40 times a second
            # is wasted work on a slow classroom laptop; a few times a second reads
            # the same to the eye.
            self.refresh_stats()
        self._schedule()

    def _advance(self, k: int) -> None:
        """Move every runner ``k`` events and paint them. The scoreboard is
        refreshed separately, so painting stays cheap."""
        assert self.race is not None
        for runner, event in self.race.step(k):
            self.panel_by_name[runner.name].apply(event)

    def step_once(self) -> None:
        if self.running:
            self.pause()
        race = self._ensure_race()
        if race is not None and not race.finished:
            self._advance(1)
            if race.finished:
                self._finish()
            else:
                self.refresh_stats()      # a step by hand shows its numbers at once
                self.run_button.config(text="▶  Resume")

    def finish_now(self) -> None:
        race = self._ensure_race()
        if race is None:
            return
        self.pause()
        race.run_to_completion()
        for runner in race.runners:
            self.panel_by_name[runner.name].render(runner)
        self._finish()

    def _finish(self) -> None:
        self.running = False
        self.run_button.config(text="▶  Start")
        race = self.race
        assert race is not None
        self.refresh_stats()          # always once, with the final numbers
        found = [r for r in race.runners if r.found]
        parts = []
        if found:
            best = min(r.path_length for r in found)
            names = ", ".join(r.name for r in found if r.path_length == best)
            parts.append(f"Shortest path, {best} steps: {names}")
            fewest = min(found, key=lambda r: len(r.explored))
            parts.append(f"Fewest cells checked: {fewest.name} ({len(fewest.explored)})")
            first = min(found, key=lambda r: r.steps)   # fewest moves in lockstep
            parts.append(f"First to finish: {first.name} ({first.steps} moves)")
        failed = [r.name for r in race.runners if not r.found]
        if failed:
            parts.append("No path found by " + ", ".join(failed))
        self.summary_var.set("     ·     ".join(parts))
        self.set_status("Race finished. Press Reset to run again, or choose another maze.")

    def reset(self) -> None:
        self.pause()
        self.race = None
        self.run_button.config(text="▶  Start")
        for panel in self.panels:
            panel.reset()
        self._reset_scoreboard([p.name for p in self.panels])
        self.set_status("Reset. The maze can be drawn on again.")

    # -- stats -----------------------------------------------------------------------------

    def refresh_stats(self) -> None:
        race = self.race
        if race is None:
            return
        for runner in race.runners:
            self.panel_by_name[runner.name].show_stats(runner, race)
            self.board.item(runner.name, values=self._row(runner, race))

    @staticmethod
    def _row(runner: Runner, race: Race) -> tuple:
        if not runner.done:
            result = "running"
        elif runner.found:
            result = "path found"
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
            runner.name,
            result,
            len(runner.explored),
            "" if runner.path_length is None else runner.path_length,
            shortest,
            fmt_clock(runner.started_at),
            fmt_clock(runner.finished_at),
            f"{runner.elapsed():.2f} s" if runner.started_at else "",
            f"{runner.compute_seconds * 1000:.2f} ms" if runner.started_at else "",
        )

    def set_status(self, text: str) -> None:
        self.status_var.set(text)

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
